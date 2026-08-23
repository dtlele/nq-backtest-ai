import json
import concurrent.futures
from pathlib import Path
from src import CandidateBar, FabioSignal, FABIO_NOTEBOOK_ID
from src.agents.llm_client import llm_ask
from src.signal_context import build_fabio_question
from src.agents.topic_router import select_fabio_topics, build_tiered_knowledge, FABIO_CORE
# Note: light_analyze is now fully deterministic (no LLM calls)

KNOWLEDGE_FILE = Path(__file__).parent.parent.parent / 'knowledge' / 'fabio_distilled.json'

_knowledge_cache = None

def _load_knowledge_store() -> dict:
    """Load and merge all Fabio knowledge into a single dict (cached)."""
    global _knowledge_cache
    if _knowledge_cache is not None:
        return _knowledge_cache
    with open(KNOWLEDGE_FILE, encoding='utf-8') as f:
        data = json.load(f)
    store = {}
    store.update(data.get('knowledge_by_topic', {}))
    store.update(data.get('simplified_strategy', {}))
    _knowledge_cache = store
    return store

def _get_system_prompt() -> str:
    prompt = "You are Fabio Valentini's PREDATORY trading methodology agent analyzing NQ futures (E-mini).\nYou follow a high-conviction institutional approach based on Volume Profile and Order Flow, aiming strictly for high-probability Triple A (A+) setups.\n\n"
    
    # Inject GEX Conformance guidelines
    prompt += (
        "⚠️ GEX REGIME & SETUP CONFORMANCE RULES:\n"
        "- If GEX_REGIME is POSITIVE (Long Gamma):\n"
        "  * Dealers suppress volatility. Expect mean-reversion / range chop.\n"
        "  * Prioritize REVERSAL and FAILED AUCTION setups off extremes (VAH, VAL, Put Wall, Call Wall).\n"
        "  * VETO or downgrade confidence on Breakout/Squeeze setups unless there is an extreme volume anomaly.\n"
        "- If GEX_REGIME is NEGATIVE (Short Gamma):\n"
        "  * Dealers amplify volatility. Expect trend expansion / momentum runs.\n"
        "  * Prioritize BREAKOUT (IBOB), SQUEEZE, and TREND CONTINUATION (TC) setups.\n"
        "  * Avoid fading momentum. Fading a negative GEX rally is a retail trap. Only attempt reversals if there is a massive institutional block (>=150 contracts) showing passive absorption.\n"
        "- If Zero Gamma Flip Level is breached:\n"
        "  * This is the ultimate pivot. A breach of Zero Gamma flips the market regime. Adjust your bias immediately (above = long bias/stability, below = short bias/volatility).\n\n"
    )

    # Load Active Dynamic Rules (Live corrections)
    try:
        from src.agents.dynamic_rules_manager import get_active_rules
        active_rules = get_active_rules()
        if active_rules:
            prompt += "ACTIVE LIVE CORRECTIONS / DYNAMIC RULES (MUST STRICTLY FOLLOW):\n"
            for r in active_rules:
                prompt += f"- [{r['rule_id']}] Topic: {r['topic']}\n"
                prompt += f"  Description: {r['description']}\n"
                prompt += f"  Required Action: {r['action']}\n"
            prompt += "\n"
    except Exception as e:
        print(f"Error loading active dynamic rules: {e}")


    # Load Core Setups
    strategies_file = Path(__file__).parent.parent.parent / 'knowledge' / 'strategies.json'
    if strategies_file.exists():
        try:
            with open(strategies_file, 'r', encoding='utf-8') as f:
                strats = json.load(f).get('strategies', [])
                if strats:
                    prompt += "CORE SETUP CLASSIFICATIONS (TRIPLE A SETUPS):\n"
                    for i, s in enumerate(strats, 1):
                        prompt += f"{i}. {s['name']} ({s['description']}):\n"
                        prompt += f"   - Trigger: {s['trigger']}\n"
                        prompt += f"   - Confirmation: {s['confirmation']}\n"
                    prompt += "\n"
        except Exception as e:
            print(f"Error loading strategies.json: {e}")

    # Load Mechanics
    mechanics_file = Path(__file__).parent.parent.parent / 'knowledge' / 'amt_mechanics.json'
    if mechanics_file.exists():
        try:
            with open(mechanics_file, 'r', encoding='utf-8') as f:
                mechs = json.load(f).get('mechanics', [])
                for m in mechs:
                    prompt += f"{m['topic']}:\n{m['description']}\n\n"
        except Exception as e:
            print(f"Error loading amt_mechanics.json: {e}")


    # JSON Schema definition
    prompt += """You are now the CHIEF PORTFOLIO MANAGER (Fabio). You will receive reports from your 3 Expert Analysts (AMT, Order Flow, Technical).
Your job is to synthesize their reports, resolve any conflicting bias, and make the final trading decision.

Respond ONLY with valid JSON matching this schema:
{
  "reasoning": "<MAX 100 WORDS. Synthesize the reports. Explain the final bias, which side is trapped, and justify the structural placement of the stop loss. ALWAYS ADD AN EXTRA 10 TICKS BUFFER BEHIND THE STRUCTURAL LEVEL.>",
  "market_narrative_update": "<Provide an evolving narrative of the trading session based on the reports.>",
  "setup_type": "squeeze" | "reversal" | "ivb_breakout" | "exhaustion" | "imbalance_hunting" | "none",
  "direction": "long" | "short" | "none",
  "confidence": <int 0-100>,
  "entry": <float or null>,
  "stop": <float or null>,
  "target": <float or null>
}"""
    return prompt

