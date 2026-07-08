import json
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

    # Statistical calibration hints (derived from 549 backtested trades)
    prompt += """BACKTESTED CONFIDENCE CALIBRATION (549 trades analyzed):
Use these empirical signals to calibrate your confidence score — they are NOT hard rules, but statistical priors:

1. STRUCTURE CONVERGENCE: IBL + VAL converging at the same level = strongest setup historically (59% WR).
   VAH or VAL alone WITHOUT IB confirmation = weak signal (22-31% WR). Subtract 10-15 from confidence.

2. INSTITUTIONAL FOOTPRINT: Big Trade >= 1000 contracts at the breakout point = strong confirmation (+10 confidence).
   High total bar volume (>3000 contracts) BUT small Big Trade = likely retail fakeout (-10 confidence).
   The SIZE of the single institutional order matters more than total volume.

3. DELTA CONVICTION: |Delta| >= 600 at entry bar = real directional commitment, confirmed.
   |Delta| < 300 = market in chop/equilibrium, subtract 10 from confidence.

4. TEMPORAL PHASES & HIGH SELECTIVITY QUESTIONS:
   For every candidate setup, you must run a strict self-audit by scoring your confidence (0-100%) for each of the following 5 questions:
   - q1_time_window_validity_score: Is the current time outside the Lunch Lull (12:00-13:30 ET), before the 13:00 ET standard cutoff (unless PM Power Hour Model B exception is met), and before 15:00 ET? (100% = high validity, <50% = dangerous/avoid).
   - q2_kill_zone_caution_score: Are we outside the 10:15 - 10:30 ET Kill Zone? IMPORTANT: If we are inside the Kill Zone but the market has just confirmed a strong breakout (Initiative Breakout / Acceptance outside the IB range with high volume and delta), the caution is OVERRIDDEN and this score must be 100% (High confidence). In a trending day, the most explosive moves happen exactly in this window — do not block them.
   - q3_rni_initiative_score: Is the market showing Initiative characteristics? (100% = clear initiative). Strong initiative usually requires directional order flow (expansive delta aligned with the price action). Absorption is important, but without follow-through and aligned delta, it can often be a fakeout.
   - q4_trend_alignment_score: Is this setup strictly trend-following in the direction of the session trend (imbalance phase), and NOT a counter-trend or fading setup? (Trend-following = 100%, Counter-trend = 0%. Fading is strictly forbidden; if counter-trend, score must be 0% and direction must be 'none').
   - q5_entry_precision_score: Is the entry point structurally sound? High scores (80-100%) MUST be given if EITHER: (A) price is actively pulling back to a boundary, OR (B) a pullback (EVEN A SHALLOW MICRO-PULLBACK ON M1) occurred recently and the current bar shows momentum/absorption confirming the resumption of the trend. To correctly identify a valid entry, you MUST have directional flow: the M1 Delta MUST be aligned with the body of the candle (e.g. positive delta for a bullish body, negative delta for a bearish body). A divergent delta (e.g. positive delta on a bearish body) is NOT a valid entry signal for initiative; it indicates mixed flow and algorithmic chop. Do not rationalize divergent delta as 'institutional absorption' to force a trade. If delta and body are misaligned, score this 0% and wait.
     STRUCTURAL STOP LOSS RULE: Stop losses MUST be placed behind significant structural levels (e.g., Institutional Walls, IB boundaries, or major volume nodes). MICRO-STOPS (e.g. 5 to 15 points distance) placed randomly inside or just outside a candle's range are strictly forbidden. Algorithmic liquidity sweeps are designed to hunt 5-15 point stops. You must protect your position by placing the stop behind a real structural wall. Wide structural stops (e.g. 30, 40, or even 50 points away, like entering at 21430 with a stop at 21400) are PERFECTLY FINE and ENCOURAGED for intraday trading because they give the trade room to breathe and survive algorithmic chop. Do NOT reject a valid setup just because the structural stop seems "too far" in points.
     
     WALL-DEPTH STOP PLACEMENT RULE: Institutional walls (Big Trade clusters) represent thick zones of support/resistance, not single price levels. When a buy wall spans from price A to price B (A < B), the stop loss for a LONG trade MUST be placed below the bottom of the wall (below A, with a buffer), NOT below the top (B). Placing it below the top puts the stop inside the wall, exposing it to stop hunts. Similarly, for a SHORT trade with a sell wall spanning from A to B (A < B), the stop loss MUST be placed above the top of the wall (above B), NOT above the bottom (A).

      ACCOUNT-STATE ADAPTIVE RISK MANAGEMENT & COOLDOWN RULE: You must dynamically evaluate whether to open a new trade based on the current session risk state (Equity, P&L, recent trades). Enforce these guidelines:
      - Profit Protection: If the session P&L is positive and exceeds +$800, you must protect your profits. Raise your setup standards. Only enter premium, high-conviction A+ setups with clear institutional absorption and structural backing. If the current setup is mediocre, set direction to 'none' to walk away.
      - Revenge Trading Prevention: If the session P&L is negative and is lower than -$800 (representing 2-3 stop losses), you have hit your daily drawdown soft limit. Do not attempt to force trades to make back losses (revenge trading). Set direction to 'none' and close the session.
      - Re-entry & Cooldown Analysis: If a trade closed very recently (e.g. less than 15 minutes ago), entering immediately is highly dangerous. You must carefully analyze if the market structure has printed a completely new institutional footprint (new Big Trades, clear breakout confirmation, or new swing extrema). If the footprint is unchanged or the market is in the same chop range, you must skip this candidate (direction='none') to allow the market to breathe.

Respond ONLY with valid JSON matching this schema (CoT reasoning is at the top of the schema to ensure logical consistency and maximum token budget is allocated to a detailed order flow narrative):
{
  "reasoning": "<Provide a comprehensive, detailed, and unconstrained Order Flow narrative. Focus on detailing the candle body vs delta alignment, buy/sell footprint imbalances, trapped participants, and structural stop placement. Do NOT use short templates; expand your analysis using as many tokens as needed to provide a professional, institutional-grade audit. Include a section explaining why this trade is worth taking given the current Account P&L and time since the last trade.>",
  "market_narrative_update": "<Provide an evolving narrative of the trading session. CRITICAL: Review your previous reasonings (Session Context) against what the market actually did afterwards (Bars Since Last). If you were wrong or missed a move, explicitly acknowledge the mistake and adjust your current bias/logic. How has the macro context shifted?>",
  "direction": "long" | "short" | "none",
  "confidence": <int 0-100>,
  "entry": <float or null>,
  "stop": <float or null>,
  "target": <float or null>,
  "setup_type": "squeeze" | "ivb_breakout" | "none",
  "imbalance_phase": "expansive" | "accumulation" | "none",
  "amt_profile_classification": "<Optional: e.g. Initiative Breakout, Responsive Rotation>",
  "macro_regime_classification": "<Optional: e.g. Trend Day, Range Day>",
  "trapped_participants_analysis": "<Optional: analysis of wicks, imbalance, and trapped size>",
  "day_classification_notes": "<Optional: classification notes for future daily cataloging>",
  "temporal_phase_audit": {
    "q1_time_window_validity_score": <int 0-100>,
    "q2_kill_zone_caution_score": <int 0-100>,
    "q3_rni_initiative_score": <int 0-100>,
    "q4_trend_alignment_score": <int 0-100>,
    "q5_entry_precision_score": <int 0-100>
  }
}"""
    return prompt

