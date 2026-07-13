import json
from pathlib import Path
from src import CandidateBar, FabioSignal, FABIO_NOTEBOOK_ID
from src.agents.llm_client import llm_ask
from src.signal_context import build_fabio_question
# Note: light_analyze is now fully deterministic (no LLM calls)

KNOWLEDGE_FILE = Path(__file__).parent.parent.parent / 'knowledge' / 'fabio_core_rules.json'

def get_formatted_rules() -> str:
    """Load and format fabio_core_rules.json into a Markdown string."""
    try:
        with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
            rules = json.load(f)
        
        md = []
        # System Overview
        sys = rules.get("system_overview", {})
        md.append("### SYSTEM OVERVIEW")
        md.append(f"- **Model Overview**: {sys.get('model_overview', '')}")
        md.append(f"- **IB Structure**: {sys.get('ib_structure', '')}")
        md.append(f"- **Day Types**: {sys.get('day_types', '')}")
        
        lq = sys.get("liquidity_mapping_rules", {})
        md.append("- **Liquidity Mapping Rules**:")
        md.append(f"  - Stop Loss Placement: {lq.get('stop_loss_placement', '')}")
        md.append(f"  - Take Profit Placement: {lq.get('take_profit_placement', '')}")
        md.append("")
        
        # Execution Rules
        exec_r = rules.get("execution_rules", {})
        md.append("### EXECUTION RULES")
        md.append(f"- **Trigger & Timing**: {exec_r.get('trigger_and_timing', '')}")
        md.append(f"- **Predatory Execution**: {exec_r.get('predatory_execution', '')}")
        md.append(f"- **Big Trades Filter**: {exec_r.get('big_trades_filter', '')}")
        md.append(f"- **Coherence**: {exec_r.get('coherence', '')}")
        md.append(f"- **Counter Trend**: {exec_r.get('counter_trend', '')}")
        md.append("")
        
        # Strategies
        md.append("### CORE SETUP CLASSIFICATIONS")
        for i, s in enumerate(rules.get("strategies", []), 1):
            md.append(f"{i}. {s.get('name', '')} ({s.get('description', '')}):")
            md.append(f"   - Trigger: {s.get('trigger', '')}")
            md.append(f"   - Confirmation: {s.get('confirmation', '')}")
        md.append("")
        
        # Market Mechanics
        mech = rules.get("market_mechanics", {})
        md.append("### MARKET MECHANICS")
        md.append(f"- **Punch In The Wall**: {mech.get('punch_in_the_wall', '')}")
        md.append(f"- **Imbalance Hunting**: {mech.get('imbalance_hunting', '')}")
        md.append(f"- **Initiative vs Absorption**: {mech.get('initiative_vs_absorption', '')}")
        
        return "\n".join(md)
    except Exception as e:
        print(f"Error reading or formatting {KNOWLEDGE_FILE}: {e}")
        return "Error loading trading rules."

import os as _os

_LANG_SUFFIX = {
    'zh': '\n\n⚠️ 重要：你的所有回答必须完全使用中文（普通话）。请用中文回答以上所有内容。',
    'en': '\n\n⚠️ IMPORTANT: Your entire response MUST be in English only. Respond in English.',
}