def light_analyze(candidate: CandidateBar, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None) -> int:
    """
    DETERMINISTIC light pass — zero API calls.

    Scoring logic (AMT + Fabio volume rules):
      +30  wall_max_size >= 50 (strong institutional conviction)
      +20  wall_max_size >= 30 (minimum institutional signal)
      +60  setup_category == 'imbalance_hunting' (always evaluate M1 footprints outside IB)
      +20  setup_category == 'momentum' (high-vol breakout)
      +15  setup_category == 'reversal' (absorption at extreme)
      +10  market_state == 'imbalance' (directional day)
      +10  auction_type == 'initiative' (outside IB/prev VA)
      +10  is_second_test == True (second drive / reload)
      +10  poc_migration != 'flat' (VP shifting = trending)
      -20  setup_category == 'pullback' AND wall_max_size < 20 (weak pullback)
      -20  market_state == 'balance' AND auction_type == 'responsive' (chop inside value)

    Returns score capped [0, 100].
    """
    from src.agents.llm_client import _get_provider
    if _get_provider() == "human":
        return 100  # Skip light pass for human operator

    score = 0

    # --- Volume / Wall strength ---
    wms = candidate.wall_max_size
    if wms >= 50:
        score += 30
    elif wms >= 30:
        score += 20

    # --- Setup category ---
    cat = candidate.setup_category
    if cat == 'imbalance_hunting':
        score += 20  # Reduced from 60. Now it requires actual big trades or context to pass the light filter!
    elif cat == 'momentum':
        score += 20
    elif cat == 'reversal':
        score += 15

    # --- AMT: market state ---
    if candidate.market_state == 'imbalance':
        score += 10

    # --- AMT: auction type ---
    if candidate.auction_type == 'initiative':
        score += 10

    # --- Second drive / reload ---
    if candidate.is_second_test:
        score += 10

    # --- VP migration (trending day) ---
    if candidate.poc_migration != 'flat':
        score += 10

    # --- Penalties ---
    if cat == 'pullback' and wms < 20:
        score -= 20
    if candidate.market_state == 'balance' and candidate.auction_type == 'responsive':
        score -= 20

    return max(0, min(100, score))