def light_analyze(candidate: CandidateBar, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None) -> int:
    """
    DETERMINISTIC light pass ÔÇö zero API calls.

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

    # --- Penalit├á fascia oraria 10:15-10:30 ET (18% WR storico su 51 trade) ---
    try:
        import pytz as _lp
        _ET = _lp.timezone('America/New_York')
        _bar_et = candidate.bar.timestamp.astimezone(_ET)
        if _bar_et.hour == 10 and 15 <= _bar_et.minute < 30:
            score -= 10  # Reduced penalty (was 25), caution only!
    except Exception:
        pass

    # --- Penalties ---
    if cat == 'pullback' and wms < 20:
        score -= 20
    if candidate.market_state == 'balance' and candidate.auction_type == 'responsive':
        score -= 20

    return max(0, min(100, score))

def analyze(candidate: CandidateBar, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None,
            equity: float = 50000.0, daily_pnl: float = 0.0, trade_count: int = 0, last_trade_pnl: float = 0.0, time_since_last_close: float = -1.0) -> FabioSignal:
    store = _load_knowledge_store()
    topics = select_fabio_topics(candidate, store)
    rules_text, context_text = build_tiered_knowledge(topics, store)
    question = build_fabio_question(
        candidate, 
        session_context=session_context, 
        m1_bars=m1_bars, 
        market_narrative=market_narrative, 
        bars_since_last=bars_since_last,
        equity=equity,
        daily_pnl=daily_pnl,
        trade_count=trade_count,
        last_trade_pnl=last_trade_pnl,
        time_since_last_close=time_since_last_close
    )
    
    # Bypass NotebookLM: inject distilled knowledge directly
    base_user_msg = f"## TRADING RULES (DISTILLED KNOWLEDGE)\n{rules_text}\n{context_text}\n\n## TASK\n{question}\n\nAnalyze this setup using the Rules above. Respond with JSON only."
    
    user_msg = base_user_msg
    last_error = ""
    
    for attempt in range(3):
        raw = llm_ask(_get_system_prompt(), user_msg)
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
                    user_msg = base_user_msg + f"\n\n{last_error}"
                    continue
                    
            if direction == 'short' and entry is not None and stop is not None:
                if stop <= entry:
                    last_error = f"ERROR: You generated a backward stop for a SHORT trade. Stop ({stop}) must be ABOVE Entry ({entry}). Please recalculate and output valid JSON."
                    user_msg = base_user_msg + f"\n\n{last_error}"
                    continue
                    
            # If we get here, it's valid
            imbalance_phase = data.get('imbalance_phase', 'none')
            
            base_reasoning = data.get('reasoning', '')
            amt_class = data.get('amt_profile_classification', '')
            macro_class = data.get('macro_regime_classification', '')
            trap_analysis = data.get('trapped_participants_analysis', '')
            temporal_audit = data.get('temporal_phase_audit', '')
            day_notes = data.get('day_classification_notes', '')
            
            full_reasoning = base_reasoning
            if amt_class or macro_class or trap_analysis or temporal_audit or day_notes:
                full_reasoning += "\n\n[Analisi Aggiuntiva]"
                if amt_class:
                    full_reasoning += f"\n- Profilo AMT: {amt_class}"
                if macro_class:
                    full_reasoning += f"\n- Macro Regime: {macro_class}"
                if trap_analysis:
                    full_reasoning += f"\n- Footprint (Trapped): {trap_analysis}"
                if temporal_audit:
                    if isinstance(temporal_audit, dict):
                        short_keys = {
                            "q1_time_window_validity_score": "Q1",
                            "q2_kill_zone_caution_score": "Q2",
                            "q3_rni_initiative_score": "Q3",
                            "q4_trend_alignment_score": "Q4",
                            "q5_entry_precision_score": "Q5"
                        }
                        parts = []
                        for k, v in temporal_audit.items():
                            label = short_keys.get(k, k)
                            val = f"{v}%" if isinstance(v, int) or (isinstance(v, str) and not v.endswith('%') and v.isdigit()) else f"{v}"
                            parts.append(f"{label}={val}")
                        full_reasoning += f"\n- Audit Fase Temporale: {' | '.join(parts)}"
                    else:
                        full_reasoning += f"\n- Audit Fase Temporale: {temporal_audit}"
                if day_notes:
                    full_reasoning += f"\n- Note Classificazione Giornata: {day_notes}"

            return FabioSignal(
                direction   = direction,
                confidence  = int(data.get('confidence', 0)),
                entry       = entry,
                stop        = stop,
                target      = data.get('target'),
                setup_type  = data.get('setup_type', 'none'),
                imbalance_phase = imbalance_phase,
                reasoning   = full_reasoning,
                market_narrative_update = data.get('market_narrative_update', ''),
                nlm_answer  = "Bypassed",
            )
            
        except json.JSONDecodeError as e:
            last_error = f"JSON parse error: {e}"
            user_msg = base_user_msg + f"\n\nERROR: {last_error}. Please output strictly valid JSON."

    # If it fails 3 times, return none
    return FabioSignal(
        direction='none', confidence=0,
        entry=None, stop=None, target=None,
        setup_type='none',
        reasoning=f'Failed after 3 attempts. Last error: {last_error}',
        nlm_answer="Bypassed",
    )

def _get_management_system_prompt() -> str:
    prompt_file = Path(__file__).parent / 'fabio_management_prompt.txt'
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(DEFAULT_MANAGEMENT_SYSTEM_PROMPT)
    return DEFAULT_MANAGEMENT_SYSTEM_PROMPT.strip()

DEFAULT_MANAGEMENT_SYSTEM_PROMPT = """You are Fabio Valentini's active risk management agent managing an open NQ futures position.
Your goal is to protect capital and maximize returns based on real-time Volume Profile, Auction Market Theory (AMT), and Order Flow.
You must analyze the open trade details and the latest M5 candle/M1 footprint to choose one of these actions:
1. "hold": Keep the position exactly as is. DEFAULT action when no structural event has occurred.
2. "trail": Move the stop loss structurally OR extend the take-profit target (or both) based on AMT.
3. "early_exit": Exit the trade immediately because the setup has been structurally invalidated, or because exhaustion/absorption has been reached near target.
4. "reverse": Exit current trade and open the opposite position on a strong reversal signature.