def _get_system_prompt() -> str:
    prompt = """You are Fabio Valentini's PREDATORY trading methodology agent analyzing NQ futures (E-mini).
You follow a high-conviction institutional approach based on Volume Profile and Order Flow, aiming strictly for high-probability Triple A (A+) setups.

⚠️ DETAILED CHAIN OF THOUGHT (EXTENDED REASONING):
- You must produce a deep, articulate, and discursive analysis of the market structure and order flow.
- Explain your reasoning step by step. Do not rush.
- You are encouraged to provide detailed market commentaries, building a coherent narrative of what the buyers and sellers are doing.

⚠️ PREDATORY PATIENCE (ANTI-FOMO):
- Do NOT be hasty or premature in classification. 
- For Second Drive/Breakout/Squeeze: You MUST wait for completed absorption of aggressive buyers/sellers and aligned micro-structure (M1 candle body and POC closing in trade direction). If confirmations are incomplete, output direction="none".
"""
    
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


    # Load Core Rules from fabio_core_rules.json
    if KNOWLEDGE_FILE.exists():
        try:
            with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
                rules = json.load(f)
                
                # Strategies
                strats = rules.get('strategies', [])
                if strats:
                    prompt += "CORE SETUP CLASSIFICATIONS (TRIPLE A SETUPS):\n"
                    for i, s in enumerate(strats, 1):
                        prompt += f"{i}. {s['name']} ({s['description']}):\n"
                        prompt += f"   - Trigger: {s['trigger']}\n"
                        prompt += f"   - Confirmation: {s['confirmation']}\n"
                    prompt += "\n"
                
                # Mechanics & Overview
                sys = rules.get('system_overview', {})
                prompt += f"SYSTEM OVERVIEW:\n- Model: {sys.get('model_overview', '')}\n- IB Structure: {sys.get('ib_structure', '')}\n- Day Types: {sys.get('day_types', '')}\n"
                lq = sys.get('liquidity_mapping_rules', {})
                prompt += f"- Stop Loss Placement: {lq.get('stop_loss_placement', '')}\n- Take Profit Placement: {lq.get('take_profit_placement', '')}\n\n"
                
                exec_r = rules.get('execution_rules', {})
                prompt += f"EXECUTION RULES:\n- Trigger & Timing: {exec_r.get('trigger_and_timing', '')}\n- Predatory Execution: {exec_r.get('predatory_execution', '')}\n- Big Trades Filter: {exec_r.get('big_trades_filter', '')}\n- Coherence: {exec_r.get('coherence', '')}\n- Counter Trend: {exec_r.get('counter_trend', '')}\n\n"
                
                mechs = rules.get('market_mechanics', {})
                prompt += "MARKET MECHANICS:\n"
                for topic, desc in mechs.items():
                    prompt += f"- {topic.upper()}: {desc}\n"
                prompt += "\n"
        except Exception as e:
            print(f"Error loading fabio_core_rules.json in system prompt: {e}")

    # Statistical calibration hints (derived from 549 backtested trades)
    prompt += """BACKTEST CONVICTION PRIORS:
1. IB + VA convergence is premium (59% WR). VAL/VAH alone without IB = weak (-15 conf).
2. Big Trade size >= 1000 = strong. High volume but small Big Trade = retail trap (-10 conf).
3. |Delta| >= 600 = directional commitment. |Delta| < 300 = chop (-10 conf).

TEMPORAL AUDIT (0-100%):
- q1: Time is outside Lunch Lull (12:00-13:30 ET), before 13:00 ET cutoff (or Power Hour exception), and before 15:00 ET.
- q2: Outside 10:15-10:30 ET Kill Zone (unless overridden by fresh strong breakout).
- q3: Clear initiative/momentum. Expansive delta aligned with price, or clear absorption.
- q4: Trend-aligned OR premium Reversal at major extremes (Overnight H/L, IB edges, VAH/VAL) with clear wicks >=35% and absorption (score q4: 70-90%, setup_type='reversal').
- q5: Entry precision at major structure.

STOP LOSS & TARGET STRUCTURAL MAPPING:
- Stop Loss: Place structurally behind the closest High Volume Node (HVN) or the defending Big Trade absorption wall. Standard placement is 2-3 ticks behind the node/wall extreme (standard 10-20 ticks, absolute max 120 ticks).
- Take Profit: Project targets prioritizing Low Volume Node (LVN) liquidity voids or towards opposite Value Area / Initial Balance extremes where price travels fast.
"""
    # Language-aware schema instructions
    import os as _os2
    _l = _os2.environ.get('BACKTEST_LANG', '').lower().strip()
    if _l == 'zh':
        _reasoning_instr = '<中文，详细构建流畅的推导过程。详细分析大单、Delta及市场结构（吸收与主动）。如果建议交易（多/空），请从结构上论证止损（放在HVN/大单墙后）和目标位（朝向LVN或对侧边界）。CRITICAL: 如果方向为"none"，请勿写长篇大论，仅用1-2句简明扼要的话解释为什么当前背景缺乏高置信度设置，以最大程度减少输出延迟。>'
        _audit_instr     = 'q1:XX%, q2:XX%, q3:XX%, q4:XX%, q5:XX% （明确计算5个因素的百分比）'
        _narrative_instr = '<中文，详细描述盘面流向、POC迁移以及M5 and M1之间的流向一致性。CRITICAL: 如果方向为"none"，仅用1-2句简明扼要的话概括 session 状态，以减少输出延迟。>'
    elif _l == 'en':
        _reasoning_instr = '<EXTENDED THOUGHT. Detail your step-by-step reasoning in a discursive, narrative style about delta, big trades, and market structure (absorption vs initiative). If proposing a trade (long/short), justify the Stop Loss structurally (behind HVN/wall) and the Target (projected towards LVN or opposite extremes). CRITICAL: If direction is "none", do not write a long paragraph; instead, summarize in exactly 1-2 concise sentences why the setup lacks conviction to minimize output latency.>'
        _audit_instr     = 'q1:XX%, q2:XX%, q3:XX%, q4:XX%, q5:XX% (calculate percentages for all 5 factors)'
        _narrative_instr = '<EXTENDED NARRATIVE. Describe the session flow, POC migration, and volume flow alignment between M5 and M1 in detail. CRITICAL: If direction is "none", summarize the session state in exactly 1-2 concise sentences to minimize output latency.>'
    else:  # default: Italian
        _reasoning_instr = '<PENSIERO ESTESO. Spiega dettagliatamente e in modo discorsivo il tuo ragionamento su delta, big trades e struttura di mercato (assorbimento vs iniziativa). Se proponi un\'entrata (long/short), giustifica lo Stop Loss (dietro HVN/muro) e il Target (proiettato verso LVN o estremi). CRITICAL: Se la direzione è "none", NON scrivere un paragrafo lungo; riassumi in esattamente 1-2 frasi concise il motivo per cui manca la convinzione per minimizzare la latenza di output.>'
        _audit_instr     = 'q1:XX%, q2:XX%, q3:XX%, q4:XX%, q5:XX% (calcola le percentuali per i 5 fattori)'
        _narrative_instr = '<NARRATIVA ESTESA. Descrivi l\'andamento della sessione, la migrazione del POC e l\'allineamento M5-M1 in dettaglio. CRITICAL: Se la direzione è "none", riassumi lo stato della sessione in esattamente 1-2 frasi concise per minimizzare la latenza di output.>'
    
    _speed_rule = ''

    prompt += f"""Respond ONLY with valid JSON matching this schema:
{{
  "direction": "long" | "short" | "none",
  "confidence": <int 0-100>,
  "entry": <float or null>,
  "stop": <float or null>,
  "target": <float or null>,
  "setup_type": "squeeze" | "ivb_breakout" | "none",
  "imbalance_phase": "expansive" | "accumulation" | "none",
  "reasoning": "{_reasoning_instr}",
  "temporal_audit": "{_audit_instr}",
  "market_narrative_update": "{_narrative_instr}",
  "session_verdict": "continue" | "stop"
}}
{_speed_rule}

Decidi se continuare a monitorare la sessione oltre l'orario standard: 'continue' se la giornata è volatile con forti volumi e setup istituzionali pendenti/attivi, 'stop' se la giornata è choppy, priva di volumi o se ritieni che l'attività istituzionale sia conclusa."""
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
    if str(cat).startswith('liquidity_map_'):
        score += 60  # Tier 1 Institutional footprint!
    elif cat == 'imbalance_hunting':
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