def analyze(candidate: CandidateBar, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None) -> FabioSignal:
    store = _load_knowledge_store()
    topics = select_fabio_topics(candidate, store)
    rules_text, context_text = build_tiered_knowledge(topics, store)
    question = build_fabio_question(candidate, session_context=session_context, m1_bars=m1_bars, market_narrative=market_narrative, bars_since_last=bars_since_last)
    
    # Base user msg containing all context
    base_user_msg = f"## TRADING RULES (DISTILLED KNOWLEDGE)\n{rules_text}\n{context_text}\n\n## TASK\n{question}\n\n"
    
    # Define Expert Prompts
    amt_prompt = "You are the AMT Analyst. Focus on Value Area High/Low, POC, Initial Balance, and Single Prints. Are we in balance or imbalance? Respond with a concise paragraph summarizing your bias (Long/Short/Neutral) and the key AMT levels."
    flow_prompt = "You are the Order Flow Analyst. Focus on Delta, imbalances, trapped traders, and volume walls. Who has control? Respond with a concise paragraph summarizing your bias (Long/Short/Neutral) and the key order flow dynamics."
    tech_prompt = "You are the Technical Structure Analyst. Focus on VWAP, standard deviations, moving averages, and general price action setups. CRUCIAL: Differentiate between extended breakouts (chasing) and high-probability pullbacks. We prefer entering on pullbacks that resume the trend. Respond with a concise paragraph summarizing your bias (Long/Short/Neutral) and the structural logic."
    macro_prompt = "You are the Macro & GEX Analyst. Focus on Gamma Exposure regimes (Positive vs Negative) and overnight session context. Are dealers suppressing or amplifying volatility? Respond with a concise paragraph dictating the 'Market Regime' (Trend vs Chop)."
    risk_prompt = "You are the Risk Manager (The Bouncer). Focus ONLY on volatility, time of day, and account protection. Will this trade require a stop wider than 20 points? Is it too close to a news event? CRUCIAL: If the stop is > 20 points because the move is extended, do NOT authorize the trade. We only enter on pullbacks where the structural stop is <= 20 points. Respond with a concise paragraph. If the trade is too risky or extended, you MUST output the exact word 'VETO'."

    def fetch_expert(prompt, user_msg):
        return llm_ask(prompt, user_msg)

    # Run all 5 experts in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        f_macro = executor.submit(fetch_expert, macro_prompt, base_user_msg + "Analyze the setup strictly from a Macro & GEX perspective.")
        f_amt   = executor.submit(fetch_expert, amt_prompt, base_user_msg + "Analyze the setup strictly from an AMT perspective.")
        f_flow  = executor.submit(fetch_expert, flow_prompt, base_user_msg + "Analyze the setup strictly from an Order Flow perspective.")
        f_tech  = executor.submit(fetch_expert, tech_prompt, base_user_msg + "Analyze the setup strictly from a Technical Structure perspective.")
        f_risk  = executor.submit(fetch_expert, risk_prompt, base_user_msg + "Analyze the setup strictly from a Risk Management perspective. Output VETO if dangerous.")
        
        macro_report = f_macro.result()
        amt_report   = f_amt.result()
        flow_report  = f_flow.result()
        tech_report  = f_tech.result()
        risk_report  = f_risk.result()

    # The Bouncer checks for VETO
    if "VETO" in risk_report.upper():
        return FabioSignal(
            direction='none', confidence=0, entry=None, stop=None, target=None, setup_type='none',
            reasoning=f"VETOED BY RISK MANAGER. Reason: {risk_report}",
            market_narrative_update="Risk Manager vetoed the trade.",
            nlm_answer="VETO",
        )

    # 4. Chief / Portfolio Manager
    chief_prompt = _get_system_prompt()
    chief_msg = base_user_msg + f"## EXPERT REPORTS\n\n### Macro & GEX Analyst Report\n{macro_report}\n\n### AMT Analyst Report\n{amt_report}\n\n### Order Flow Analyst Report\n{flow_report}\n\n### Technical Analyst Report\n{tech_report}\n\n"
    chief_msg += "You are the Chief Portfolio Manager. Read the expert reports above, evaluate any divergences, and make the final trading decision. Respond with JSON only."
    
    user_msg = chief_msg
    last_error = ""
    
    for attempt in range(3):
        raw = llm_ask(chief_prompt, user_msg)
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()

        try:
            data = json.loads(raw)
            direction = data.get('direction', 'none')
            entry = data.get('entry')
            stop = data.get('stop')
            
            # Validation for backward stops
            if direction == 'long' and entry is not None and stop is not None:
                if stop >= entry:
                    last_error = f"ERROR: You generated a backward stop for a LONG trade. Stop ({stop}) must be BELOW Entry ({entry}). Please recalculate and output valid JSON."
                    user_msg = chief_msg + f"\n\n{last_error}"
                    continue
                    
            if direction == 'short' and entry is not None and stop is not None:
                if stop <= entry:
                    last_error = f"ERROR: You generated a backward stop for a SHORT trade. Stop ({stop}) must be ABOVE Entry ({entry}). Please recalculate and output valid JSON."
                    user_msg = chief_msg + f"\n\n{last_error}"
                    continue
                    
            # If we get here, it's valid
            # We also attach the sub-reports inside the reasoning or as a side-note for auditing.
            combined_reasoning = data.get('reasoning', '') + f" [Macro: {macro_report[:40]}... | AMT: {amt_report[:40]}... | Flow: {flow_report[:40]}...]"
            return FabioSignal(
                direction   = direction,
                confidence  = int(data.get('confidence', 0)),
                entry       = entry,
                stop        = stop,
                target      = data.get('target'),
                setup_type  = data.get('setup_type', 'none'),
                reasoning   = combined_reasoning,
                market_narrative_update = data.get('market_narrative_update', ''),
                nlm_answer  = "Multi-Agent Synthesis",
            )
            
        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
            user_msg = chief_msg + f"\n\nERROR: {last_error}. Please output strictly valid JSON."

    # If it fails 3 times, return none
    return FabioSignal(
        direction='none', confidence=0,
        entry=None, stop=None, target=None,
        setup_type='none',
        reasoning=f'Failed after 3 attempts. Last error: {last_error}',
        nlm_answer="Failed Synthesis",
    )