--- AMT-BASED DYNAMIC TARGET MANAGEMENT (TAKE PROFIT VS. EXTENSION) ---

You must actively evaluate the candle-by-candle Auction Market Theory (AMT) dynamics to decide whether to take profit early (exit) or extend the target (trail target):

1. DYNAMIC TAKE PROFIT (EARLY EXIT FOR EXHAUSTION/ABSORPTION):
   Even if the fixed target ("Current Target") has not been hit, you should exit early ("early_exit") to lock in profits if you see institutional exhaustion or counter-trend absorption:
   - For LONG trades: Price rises near a key level (resistance, VAL/VAH/POC, previous high), but the M1 footprint shows massive positive delta on bearish candle wicks (aggressive buyers buying but getting absorbed by limit sellers) or extreme negative delta at the high. This indicates exhaustion/absorption and imminent reversal. Exit immediately!
   - For SHORT trades: Price falls near a key level (support, VAL/VAH/POC, previous low), but the M1 footprint shows massive negative delta on bullish candle wicks (aggressive sellers getting absorbed by limit buyers) or extreme positive delta at the low. Exit immediately!
   - If the price has traveled >= 80% of the distance to the target, and momentum stalls with delta divergence or absorption — do not be greedy. Exit early to protect the open gain.

2. DYNAMIC TARGET EXTENSION (HOLD & EXTEND TP):
   If price is approaching the "Current Target", but the auction shows powerful initiative momentum and acceptance, do NOT exit. You can choose to extend the target ("trail" with a new target value):
   - For LONG trades: If price approaches the target, but the latest M1/M5 bars show a strong bullish body close with large positive delta, POC engulfing higher, and high volume (breakout acceptance). Update "new_target" to a higher structural level from the LEVEL MATRIX.
   - For SHORT trades: If price approaches the target, but the latest M1/M5 bars show a strong bearish body close with large negative delta, POC engulfing lower, and high volume (breakout acceptance). Update "new_target" to a lower structural level from the LEVEL MATRIX.
   - When extending the target, you must also trail the stop loss to protect the locked-in profits (e.g. to break-even or behind the breakout ignition wall).

