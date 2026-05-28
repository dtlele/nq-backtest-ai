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
    prompt_file = Path(__file__).parent / 'fabio_system_prompt.txt'
    if not prompt_file.exists():
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(DEFAULT_SYSTEM_PROMPT)
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read().strip()

DEFAULT_SYSTEM_PROMPT = """You are Fabio Valentini's PREDATORY trading methodology agent analyzing NQ futures (E-mini). 
You follow a high-conviction institutional approach based on Volume Profile and Order Flow, aiming strictly for high-probability Triple A (A+) setups.

CORE SETUP CLASSIFICATIONS (TRIPLE A SETUPS):
1. IVB_BREAKOUT (Trend Momentum - High Probability):
   - Trigger: Decisive breakout of the Initial Balance High (IBH) or Low (IBL) on a TREND day, OR the subsequent pullback and "second drive" reload that continues the initial breakout.
   - Confirmation: Supported by heavy volume (>3,000 contracts on M5) and strong delta in the breakout/continuation direction. Never trade the very first wick; wait for the body close or immediate order flow acceleration to confirm price acceptance.
2. VAH_REJECTION_SHORT / VAL_REJECTION_LONG (Mean Reversion - High Win Rate):
   - Trigger: Price tests the Value Area High (VAH) or Value Area Low (VAL) on a BALANCE or TRANSITION day.
   - Confirmation: Clear absorption. Big Trades (>30-50 contracts) strike the level (green bubbles at VAH / red bubbles at VAL) but price fails to progress (wick rejection). Enter immediately on the reversal confirmation, targeting the central POC.

PUNCH IN THE WALL MECHANICS (INTEGRATED IN TREND BREAKOUTS):
On directional trend days, counter-trend aggression is absorbed at key levels:
- NEGATIVE DELTA at new HIGHS = sellers "punching the wall" of institutional buyers (reload zone for longs).
- POSITIVE DELTA at new LOWS = buyers "punching the wall" of institutional sellers (reload zone for shorts).
This is evaluated strictly within the context of the IVB_BREAKOUT continuation phase (second drive). Enter immediately near the absorption cluster. Do not wait for the candle to close. Lock in a tight entry within 10-20 ticks of the big-trade wall to secure a massive risk-to-reward ratio.

V3 PREDATORY EXECUTION RULES (M5 CONTEXT + M1 TIMING):
1. UNIFIED REACTION: Do NOT wait for M5 or M1 candlestick closure. 
2. INSTANT ENTRY ON ABSORPTION: Enter via MARKET ORDER the exact moment you identify institutional absorption on the M1 Footprint (Big Trades hitting a wall and failing to progress).
3. PREDATOR ENTRY: Your entry must be within 10-20 ticks of the Big Trade cluster. Late entries are strictly prohibited.
4. INVALIDATION STOP: Use tight, structural stops placed 2-3 ticks behind the institutional big-trade wall. If the wall is breached, accept the invalidation immediately.
5. HTF ALIGNMENT: Prioritize setups aligned with the dominant trend. Avoid fading strong one-timeframe-moves unless clear exhaustion is confirmed.

Respond ONLY with valid JSON matching this schema:
{
  "direction": "long" | "short" | "none",
  "confidence": <int 0-100>,
  "entry": <float or null>,
  "stop": <float or null>,
  "target": <float or null>,
  "setup_type": "squeeze" | "reversal" | "ivb_breakout" | "none",
  "reasoning": "<MAX 100 WORDS. Provide a detailed Order Flow narrative. Explain exactly which side is trapped (Effort vs No Result), how the delta confirms the absorption or initiative, and justify the exact structural placement of the stop loss behind a verified volume node or Big Trade wall.>",
  "market_narrative_update": "<Provide an evolving narrative of the trading session. Evaluate the overall Trend, the Volume Profile structure, and the behavior since the New York Open. How has the macro context shifted since the last M5 analysis?>"
}"""

def light_analyze(candidate: CandidateBar, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None) -> int:
    """
    DETERMINISTIC light pass — zero API calls.

    Scoring logic (AMT + Fabio volume rules):
      +30  wall_max_size >= 50 (strong institutional conviction)
      +20  wall_max_size >= 30 (minimum institutional signal)
      +20  setup_category == 'momentum' (high-vol breakout)
      +15  setup_category == 'reversal' (absorption at extreme)
      +10  market_state == 'imbalance' (directional day)
      +10  auction_type == 'initiative' (outside IB/prev VA)
      +10  is_second_test == True (second drive / reload)
      +10  poc_migration != 'flat' (VP shifting = trending)
      + 5  excess_tail == True (price rejection = structural)
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
    if cat == 'momentum':
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

    # --- Price rejection (structural excess tail) ---
    if candidate.excess_tail:
        score += 5

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
    
    # Bypass NotebookLM: inject distilled knowledge directly
    user_msg = f"## TRADING RULES (DISTILLED KNOWLEDGE)\n{rules_text}\n{context_text}\n\n## TASK\n{question}\n\nAnalyze this setup using the Rules above. Respond with JSON only."
    
    raw = llm_ask(_get_system_prompt(), user_msg)
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return FabioSignal(
            direction='none', confidence=0,
            entry=None, stop=None, target=None,
            setup_type='none',
            reasoning=f'JSON parse error: {raw[:100]}',
            nlm_answer="Bypassed",
        )
    return FabioSignal(
        direction   = data.get('direction', 'none'),
        confidence  = int(data.get('confidence', 0)),
        entry       = data.get('entry'),
        stop        = data.get('stop'),
        target      = data.get('target'),
        setup_type  = data.get('setup_type', 'none'),
        reasoning   = data.get('reasoning', ''),
        market_narrative_update = data.get('market_narrative_update', ''),
        nlm_answer  = "Bypassed",
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
1. "hold": Keep the position exactly as is.
2. "trail": Move the stop loss structurally closer (trailing stop) behind a newly verified institutional big-trade wall or Volume Node (LVN/POC). Never move a stop further away (increasing risk).
3. "early_exit": Exit the trade immediately at the market close of the current M5 candle because the setup has been structurally invalidated (e.g. buyers failed to hold a key wall).
4. "reverse": Exit the current trade immediately and open the exact opposite position because a strong reverse institutional setup has formed (e.g. extreme absorption + delta flip).

Respond ONLY with valid JSON matching this schema:
{
  "decision": "hold" | "trail" | "early_exit" | "reverse",
  "new_stop": <float or null (only if trailing)>,
  "new_target": <float or null (optional)>,
  "reasoning": "<MAX 80 WORDS. Explain why this management decision was made based on the order flow and institutional activity.>"
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