def _get_management_system_prompt() -> str:
    prompt_file = Path(__file__).parent / 'fabio_management_prompt.txt'
    if not prompt_file.exists():
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(DEFAULT_MANAGEMENT_SYSTEM_PROMPT)
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read().strip()

DEFAULT_MANAGEMENT_SYSTEM_PROMPT = """You are Fabio Valentini's active risk management agent managing an open NQ futures position.
Your goal is to protect capital and maximize returns based on real-time Volume Profile and Order Flow.
You must analyze the open trade details and the latest M5 candle/M1 footprint to choose one of these actions:
1. "hold": Keep the position exactly as is. DEFAULT action when no structural event has occurred.
2. "trail": Move the stop loss structurally — but ONLY when strict conditions are met (see below).
3. "early_exit": Exit the trade immediately because the setup has been structurally invalidated.
4. "reverse": Exit current trade and open the opposite position on a strong reversal signature.

--- ACTIVE POSITION MANAGEMENT (APM) ---

1. TRAILING STOPS — STRICT STRUCTURAL RULES:
   Trail ONLY when ALL THREE of the following conditions are simultaneously true:
   
   A) MINIMUM 1:1 RISK/REWARD REACHED:
      - The trade must have moved at least 1x the initial risk in your favor before any trailing is allowed.
      - Example: Entry=25000 SHORT, initial Stop=25040 (risk=40pts). Trail only activates if price reaches 24960 or below (1:1).
      - If 1:1 is NOT reached → always output "hold". No exceptions.
   
   B) A STRUCTURAL EVENT HAS OCCURRED in your favor (one of the following):
      - A new significant SWING EXTREME has been printed: a new swing low (for SHORT) or new swing high (for LONG).
      - A new cluster of Big Trades (>=30 contracts) has formed IN THE DIRECTION of your trade at a new level, AND price has ACCEPTED (closed past it).
      - New TRAPPED TRADERS are confirmed: the opposite side tried to push back and failed, leaving wicks without body closes.
      - A known structural level (LVN, POC, prior swing) has been BROKEN AND ACCEPTED (body close past it).
   
   C) STOP PLACEMENT MUST GIVE BREATHING ROOM:
      - Place the new stop BEHIND the structural event — not 2-4 ticks behind a single bar's wall.
      - Minimum distance: behind the wick/extreme of the structural event candle, or behind the Big Trade cluster origin.
      - Never trail to break-even UNLESS a full structural event has occurred. "BE is good" does NOT override the structural requirement.
      - If the structural event is a Big Trade wall, place stop at least 15-20 ticks behind the wall, not immediately adjacent (buffer against stop hunts).
   
   If any of A, B, or C is NOT met → output "hold". Give the trade room to work.

2. REVERSAL SIGNATURES (Early Exit / Reverse):
   - Do NOT use early_exit for minor delta divergences, retail noise, or temporary pullbacks.
   - True Reversal requires: MASSIVE institutional Big Trades (>=50 contracts) acting as passive absorption AGAINST your position, confirmed by price BODY closing back through a key level.
   - Massive Ask/Bid Clusters (>100 contracts) on the opposite side near a structural level → EXIT EARLY.
   - A single bar of adverse delta is NOT enough. You need 2+ consecutive bars of institutional flow against your position.

3. DEFAULT BEHAVIOR:
   - When in doubt → "hold".
   - Only trail when the market has PROVEN the structural event with ACCEPTED price action (body close, not just a wick).
   - Premature trailing is worse than a stop loss: it guarantees a scratch on a potentially great trade.

Respond ONLY with valid JSON matching this schema:
{
  "decision": "hold" | "trail" | "early_exit" | "reverse",
  "new_stop": <float or null (only if trailing, must give structural breathing room)>,
  "new_target": <float or null (optional)>,
  "rr_reached": <float — current R:R achieved at this bar, e.g. 1.2>,
  "structural_event": "<describe the structural event that triggered trail, or 'none'>",
  "reasoning": "<MAX 80 WORDS. Cite R:R ratio, the specific structural event (or why holding), Big Trade levels, and exact stop placement logic.>"
}"""


