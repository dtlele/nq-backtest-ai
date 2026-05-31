import json
from pathlib import Path
from src import CandidateBar, FabioSignal, AndreaSignal, ANDREA_NOTEBOOK_ID, Bar
from src.agents.nlm_client import nlm_ask
from src.agents.llm_client import llm_ask
from src.signal_context import build_andrea_question
from src.agents.topic_router import select_andrea_topics, build_tiered_knowledge

KNOWLEDGE_FILE = Path(__file__).parent.parent.parent / 'knowledge' / 'andrea_distilled.json'

_knowledge_cache = None

def _load_knowledge_store() -> dict:
    """Load and merge all Andrea knowledge into a single dict (cached)."""
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

SYSTEM_PROMPT = """You are Andrea Cimi's methodology agent providing confirmation analysis for NQ futures (E-mini). 
You use Auction Market Theory to validate Fabio's setups.

STRUCTURAL VALIDATION (NQ 2025):
- LEDGE PROTECTION: Every trade must have a 'Structural Invalidation Point' (Ledge). This is the transition from a High Volume Node (HVN) to a Low Volume Node (LVN). The stop MUST sit behind this ledge. OR, if Fabio is trading an INITIATIVE setup, the stop MUST sit behind the origin (tail) of the initiative Big Trades.
- PRICE ACCEPTANCE: A breakout is only valid if price builds a new range (High Volume Node) outside the previous Value Area.
- WICK REJECTION FILTER: If price pokes a level but the BODY of the M1 candle does not close outside, it is a 'Liquidity Sweep' (Fake), not a breakout.

CONFIRMATION RULES:
1. MOMENTUM: Confirm ONLY if price shows initiative delta (>10%) AND acceptance (body close) past the structural wall.
2. REVERSAL (FAILED AUCTION): Confirm if price probes an extreme (VAH/VAL/IB) and closes BACK INSIDE with increasing volume. Stop must be behind the failed wick.
3. WIDE STRUCTURAL STOPS: Do NOT aggressively tighten Fabio's stop based on 1-minute micro-swings. Respect Fabio's wider structural stop to avoid being stopped out by normal liquidity sweeps (stop runs). Propose a 'Structural SL' ONLY if Fabio's stop is dangerously tight.
4. TOXIC FLOW: If M1 volume is < 300 contracts, VETO the trade as 'Thin Liquidity/Toxic Flow'.
5. IMBALANCE_HUNTING OVERRIDE: If Fabio's setup is 'imbalance_hunting', the market is in a massive momentum trend outside the Initial Balance. In this state, DO NOT veto a trade just because the M1 body did not close perfectly outside. If the delta confirms the breakout direction and momentum is strong, APPROVE the trade. Momentum takes precedence over perfect structure.

Respond ONLY with valid JSON:
{
  "confirmation": true | false,
  "confidence": <int 0-100>,
  "setup_type": "ibob" | "failed_auction" | "reversal" | "none",
  "structural_stop": <float | null>,
  "reasoning": "<MAX 40 WORDS. Explain referencing structural ledges, M1 bodies vs wicks, and volume acceptance.>"
}"""

def confirm(candidate: CandidateBar, fabio_signal: FabioSignal, m1_bars: list[Bar] = None) -> AndreaSignal:
    store = _load_knowledge_store()
    topics = select_andrea_topics(candidate, fabio_signal.setup_type, store)
    rules_text, context_text = build_tiered_knowledge(topics, store)
    question = build_andrea_question(candidate, fabio_signal, m1_bars=m1_bars)

    # ── PRE-CHECK DETERMINISTICI (basati su 549 trade storici) ──────────────
    # Check 1: Nessun Big Trade istituzionale → veto immediato
    if candidate.wall_max_size < 200:
        return AndreaSignal(
            confirmation=False, confidence=25,
            setup_type='none',
            reasoning=f'VETO: No institutional footprint (wall_max_size={candidate.wall_max_size} < 200 contracts). Statistically 18% WR.',
            nlm_answer='Deterministic veto',
        )

    # Check 2: Kill zone 10:15–10:30 ET (18% WR su 51 trade storici)
    _is_kill_zone = False
    try:
        import pytz as _ap
        _ET2 = _ap.timezone('America/New_York')
        _bar_et2 = candidate.bar.timestamp.astimezone(_ET2)
        if _bar_et2.hour == 10 and 15 <= _bar_et2.minute < 30:
            _is_kill_zone = True
    except Exception:
        pass
    # ────────────────────────────────────────────────────────────────────────

    # Bypass NotebookLM: inject distilled knowledge directly
    user_msg = f"## TRADING RULES (DISTILLED KNOWLEDGE)\n{rules_text}\n{context_text}\n\n## TASK\n{question}\n\nDoes this bar confirm Fabio's signal? Respond with JSON only."

    raw = llm_ask(SYSTEM_PROMPT, user_msg)
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return AndreaSignal(
            confirmation=False, confidence=0,
            setup_type='none',
            reasoning=f'JSON parse error: {raw[:100]}',
            nlm_answer="Bypassed",
        )
    

    confidence = int(data.get('confidence', 0))

    # Apply kill zone cap AFTER LLM response
    if _is_kill_zone:
        confidence = min(confidence, 40)
        return AndreaSignal(
            confirmation=False, confidence=confidence,
            setup_type=data.get('setup_type', 'none'),
            reasoning=f'KILL ZONE 10:15-10:30 ET (18% WR storico). ' + data.get('reasoning', ''),
            nlm_answer='Bypassed',
            structural_stop=data.get('structural_stop'),
        )

    # Compute stop distance in ticks (NQ tick = 0.25)
    stop_distance_ticks = abs(fabio_signal.entry - fabio_signal.stop) / 0.25
    # Veto trades with very tight stops (<10 ticks)
    if stop_distance_ticks < 10:
        confirmation = False
        confidence = min(confidence, 30)
    else:
        # ROBUSTNESS: If manual mailbox input lacks "confirmation" but has high confidence + direction, assume True.
        # Check for both 'confirmation' and legacy 'confirm' keys
        confirmation = bool(data.get('confirmation') or data.get('confirm'))
        # Preserve existing robustness heuristic
        if not confirmation and confidence >= 65 and data.get('direction', 'none') != 'none':
            confirmation = True

    return AndreaSignal(
        confirmation = confirmation,
        confidence   = confidence,
        setup_type   = data.get('setup_type', 'none'),
        reasoning    = data.get('reasoning', ''),
        nlm_answer   = "Bypassed",
        structural_stop = data.get('structural_stop')
    )
