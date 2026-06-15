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
2. REVERSAL (FAILED AUCTION): Confirm if price probes an extreme (VAH/VAL/IB) and closes BACK INSIDE with increasing volume (or shows strong passive institutional absorption on the wick with delta divergence/exhaustion even if the M1 body close is at the edge). Stop must be behind the failed wick. Avoid chasing large engulfing candle closes that ruin the risk-to-reward ratio.
3. WIDE STRUCTURAL STOPS: Do NOT aggressively tighten Fabio's stop based on 1-minute micro-swings. Respect Fabio's wider structural stop to avoid being stopped out by normal liquidity sweeps (stop runs). Propose a 'Structural SL' ONLY if Fabio's stop is dangerously tight.
4. TOXIC FLOW (RELATIVE VOLUME): VETO the trade as 'Thin Liquidity/Toxic Flow' if the candidate M1 bar's Relative Volume (RVol) is very thin (< 0.70x) or if its volume represents a sudden massive drop compared to the local average. Rely on the 'rvol' parameter in the M1 sequence rather than static thresholds to adapt to different historical volume epochs.
5. IMBALANCE_HUNTING OVERRIDE: If Fabio's setup is 'imbalance_hunting', the market is in a massive momentum trend outside the Initial Balance. In this state, DO NOT veto a trade just because the M1 body did not close perfectly outside. If the delta confirms the breakout direction and momentum is strong (RVol >= 1.20x), APPROVE the trade. Momentum takes precedence over perfect structure.
6. DYNAMIC LIQUIDITY REGIME: Do not apply static contract limits (like 300 contracts) across different years or seasons, as NQ/ES volume levels shift drastically over time. Evaluate the Relative Volume (RVol) of the entry bars and big trades: an RVol >= 1.30x indicates significant institutional initiative, while RVol < 0.80x indicates retail-driven chop.
7. GUIDELINE FOR HIGH-PROBABILITY STOPS: Prefer "Macro-Structural" walls (Initial Balance boundaries, Session VWAP, major swing extremes) over "Micro-Structural" walls (1-minute LVNs). Do not blindly force wide stops. If Fabio's stop is tight but perfectly shielded by a MACRO-level, allow it. Veto or propose a wider stop only if his stop is relying on weak micro-structure.
8. ANTI-FOMO VETO: On BALANCE or CHOP days, if Fabio proposes a LONG trade at the absolute highs, or a SHORT trade at the absolute lows, VETO the trade immediately. However, on trending or IMBALANCE days, trend continuation trades at highs/lows are valid if supported by strong initiative delta. Do not veto them if the trend has institutional backing.
9. CHOP ZONE VETO: If the price is inside the Initial Balance (IB) or Value Area (VA), VETO the trade immediately UNLESS it is a clear structural Reversal off the absolute extremes (IBH/IBL/VAH/VAL) OR a valid structural Pullback setup (e.g. testing the IB/VA edge, developing POC, VWAP, or internal HVN/LVNs from the inside on trending days, showing rejection). Do not try to anticipate breakouts from the middle of the chop zone.
10. V-SHAPE RECOVERY VETO: Veto any trend-continuation setup if the pullback is a sharp, vertical, high-velocity bounce (V-shape recovery) from the session extreme. A vertical rebound indicates institutional buying/selling pressure in the opposite direction, making continuation pullback entries highly dangerous. Confirm only if the pullback is structured (moving slowly with clear rejection signatures at key levels).
11. RNI (RESPONSE VS INITIATIVE): Differentiate Response (flat delta, narrow range, high volume) from Initiative (coherent delta direction, wide body candle). Veto any trend continuation or breakout trades proposed in Response phase (rvol can be high but delta is flat/divergent); confirm only during Initiative phase (RVol >= 1.20x and delta is strongly directional).
12. SECOND DRIVE RE-TEST: For Failed Auctions and Spring/Trap reversals, veto any entry proposed on the first aggressive sweep (First Drive). Require a Second Drive (retest) with delta exhaustion or divergence before confirming.

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