def manage_active_trade(trade, candidate: CandidateBar, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None) -> dict:
    """Ask Fabio to manage the active trade based on the latest bar activity."""
    store = _load_knowledge_store()
    topics = select_fabio_topics(candidate, store)
    rules_text, context_text = build_tiered_knowledge(topics, store)
    question = build_fabio_question(candidate, session_context=session_context, m1_bars=m1_bars, market_narrative=market_narrative, bars_since_last=bars_since_last)
    
    # Inject active trade details
    trade_context = (
        f"\n\n## ACTIVE OPEN POSITION DETAILS:\n"
        f"Direction: {trade.direction.upper()}\n"
        f"Entry Price: {trade.entry:.2f}\n"
        f"Current Stop Loss: {trade.stop:.2f}\n"
        f"Current Target: {trade.target:.2f}\n"
        f"Contracts: {trade.contracts}\n"
        f"Entry Time: {trade.entry_bar.timestamp.strftime('%H:%M UTC')}\n"
    )
    
    user_msg = f"## TRADING RULES (DISTILLED KNOWLEDGE)\n{rules_text}\n{context_text}\n{trade_context}\n\n## TASK\n{question}\n\nAnalyze this active position and choose one of the actions: 'hold', 'trail', 'early_exit', or 'reverse'. Respond with JSON only."
    
    raw = llm_ask(_get_management_system_prompt(), user_msg)
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()
        
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "decision": "hold",
            "new_stop": None,
            "new_target": None,
            "reasoning": f"JSON parse error: {raw[:100]}"
        }
        
    return {
        "decision": data.get("decision", "hold"),
        "new_stop": data.get("new_stop"),
        "new_target": data.get("new_target"),
        "reasoning": data.get("reasoning", "")
    }
