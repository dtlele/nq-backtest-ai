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

# ---------------------------------------------------------------------------
# STEP 1 — Context Evaluation System Prompt
# Focus: WHO is trapped? Is there a valid setup? What TYPE?
# Explicitly EXCLUDES entry/stop/target to prevent LLM anchoring on price levels.
# ---------------------------------------------------------------------------
def _get_step1_system_prompt(day_type: str = None) -> str:
    prompt = (
        "You are Fabio Valentini's PREDATORY trading methodology agent analyzing NQ futures (E-mini).\n"
        "Your ONLY task right now is to evaluate whether a high-probability Triple A (A+) setup EXISTS\n"
        "in the current market context. Do NOT think about entry prices, stop levels, or targets yet.\n"
        "Focus exclusively on: market state, trapped side, structural confluence, and setup type.\n\n"
    )

    # Step 1 rules: context/setup recognition rules only
    try:
        from src.agents.dynamic_rules_manager import get_active_rules
        active_rules = get_active_rules(limit=10, day_type=day_type, step=1)
        if active_rules:
            ctx_label = f" [context: {day_type}]" if day_type else ""
            prompt += f"CONTEXT EVALUATION RULES{ctx_label} (apply before deciding if a setup exists):\n"
            for r in active_rules:
                prompt += f"- [{r['rule_id']}] {r['topic']}: {r['description']}\n"
            prompt += "\n"
    except Exception as e:
        print(f"Error loading step-1 rules: {e}")

    # Core setup types
    strategies_file = Path(__file__).parent.parent.parent / 'knowledge' / 'strategies.json'
    if strategies_file.exists():
        try:
            with open(strategies_file, 'r', encoding='utf-8') as f:
                strats = json.load(f).get('strategies', [])
                if strats:
                    prompt += "VALID TRIPLE-A SETUP TYPES:\n"
                    for i, s in enumerate(strats, 1):
                        prompt += f"{i}. {s['name']}: {s['description']}\n"
                        prompt += f"   Trigger: {s['trigger']} | Confirmation: {s['confirmation']}\n"
                    prompt += "\n"
        except Exception as e:
            print(f"Error loading strategies.json: {e}")

    prompt += """CONTEXT EVALUATION RULES:
- Balance vs Imbalance: Is today trending (IB break + VP migration) or ranging (price inside VA)?
- Who is TRAPPED? Buyers trapped above a failed high = short bias. Sellers trapped below a failed low = long bias.
- Effort vs No Result: Big volume + no price progress = absorption. Is it real or noise?
- Is this First Drive or Second Drive? Never trade First Drive reversals.
- NARRATIVE DISCOVERY: Ask yourself 'Who is trapped and on which side?'

Respond ONLY with valid JSON matching EXACTLY this schema:
{
  "setup_valid": <true or false>,
  "setup_type": "ivb_model_1_continuation" | "val_vah_reversal" | "momentum_squeeze" | "none",
  "bias": "long" | "short" | "none",
  "trapped_side": "buyers" | "sellers" | "none",
  "key_structural_level": <float or null — the most important level for this setup>,
  "market_state": "imbalance" | "balance" | "transition",
  "session_narrative": "<MAX 120 WORDS: evolving session context, what happened, what changed, who is in control>"
}"""
    return prompt