--- ACTIVE POSITION MANAGEMENT (APM) ---

1. TRAILING STOPS — STRUCTURAL RULES:
   Trail stop loss when the trade has moved in your favor and a structural event has occurred:
   
   A) MINIMUM 1:1 RISK/REWARD OR STRONG BREAKOUT REACHED:
      - The trade must have moved at least 1x the initial risk in your favor OR must have completed a clean structural breakout (e.g., broke out of IB range or a major level with high volume).
      - If no structural progress is made, hold.
   
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

2. REVERSAL SIGNATURES (Early Exit / Reverse):
   - Do NOT use early_exit for minor delta divergences, retail noise, or temporary pullbacks.
   - True Reversal requires: MASSIVE institutional Big Trades (>=50 contracts) acting as passive absorption AGAINST your position, confirmed by price BODY closing back through a key level.
   - Massive Ask/Bid Clusters (>100 contracts) on the opposite side near a structural level -> EXIT EARLY.
   - A single bar of adverse delta is NOT enough. You need 2+ consecutive bars of institutional flow against your position.

3. DEFAULT BEHAVIOR:
   - When in doubt -> "hold".
   - Only trail when the market has PROVEN the structural event with ACCEPTED price action (body close, not just a wick).
   - Premature trailing is worse than a stop loss: it guarantees a scratch on a potentially great trade.

Respond ONLY with valid JSON matching this schema:
{
  "decision": "hold" | "trail" | "early_exit" | "reverse",
  "new_stop": <float or null (only if trailing, must give structural breathing room)>,
  "new_target": <float or null (optional, use to dynamically extend TP or adjust target)>,
  "rr_reached": <float — current R:R achieved at this bar, e.g. 1.2>,
  "structural_event": "<describe the structural event that triggered trail, target adjustment, or exit, or 'none'>",
  "reasoning": "<Provide a comprehensive, detailed, and unconstrained Order Flow narrative. Focus on detailing the candle volume, body-delta alignment, footprint imbalances, and structural level matrix to justify your decision to hold, trail stop, extend target, or exit early. Explain why this action is correct given the real-time AMT profile. Do NOT use short templates; expand your analysis as much as needed.>"
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
