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

⚠️ OPTIONS CONFLUENCE & WALL PROTECTION RULES:
1. TIER 1 CONFLUENCE GATES:
   - A setup is high-probability if a GEX Level (Call/Put Wall) overlaps with a Volume Profile level (VAH/VAL/HVN) within +/- 15 ticks.
   - Propose adjustment of Fabio's Stop Loss (SL) to sit structurally behind this Tier 1 Confluence zone.
2. GEX SPEED BUMPS VS ACCELERATORS:
   - When price tests the Call Wall or Put Wall, it acts as a "speed bump" (absorption).
   - Confirm REVERSALS at GEX Walls ONLY if Footprint shows passive absorption (wicks >=35% and delta exhaustion).
   - Confirm BREAKOUTS past GEX Walls ONLY if RVol >= 1.25x and Delta is strongly directional, indicating institutions are slicing through dealer hedging.
3. ZERO GAMMA FLIP VETO:
   - Veto any long trade if price is trading below the Zero Gamma Flip level on increasing negative delta.
   - Veto any short trade if price is trading above the Zero Gamma Flip level on increasing positive delta.

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

    # ── PRE-CHECK DETERMINISTICI ───────────────────────────────────────────
    # Note: Legacy timing constraints (10:15-10:30 ET) removed to align strictly with video teachings.
    # ────────────────────────────────────────────────────────────────────────

    # Bypass NotebookLM: inject distilled knowledge directly
    user_msg = f"## TRADING RULES (DISTILLED KNOWLEDGE)\n{rules_text}\n{context_text}\n\n## TASK\n{question}\n\nDoes this bar confirm Fabio's signal? Respond with JSON only."

    sys_prompt = SYSTEM_PROMPT
    try:
        from src.agents.dynamic_rules_manager import get_active_rules
        active_rules = get_active_rules(limit=20)
        if active_rules:
            active_rules_text = "\n\nACTIVE LIVE CORRECTIONS / DYNAMIC RULES (MUST STRICTLY FOLLOW):\n"
            for r in active_rules:
                active_rules_text += f"- [{r['rule_id']}] Topic: {r['topic']}\n"
                active_rules_text += f"  Description: {r['description']}\n"
                active_rules_text += f"  Required Action: {r['action']}\n"
            sys_prompt = SYSTEM_PROMPT + active_rules_text
    except Exception as e:
        print(f"Error loading active dynamic rules: {e}")

    raw = llm_ask(sys_prompt, user_msg)
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

    # Legacy kill zone cap removed to align with video teachings.

    # ROBUSTNESS: Get confirmation from LLM data
    confirmation = bool(data.get('confirmation') or data.get('confirm'))
    if not confirmation and confidence >= 65 and data.get('direction', 'none') != 'none':
        confirmation = True

    # Ensure entry and stop are provided
    if fabio_signal.entry is None or fabio_signal.stop is None:
        confirmation = False
        confidence = 0

    return AndreaSignal(
        confirmation = confirmation,
        confidence   = confidence,
        setup_type   = data.get('setup_type', 'none'),
        reasoning    = data.get('reasoning', ''),
        nlm_answer   = "Bypassed",
        structural_stop = data.get('structural_stop')
    )