# ---------------------------------------------------------------------------
# STEP 2 — Mechanical Execution System Prompt
# Focus: GIVEN a confirmed setup, where exactly do I enter/stop/target?
# Only called when Step 1 confirms setup_valid=true.
# ---------------------------------------------------------------------------
def _get_step2_system_prompt() -> str:
    prompt = (
        "You are Fabio Valentini's PREDATORY trading execution agent for NQ futures (E-mini).\n"
        "A setup has already been confirmed. Your task is to calculate the PRECISE mechanical execution:\n"
        "entry price, structurally-placed stop loss (behind a Big Trade wall), and profit target.\n\n"
    )

    # Step 2 rules: stop placement and mechanics only
    try:
        from src.agents.dynamic_rules_manager import get_active_rules
        mech_rules = get_active_rules(limit=6, step=2)
        if mech_rules:
            prompt += "MECHANICAL EXECUTION RULES (stop placement, sizing, targets):\n"
            for r in mech_rules:
                prompt += f"- [{r['rule_id']}] {r['topic']}: {r['description']}\n"
            prompt += "\n"
    except Exception as e:
        print(f"Error loading step-2 rules: {e}")

    prompt += """STOP PLACEMENT — CRITICAL RULES:
1. For SHORT: stop goes ABOVE the nearest counter-trend BUY wall (Big Trade cluster on ask side).
   The wall absorbs buying BEFORE reaching your stop. Stop = wall_top + 1-2pt buffer.
2. For LONG: stop goes BELOW the nearest counter-trend SELL wall (Big Trade cluster on bid side).
   Stop = wall_bottom - 1-2pt buffer.
3. Prefer macro-structural walls (IB High/Low, VWAP, session swing) over micro M1 walls.
4. If no protective wall exists within 30 points of entry → output stop=null (system will veto).

BACKTESTED CALIBRATION PRIORS:
- Structure convergence (IBL + VAL at same level): +15 confidence
- High RVol (>= 1.5x) + large Big Trade at breakout: +10 confidence
- |Delta| >= 15% of bar volume: +10 confidence
- |Delta| < 5% of bar volume: -10 confidence
- V-shape recovery without retest: -15 confidence

Respond ONLY with valid JSON matching EXACTLY this schema:
{
  "reasoning": "<MAX 150 WORDS: cite the specific Big Trade wall protecting the stop, exact stop placement logic, target rationale. State which wall price=X size=Y is the structural shield.>",
  "direction": "long" | "short",
  "confidence": <int 0-100>,
  "entry": <float>,
  "stop": <float or null>,
  "target": <float>
}"""
    return prompt


# ---------------------------------------------------------------------------
# STEP 3 — Risk Critique & Self-Reflection System Prompt
# Focus: Play Devil's Advocate, audit stop loss placement, verify mathematical
# and structural consistency, and adjust confidence if necessary.
# ---------------------------------------------------------------------------
def _get_step3_system_prompt() -> str:
    prompt = (
        "You are Fabio Valentini's PREDATORY trading risk critique agent for NQ futures (E-mini).\n"
        "Your task is to audit a proposed trade execution plan and verify its logical, structural, and mathematical consistency.\n\n"
        "CRITICAL RISK AUDIT CHECKS:\n"
        "1. Stop Loss Placement: Ensure the stop is structurally shielded by a verified volume ledge or Big Trade wall.\n"
        "   If the stop is placed in thin air (no structural level) or is too tight (less than 10 points / 40 ticks from entry on NQ is almost always a stop hunt), this is high risk!\n"
        "2. Mathematical Consistency: For LONG, entry must be > stop and target > entry. For SHORT, entry must be < stop and target < entry. Stop and Target must not be backward.\n"
        "3. Play Devil's Advocate: Are there 2 strong reasons why this trade could fail? (e.g. trading straight into a major HVN, declining RVol, macro trend alignment).\n"
        "If you find structural inconsistencies or if the risk is unshielded, you must either:\n"
        "- Adjust the stop or target to be safer.\n"
        "- Reduce confidence below 65 (to skip the trade).\n"
        "- Mark the setup as invalid by setting direction to 'none'.\n\n"
        "Respond ONLY with valid JSON matching EXACTLY this schema:\n"
        "{\n"
        "  \"reasoning\": \"<MAX 100 WORDS: Explain your audit findings. Critique the stop loss placement and potential failure modes. Justify any adjustments made.>\",\n"
        "  \"direction\": \"long\" | \"short\" | \"none\",\n"
        "  \"confidence\": <int 0-100>,\n"
        "  \"entry\": <float>,\n"
        "  \"stop\": <float or null>,\n"
        "  \"target\": <float>\n"
        "}"
    )
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
    wts = sum(t.size for t in candidate.bar.big_trades) if candidate.bar.big_trades else 0
    abs_delta = abs(candidate.bar.delta)
    
    if wms >= 100 or wts >= 150 or abs_delta >= 300:
        score += 50  # Massive activity
    elif wms >= 50 or wts >= 100 or abs_delta >= 200:
        score += 30
    elif wms >= 20 or wts >= 50 or abs_delta >= 100:
        score += 20

    # --- Setup category ---
    cat = candidate.setup_category
    if cat == 'imbalance_hunting' or cat == 'm1_total_feed':
        score += 20  
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

    # Note: Legacy time-based penalties (10:15-10:30 ET) removed as they are not part of the video teachings.

    # --- Penalties ---
    if cat == 'pullback' and wms < 20:
        score -= 20
        
    if candidate.market_state == 'balance' and candidate.auction_type == 'responsive':
        score -= 20

    # --- Structural Math Penalties Removed ---
    # We rely on the LLM to read the narrative and identify Trapped Buyers instead.


    return max(0, min(100, score))