def analyze(candidate: CandidateBar, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None) -> FabioSignal:
    rules_text = get_formatted_rules()
    question = build_fabio_question(candidate, session_context=session_context, m1_bars=m1_bars, market_narrative=market_narrative, bars_since_last=bars_since_last)
    
    # Bypass NotebookLM: inject distilled knowledge directly
    base_user_msg = f"## TRADING RULES (DISTILLED KNOWLEDGE)\n{rules_text}\n\n## TASK\n{question}\n\nAnalyze this setup using the Rules above. Respond with JSON only."
    
    # Inject language instruction at END of user message (model follows last instruction)
    _lang = _os.environ.get('BACKTEST_LANG', '').lower().strip()
    lang_suffix = _LANG_SUFFIX.get(_lang, '')
    user_msg = base_user_msg + lang_suffix
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
            temporal_audit = data.get('temporal_audit', '')
            if temporal_audit:
                base_reasoning += f"\n\n[Audit Fase Temporale]\n{temporal_audit}"
            return FabioSignal(
                direction   = direction,
                confidence  = int(data.get('confidence', 0)),
                entry       = entry,
                stop        = stop,
                target      = data.get('target'),
                setup_type  = data.get('setup_type', 'none'),
                imbalance_phase = imbalance_phase,
                reasoning   = base_reasoning,
                market_narrative_update = data.get('market_narrative_update', ''),
                nlm_answer  = "Bypassed",
                session_verdict = data.get('session_verdict', 'continue'),
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
    if not prompt_file.exists():
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(DEFAULT_MANAGEMENT_SYSTEM_PROMPT)
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read().strip()

DEFAULT_MANAGEMENT_SYSTEM_PROMPT = """You are Fabio Valentini's active risk management agent managing an open NQ futures position.
Your goal is to protect capital and maximize returns based on real-time Volume Profile and Order Flow.
You must analyze the open trade details and the latest M5 candle/M1 footprint to choose one of these actions:
1. "hold": Keep the position exactly as is. DEFAULT action when no structural event has occurred.
2. "trail": Move the stop loss structurally ÔÇö but ONLY when strict conditions are met (see below).
3. "early_exit": Exit the trade immediately because the setup has been structurally invalidated.
4. "reverse": Exit current trade and open the opposite position on a strong reversal signature.

--- ACTIVE POSITION MANAGEMENT (APM) ---

1. TRAILING STOPS ÔÇö STRICT STRUCTURAL RULES:
   Trail ONLY when ALL THREE of the following conditions are simultaneously true:
   
   A) MINIMUM 1:1 RISK/REWARD REACHED:
      - The trade must have moved at least 1x the initial risk in your favor before any trailing is allowed.
      - Example: Entry=25000 SHORT, initial Stop=25040 (risk=40pts). Trail only activates if price reaches 24960 or below (1:1).
      - If 1:1 is NOT reached ÔåÆ always output "hold". No exceptions.
   
   B) A STRUCTURAL EVENT HAS OCCURRED in your favor (one of the following):
      - A new significant SWING EXTREME has been printed: a new swing low (for SHORT) or new swing high (for LONG).
      - A new cluster of Big Trades (>=30 contracts) has formed IN THE DIRECTION of your trade at a new level, AND price has ACCEPTED (closed past it).
      - New TRAPPED TRADERS are confirmed: the opposite side tried to push back and failed, leaving wicks without body closes.
      - A known structural level (LVN, POC, prior swing) has been BROKEN AND ACCEPTED (body close past it).
   
   C) STOP PLACEMENT MUST GIVE BREATHING ROOM:
      - Place the new stop BEHIND the structural event ÔÇö not 2-4 ticks behind a single bar's wall.
      - Minimum distance: behind the wick/extreme of the structural event candle, or behind the Big Trade cluster origin.
      - Never trail to break-even UNLESS a full structural event has occurred. "BE is good" does NOT override the structural requirement.
      - If the structural event is a Big Trade wall, place stop at least 15-20 ticks behind the wall, not immediately adjacent (buffer against stop hunts).
   
   If any of A, B, or C is NOT met ÔåÆ output "hold". Give the trade room to work.

2. REVERSAL SIGNATURES (Early Exit / Reverse):
   - Do NOT use early_exit for minor delta divergences, retail noise, or temporary pullbacks.
   - True Reversal requires: MASSIVE institutional Big Trades (>=50 contracts) acting as passive absorption AGAINST your position, confirmed by price BODY closing back through a key level.
   - Massive Ask/Bid Clusters (>100 contracts) on the opposite side near a structural level ÔåÆ EXIT EARLY.
   - A single bar of adverse delta is NOT enough. You need 2+ consecutive bars of institutional flow against your position.

3. DEFAULT BEHAVIOR:
   - When in doubt ÔåÆ "hold".
   - Only trail when the market has PROVEN the structural event with ACCEPTED price action (body close, not just a wick).
   - Premature trailing is worse than a stop loss: it guarantees a scratch on a potentially great trade.

Respond ONLY with valid JSON matching this schema:
{
  "decision": "hold" | "trail" | "early_exit" | "reverse",
  "new_stop": <float or null (only if trailing, must give structural breathing room)>,
  "new_target": <float or null (optional)>,
  "rr_reached": <float ÔÇö current R:R achieved at this bar, e.g. 1.2>,
  "structural_event": "<describe the structural event that triggered trail, or 'none'>",
  "reasoning": "<MAX 80 WORDS. Cite R:R ratio, the specific structural event (or why holding), Big Trade levels, and exact stop placement logic.>"
}"""


def manage_active_trade(trade, candidate: CandidateBar, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None) -> dict:
    """Ask Fabio to manage the active trade based on the latest bar activity."""
    rules_text = get_formatted_rules()
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
    
    user_msg = f"## TRADING RULES (DISTILLED KNOWLEDGE)\n{rules_text}\n{trade_context}\n\n## TASK\n{question}\n\nAnalyze this active position and choose one of the actions: 'hold', 'trail', 'early_exit', or 'reverse'. Respond with JSON only."
    
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


def _get_auditor_system_prompt() -> str:
    return """You are the Lead Risk Auditor for Fabio Valentini's predatory trading desk.
Your job is to perform a rigorous second-stage audit of a trade proposed by our Reflex model.
You have the final authority to confirm the trade, veto it (canceling it immediately), or optimize/adjust its Stop Loss (SL) and Take Profit (TP) levels to match the structural extremes (such as POC overnight, IB edges, VA boundaries, or key Big Trade walls).

Respond ONLY with valid JSON matching this schema:
{
  "decision": "confirm" | "veto",
  "adjusted_stop": <float or null (provide a float value to update/adjust the Stop Loss structural level, or null to keep original)>,
  "adjusted_target": <float or null (provide a float value to update/adjust the Target structural level, or null to keep original)>,
  "reasoning": "<Explain in detail why you decided to confirm, veto, or modify the stop/target. Quote relevant order flow and structural facts. Do not limit your length.>"
}"""


def deep_audit(candidate: CandidateBar, reflex_signal: FabioSignal, session_context: list = None, m1_bars: list = None, market_narrative: str = "", bars_since_last: list = None) -> dict:
    """Perform a deep structural audit of a proposed reflex trade using GLM 5.2 with full context."""
    rules_text = get_formatted_rules()
    question = build_fabio_question(candidate, session_context=session_context, m1_bars=m1_bars, market_narrative=market_narrative, bars_since_last=bars_since_last)
    
    # Format M1 sequence text for the prompt
    from src.signal_context import _format_m1_sequence
    m1_sequence_text = _format_m1_sequence(m1_bars) if m1_bars else "No M1 sequence context."
    
    # Session Context parameters
    import pytz
    ET = pytz.timezone('US/Eastern')
    
    user_msg = f"""## TRADING RULES (DISTILLED KNOWLEDGE)
{rules_text}

## PROPOSED TRADE FROM REFLEX MODEL
Direction: {reflex_signal.direction.upper()}
Proximity: {candidate.proximity_to.upper()} near {candidate.proximity_level:.2f}
Suggested Entry: {reflex_signal.entry}
Suggested Stop: {reflex_signal.stop}
Suggested Target: {reflex_signal.target}

## SESSION CONTEXT DATA
- Date: {candidate.bar.timestamp.strftime('%Y-%m-%d')}
- Bar Time: {candidate.bar.timestamp.astimezone(ET).strftime('%H:%M')} ET
- Current Price: {candidate.bar.close}
- Developing POC: {candidate.session_ctx.vp.poc if candidate.session_ctx.vp else 'N/A'}
- IB boundaries: Low={candidate.session_ctx.ib_low}, High={candidate.session_ctx.ib_high}
- Institutional footprint (Recent M1 sequence):
{m1_sequence_text}

## AUDIT TASK
Perform a deep structural analysis using the Rules above.
1. Is this a fakeout/trap? (If yes, output veto).
2. Does the order flow (big trades/delta) confirm absorption or initiative?
3. Check the stop loss: is it placed structurally behind the defending wall/IB boundary? If not, adjust it.
4. Check the target: is there a structural logic for the target? If not, adjust it.
Respond with JSON only.
"""
    
    # Force GLM 5.2 via OpenRouter for high-conviction audit
    import os
    model = "z-ai/glm-5.2"
    
    raw = llm_ask(_get_auditor_system_prompt(), user_msg, model=model)
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()
        
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"  [DEEP AUDIT ERROR] Failed to parse auditor JSON: {raw[:150]}")
        return {
            "decision": "confirm",  # Safe fallback: keep the trade if auditor fails
            "adjusted_stop": None,
            "adjusted_target": None,
            "reasoning": f"JSON parse error: {raw[:80]}"
        }
        
    return {
        "decision": data.get("decision", "confirm"),
        "adjusted_stop": data.get("adjusted_stop"),
        "adjusted_target": data.get("adjusted_target"),
        "reasoning": data.get("reasoning", "")
    }

