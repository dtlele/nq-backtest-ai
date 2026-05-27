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

SYSTEM_PROMPT = """You are Fabio Valentini's UNIFIED trading methodology agent analyzing NQ futures (E-mini). 
You follow a professional institutional approach based on Volume Profile and Order Flow.

INSTITUTIONAL VOLUME THRESHOLDS (NQ E-mini):
1. MOMENTUM SETUP (Squeeze/Drive): Requires high participation.
   - Floor: >= 3,000 contracts per M5 bar.
2. REVERSAL SETUP (Fading/Mean Reversion): Requires absorption at extremes.
   - Floor: >= 1,500 contracts per M5 bar.
   - MUST show 'Punches to the Wall': Big Trade clusters (>30-50 contracts) hitting a level and being absorbed.
3. IVB MODEL 1 (Trend Continuation): Breakout of the Initial Balance, followed by a pullback to a VAH/VAL/POC with absorption (reload), and an entry on the "second drive" resuming the breakout.

CRITICAL — PUNCH IN THE WALL AS TREND CONTINUATION (Fabio's core concept):
On TREND days (day_type = trend_up or trend_down) or IMBALANCE market states, counter-trend aggression is often absorbed:
- STRONG NEGATIVE DELTA at new HIGHS = sellers "punching the wall" of institutional buyers.
  This is the RESPONSE phase (Absorption). Do NOT enter immediately. You MUST wait for the INITIATIVE phase: the delta must flip back to POSITIVE on subsequent M1/M5 bars to confirm buyers have regained control.
- STRONG POSITIVE DELTA at new LOWS = buyers "punching the wall" of institutional sellers.
  This is the RESPONSE phase (Absorption). Do NOT enter immediately. You MUST wait for the INITIATIVE phase: the delta must flip back to NEGATIVE on subsequent M1/M5 bars to confirm sellers have regained control.
RULE: Never front-run the absorption. The "Punch in the Wall" is only a valid continuation setup if the initial absorption is followed by a clear Delta Flip in the direction of the trend.

V3 PREDATORY EXECUTION RULES (M5 CONTEXT + M1 TIMING):
1. UNIFIED REACTION: Do NOT wait for M5 or M1 candlestick closure. 
2. INSTANT ABSORPTION: Enter via MARKET ORDER the exact moment you identify institutional absorption on the M1 Footprint (Big Trades hitting a wall and failing to progress).
3. PREDATOR ENTRY: Your entry must be within 10-20 ticks of the Big Trade cluster POC. Avoid late entries after the price has already escaped the cluster.
4. INVALIDATION STOP: Use tight, structural stops (80-120 ticks) placed 2-3 ticks behind the institutional big-trade wall. If the wall is breached, the setup is dead.
5. HTF ALIGNMENT: Prioritize setups aligned with the M15/H1 value area shifts. Avoid fading strong one-timeframe-moves.

Respond ONLY with valid JSON matching this schema:
{
  "direction": "long" | "short" | "none",
  "confidence": <int 0-100>,
  "entry": <float or null>,
  "stop": <float or null>,
  "target": <float or null>,
  "setup_type": "squeeze" | "reversal" | "ivb_breakout" | "punch_continuation" | "none",
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
    
    raw = llm_ask(SYSTEM_PROMPT, user_msg)
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