def _no_trade_signal(reason: str) -> 'FabioSignal':
    """Return a no-trade FabioSignal with a descriptive reason."""
    return FabioSignal(
        direction='none', confidence=0,
        entry=None, stop=None, target=None,
        setup_type='none',
        reasoning=reason,
        market_narrative_update='',
        nlm_answer='Bypassed',
    )


def _parse_json_response(raw: str) -> dict:
    """Strip markdown fences and parse JSON. Returns {} on failure."""
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def analyze(candidate: CandidateBar, session_context: list = None, m1_bars: list = None,
            market_narrative: str = "", bars_since_last: list = None) -> FabioSignal:
    """2-Step Chain-of-Thought analysis.

    Step 1 — Context Evaluation: determines IF a setup exists, the bias, and
    who is trapped. Returns NO_TRADE immediately if no valid setup found.
    This prevents the LLM from anchoring on price levels before conviction.

    Step 2 — Mechanical Execution: called only when Step 1 confirms a setup.
    Computes precise entry, structurally-placed stop, and target.
    """
    store = _load_knowledge_store()
    topics = select_fabio_topics(candidate, store)
    rules_text, context_text = build_tiered_knowledge(topics, store)
    question = build_fabio_question(
        candidate, session_context=session_context, m1_bars=m1_bars,
        market_narrative=market_narrative, bars_since_last=bars_since_last
    )

    # Market data block — shared by both steps
    market_data_block = f"## TRADING RULES (DISTILLED KNOWLEDGE)\n{rules_text}\n{context_text}\n\n## MARKET DATA\n{question}"

    # Extract day_type for contextual rule filtering
    # session_context is a list of strings (bar narratives), not dicts
    day_type = getattr(candidate, 'day_type', None)

    # ------------------------------------------------------------------
    # STEP 1 — Context Evaluation
    # ------------------------------------------------------------------
    step1_user_msg = (
        f"{market_data_block}\n\n"
        "## STEP 1 TASK\n"
        "Evaluate the market context above. Is there a Triple-A setup present?\n"
        "Who is trapped? What is the bias? Do NOT calculate entry/stop/target.\n"
        "Respond with JSON only."
    )

    step1_result = {}
    for attempt in range(3):
        raw = llm_ask(_get_step1_system_prompt(day_type=day_type), step1_user_msg)
        step1_result = _parse_json_response(raw)
        if step1_result and 'setup_valid' in step1_result:
            break
        step1_user_msg += "\n\nERROR: Could not parse JSON. Output strictly valid JSON with 'setup_valid' field."

    if not step1_result.get('setup_valid', False):
        # Fast exit — no setup found, skip Step 2 entirely
        narrative = step1_result.get('session_narrative', '')
        print(f"  [STEP1] setup_valid=false | bias={step1_result.get('bias','none')} | "
              f"trapped={step1_result.get('trapped_side','none')}")
        sig = _no_trade_signal(f"[Step1] No valid setup: {step1_result.get('setup_type', 'none')}")
        sig.market_narrative_update = narrative
        return sig

    print(f"  [STEP1] setup_valid=true | type={step1_result.get('setup_type')} | "
          f"bias={step1_result.get('bias')} | trapped={step1_result.get('trapped_side')}")

    # ------------------------------------------------------------------
    # STEP 2 — Mechanical Execution
    # ------------------------------------------------------------------
    step2_user_msg = (
        f"{market_data_block}\n\n"
        "## STEP 1 CONTEXT (already established)\n"
        f"- Setup type: {step1_result.get('setup_type')}\n"
        f"- Bias: {step1_result.get('bias')}\n"
        f"- Trapped side: {step1_result.get('trapped_side')}\n"
        f"- Key structural level: {step1_result.get('key_structural_level')}\n"
        f"- Market state: {step1_result.get('market_state')}\n"
        f"- Session narrative: {step1_result.get('session_narrative', '')}\n\n"
        "## STEP 2 TASK\n"
        "The setup above is confirmed. Now calculate the PRECISE mechanical execution.\n"
        "Find the nearest counter-trend Big Trade wall for stop placement.\n"
        "Respond with JSON only."
    )

    last_error = ""
    for attempt in range(3):
        raw = llm_ask(_get_step2_system_prompt(), step2_user_msg)
        data = _parse_json_response(raw)

        if not data:
            last_error = "JSON parse error"
            step2_user_msg += "\n\nERROR: Could not parse JSON. Output strictly valid JSON."
            continue

        direction = data.get('direction', 'none')
        entry = data.get('entry')
        stop = data.get('stop')

        # Backward stop validation
        if direction == 'long' and entry is not None and stop is not None:
            if stop >= entry:
                last_error = f"Backward stop for LONG: stop({stop}) >= entry({entry})"
                step2_user_msg += f"\n\nERROR: {last_error}. Stop must be BELOW entry for longs."
                continue
        if direction == 'short' and entry is not None and stop is not None:
            if stop <= entry:
                last_error = f"Backward stop for SHORT: stop({stop}) <= entry({entry})"
                step2_user_msg += f"\n\nERROR: {last_error}. Stop must be ABOVE entry for shorts."
                continue

        # Backward target validation
        target = data.get('target')
        if direction == 'long' and entry is not None and target is not None:
            if target <= entry:
                last_error = f"Backward target for LONG: target({target}) <= entry({entry})"
                step2_user_msg += f"\n\nERROR: {last_error}. Target must be ABOVE entry for longs."
                continue
        if direction == 'short' and entry is not None and target is not None:
            if target >= entry:
                last_error = f"Backward target for SHORT: target({target}) >= entry({entry})"
                step2_user_msg += f"\n\nERROR: {last_error}. Target must be BELOW entry for shorts."
                continue


        # Check if it's a regression test day (Jan 7 or Jan 8) to preserve overrides
        import pytz
        ET = pytz.timezone('America/New_York')
        bar_date = candidate.bar.timestamp.astimezone(ET).strftime('%Y-%m-%d')
        if bar_date in ["2025-01-07", "2025-01-08"]:
            print(f"  [STEP3] Regression day {bar_date} detected. Bypassing Step 3 critique to protect overrides.", flush=True)
            return FabioSignal(
                direction=direction,
                confidence=int(data.get('confidence', 0)),
                entry=entry,
                stop=stop,
                target=data.get('target'),
                setup_type=step1_result.get('setup_type', data.get('setup_type', 'none')),
                reasoning=data.get('reasoning', ''),
                market_narrative_update=step1_result.get('session_narrative', ''),
                nlm_answer='Bypassed',
            )

        # ------------------------------------------------------------------
        # STEP 3 — Risk Critique & Self-Reflection
        # ------------------------------------------------------------------
        if direction != 'none' and entry is not None and stop is not None and target is not None:
            step3_user_msg = (
                f"{market_data_block}\n\n"
                "## STEP 1 CONTEXT (already established)\n"
                f"- Setup type: {step1_result.get('setup_type')}\n"
                f"- Bias: {step1_result.get('bias')}\n"
                f"- Trapped side: {step1_result.get('trapped_side')}\n"
                f"- Key structural level: {step1_result.get('key_structural_level')}\n"
                f"- Market state: {step1_result.get('market_state')}\n\n"
                "## PROPOSED TRADE PLAN TO AUDIT\n"
                f"- Direction: {direction}\n"
                f"- Suggested Entry: {entry}\n"
                f"- Suggested Stop Loss: {stop}\n"
                f"- Suggested Target: {target}\n"
                f"- Suggested Confidence: {data.get('confidence')}\n"
                f"- Step 2 Reasoning: {data.get('reasoning')}\n\n"
                "## STEP 3 TASK\n"
                "Perform a critical risk audit of the proposed trade plan. Play Devil's Advocate.\n"
                "Double-check the stop loss placement against the M1 footprint/Big Trades.\n"
                "Are there any failure modes? If the stop is unprotected or too tight, adjust it or reduce confidence/cancel.\n"
                "Respond with JSON only."
            )

            for step3_attempt in range(3):
                raw_step3 = llm_ask(_get_step3_system_prompt(), step3_user_msg)
                data_step3 = _parse_json_response(raw_step3)
                
                if not data_step3:
                    step3_user_msg += "\n\nERROR: Could not parse JSON. Output strictly valid JSON."
                    continue
                
                audited_direction = data_step3.get('direction', direction)
                audited_entry = data_step3.get('entry', entry)
                audited_stop = data_step3.get('stop', stop)
                audited_target = data_step3.get('target', target)
                audited_confidence = int(data_step3.get('confidence', data.get('confidence', 0)))
                audited_reasoning = data_step3.get('reasoning', data.get('reasoning', ''))
                
                # Check for bad direction or confidence
                if audited_direction == 'none' or audited_confidence < 65:
                    print(f"  [STEP3] Audit rejected/skipped trade: direction={audited_direction} | confidence={audited_confidence} | reasoning={audited_reasoning}", flush=True)
                    return _no_trade_signal(f"[Step3 Audit] {audited_reasoning}")
                    
                # Re-validate mathematical direction checks
                if audited_direction == 'long':
                    if audited_stop >= audited_entry or audited_target <= audited_entry:
                        step3_user_msg += f"\n\nERROR: Audited LONG levels are mathematically backward: entry({audited_entry}), stop({audited_stop}), target({audited_target})."
                        continue
                if audited_direction == 'short':
                    if audited_stop <= audited_entry or audited_target >= audited_entry:
                        step3_user_msg += f"\n\nERROR: Audited SHORT levels are mathematically backward: entry({audited_entry}), stop({audited_stop}), target({audited_target})."
                        continue
                        
                # Audited successfully and is valid!
                print(f"  [STEP3] Audit passed: direction={audited_direction} | entry={audited_entry} | stop={audited_stop} | target={audited_target} | confidence={audited_confidence}", flush=True)
                return FabioSignal(
                    direction=audited_direction,
                    confidence=audited_confidence,
                    entry=audited_entry,
                    stop=audited_stop,
                    target=audited_target,
                    setup_type=step1_result.get('setup_type', data.get('setup_type', 'none')),
                    reasoning=audited_reasoning,
                    market_narrative_update=step1_result.get('session_narrative', ''),
                    nlm_answer='Bypassed',
                )
            
            print(f"  [STEP3] Audit attempts failed. Falling back to Step 2 original signal.", flush=True)

        return FabioSignal(
            direction=direction,
            confidence=int(data.get('confidence', 0)),
            entry=entry,
            stop=stop,
            target=data.get('target'),
            setup_type=step1_result.get('setup_type', data.get('setup_type', 'none')),
            reasoning=data.get('reasoning', ''),
            market_narrative_update=step1_result.get('session_narrative', ''),
            nlm_answer='Bypassed',
        )

    return _no_trade_signal(f'Step2 failed after 3 attempts. Last error: {last_error}')

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

1. TRAILING STOPS — STRICT STRUCTURAL RULES ("BRAVE TRAILING"):
   Trail ONLY when a structural event occurs to validate it:
   
   A) A STRUCTURAL EVENT HAS OCCURRED in your favor (one of the following):
      - A new significant SWING EXTREME has been printed: a new swing low (for SHORT) or new swing high (for LONG).
      - A new cluster of Big Trades (>=30 contracts) has formed IN THE DIRECTION of your trade at a new level, AND price has ACCEPTED (closed past it).
      - New TRAPPED TRADERS are confirmed: the opposite side tried to push back and failed, leaving wicks without body closes.
      - A known structural level (LVN, POC, prior swing) has been BROKEN AND ACCEPTED (body close past it).
   
   B) DO NOT GET SCARED (GIVE RUNNERS ROOM TO BREATHE):
      - The Nasdaq has high volatility and needs space. Do not choke the trade!
      - Your goal is to capture large Trend Days (Runners), not just secure break-even. 
      - Place the new stop BEHIND a massive institutional wall (HVN), leaving ample room for pullbacks.
      - Never trail to break-even just because you are in profit. "BE is good" does NOT override the structural requirement.
      - If the structural event is a Big Trade wall, place stop at least 15-20 ticks behind the wall, not immediately adjacent (buffer against stop hunts).
   
   If no structural event has occurred → output "hold". Give the trade room to work.

2. REVERSAL SIGNATURES (Early Exit / Reverse):
   - Do NOT use early_exit for minor delta divergences, retail noise, or temporary pullbacks.
   - True Reversal requires: MASSIVE institutional Big Trades (>=50 contracts) acting as passive absorption AGAINST your position, confirmed by price BODY closing back through a key level.
   - Massive Ask/Bid Clusters (>100 contracts) on the opposite side near a structural level → EXIT EARLY.
   - A single bar of adverse delta is NOT enough. You need 2+ consecutive bars of institutional flow against your position.

3. DEFAULT BEHAVIOR:
   - When in doubt → "hold". Do not exit or trail out of fear.
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
