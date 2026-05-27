"""
Precision Entry Agent — M1 refinement after M5 consensus.

After Fabio+Andrea agree on a trade direction at M5 level, this agent
drops to 1-minute bars to find:
  1. Exact entry price (based on institutional wall position in M1)
  2. Tight stop (behind the M1 big-trade cluster)
  3. Reasoned target (based on knowledge + session structure)

This replaces Fabio's M5-estimated entry/stop/target with precise M1 levels.
"""
import json
from pathlib import Path
from src import (Bar, CandidateBar, ConsensusSignal, SessionContext,
                 NQ_BIG_TRADE_THRESHOLD, NQ_TICK_SIZE)
from src.agents.llm_client import llm_ask
from src.agents.topic_router import build_knowledge_text

KNOWLEDGE_FILE = Path(__file__).parent.parent.parent / 'knowledge' / 'fabio_distilled.json'

_knowledge_cache = None

def _load_knowledge_store() -> dict:
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


# Topics selected for precision entry — focused on micro execution
def _select_precision_topics(day_type: str, setup_type: str) -> list[str]:
    """Select knowledge topics relevant to precision entry/stop/target."""
    topics = [
        'entry_mechanics',
        'stop_placement',
    ]
    # Target selection based on day type
    if day_type in ('trend_up', 'trend_down'):
        topics.append('targets_high_volatility')
    else:
        topics.append('targets_standard')

    # Setup-specific micro knowledge
    if setup_type == 'squeeze':
        topics.extend(['squeeze_entry_trigger', 'trapped_buyers', 'trapped_sellers'])
    elif setup_type == 'ivb_breakout':
        topics.extend(['ib_extension_targets', 'second_drive'])
    elif setup_type == 'failed_auction':
        topics.extend(['squeeze_vs_failed_auction', 'pre_explosion_pattern'])

    # Always include the real trade example for calibration
    topics.append('simplified_real_trade_example')
    return topics


SYSTEM_PROMPT = """You are a precision execution agent for NQ futures, applying Fabio Valentini's methodology at the 1-minute level.

The M5 analysis has already confirmed a trade direction. Your job is to:
1. Analyze the M1 bars AFTER the M5 candidate bar closes (the "Initiative" window).
2. Find the EXACT entry price — prioritizing the first instance of Diagonal Imbalance (aggressive delta follow-through).
3. Place the stop SURGICALLY behind the 'Structural Ledge' (the LVN or volume cluster) identified in the context.

RULES V3.1 (STRICT):
- ANTI-SWEEP (M1 BODY CLOSE): Do NOT enter on a mere wick probe. The M1 candle must CLOSE in your direction to confirm price acceptance. If it's a long shadow (wick) with no close acceptance, skip the trade.
- STRUCTURAL SL (ANTI-NOISE): Fixed tick stops (15/20/35) are strictly prohibited. The stop must sit behind a structural wall (Big Trade cluster >= 30 contracts) or the Ledge level provided by Andrea.
- INITIATIVE CONFIRMATION: Wait for at least ONE M1 bar to close beyond the 'Wall' to ensure we aren't being trapped in an absorption phase.
- TOXIC FLOW: If M1 volume is < 300, abort (entry=null, abort=true).

Respond ONLY with valid JSON:
{
  "entry": <float | null>,
  "stop": <float>,
  "target": <float>,
  "abort": <bool>,
  "entry_reasoning": "<1-2 sentences: confirm M1 body close and volume participation>",
  "stop_reasoning": "<1-2 sentences: identify the structural ledge/cluster protecting the stop>",
  "target_reasoning": "<1-2 sentences: why this target (POC/Opposite VA)>"
}"""


def _format_m1_bars(bars: list[Bar], direction: str) -> str:
    """Format M1 bars with big trade detail for the precision agent."""
    import pytz
    ET = pytz.timezone('America/New_York')
    lines = ["M1 bar sequence (oldest -> newest):"]
    for b in bars:
        t_et = b.timestamp.astimezone(ET)
        big_info = ""
        if b.big_trades:
            details = []
            for t in b.big_trades:
                side_label = "BUY" if t.side == 'A' else "SELL"
                details.append(f"{t.size}@{t.price:.2f}({side_label})")
            big_info = f" | BIG_TRADES=[{', '.join(details)}]"
        lines.append(
            f"  {t_et.strftime('%H:%M:%S')} O={b.open:.2f} H={b.high:.2f} "
            f"L={b.low:.2f} C={b.close:.2f} V={b.volume} "
            f"delta={b.delta:+d}{big_info}"
        )
    return "\n".join(lines)


def refine_entry(candidate: CandidateBar,
                 consensus: ConsensusSignal,
                 m1_bars: list[Bar]) -> dict:
    """Refine entry/stop/target using M1 bars after M5 consensus approves a trade.

    Args:
        candidate: The M5 CandidateBar that triggered the trade
        consensus: The approved ConsensusSignal from Fabio+Andrea
        m1_bars: 1-minute bars covering the M5 candidate bar +/- context

    Returns:
        dict with keys: entry, stop, target, abort, entry_reasoning,
        stop_reasoning, target_reasoning. If abort=True, trade should be skipped.
    """
    store = _load_knowledge_store()
    topics = _select_precision_topics(
        candidate.session_ctx.day_type,
        consensus.fabio.setup_type,
    )
    knowledge = build_knowledge_text(topics, store)

    ctx = candidate.session_ctx
    vp = ctx.vp

    m1_text = _format_m1_bars(m1_bars, consensus.direction)

    # Count big trades in M1 window
    all_bigs = []
    for b in m1_bars:
        for t in b.big_trades:
            all_bigs.append(t)
    buy_bigs = sum(t.size for t in all_bigs if t.side == 'A')
    sell_bigs = sum(t.size for t in all_bigs if t.side == 'B')

    user_msg = f"""## Precision Entry Knowledge
{knowledge}

## M5 Consensus (already confirmed)
Direction: {consensus.direction}
M5 Entry: {consensus.entry} | M5 Stop: {consensus.stop} | M5 Target: {consensus.target}
Andrea Structural SL: {consensus.andrea.structural_stop if consensus.andrea.structural_stop else 'not provided'}
Setup: {consensus.fabio.setup_type} | Confidence: {consensus.final_confidence}
Fabio reasoning: {consensus.fabio.reasoning}

## Session Structure
Day type: {ctx.day_type}
IB: {ctx.ib_low:.2f} - {ctx.ib_high:.2f} (range={ctx.ib_range:.0f} pts)
POC: {vp.poc:.2f} | VA: {vp.va_low:.2f} - {vp.va_high:.2f}
LVN levels: {[f'{l:.2f}' for l in vp.lvn_levels] if vp.lvn_levels else 'none'}
HVN levels: {[f'{l:.2f}' for l in vp.hvn_levels] if vp.hvn_levels else 'none'}

## M1 Institutional Activity
Total big trades: {len(all_bigs)} ({buy_bigs} buy / {sell_bigs} sell contracts)

## M1 Bar Data
{m1_text}

Based on the M1 data, find the precise entry, stop, and target. Respond with JSON only."""

    try:
        raw = llm_ask(SYSTEM_PROMPT, user_msg)
        if raw.startswith('```'):
            raw = raw.split('```')[1].lstrip('json').strip()
        data = json.loads(raw)
    except Exception as e:
        print(f"  [PRECISION ERROR] LLM or parsing failed: {e}. Falling back to default levels.", flush=True)
        return {
            'entry': consensus.entry,
            'stop': consensus.stop,
            'target': consensus.target,
            'abort': False,
            'entry_reasoning': f"Fallback due to LLM error or parsing failure: {e}",
            'stop_reasoning': 'Fallback to M5',
            'target_reasoning': 'Fallback to M5',
        }

    # Extract abort flag first
    abort = bool(data.get('abort', False))
    
    # RULE: High-confidence consensus override (>=85)
    # If Fabio's confidence is very high, we DO NOT allow M1 precision to abort the trade.
    is_high_confidence = getattr(consensus, 'final_confidence', 0) >= 85
    if is_high_confidence and (abort or data.get('entry') is None):
        print(f"  [PRECISION OVERRIDE] High confidence ({consensus.final_confidence} >= 85) overrides M1 abort request.", flush=True)
        abort = False
        data['entry'] = consensus.entry
        data['stop'] = consensus.stop
        data['target'] = consensus.target
        data['entry_reasoning'] = f"High confidence override: {data.get('entry_reasoning', 'M1 abort request bypassed')}"

    # If explicitly aborted or entry is missing/null, trigger the abort flow
    if abort or data.get('entry') is None:
        return {
            'entry': 0.0,
            'stop': 0.0,
            'target': 0.0,
            'abort': True,
            'entry_reasoning': data.get('entry_reasoning', 'Manual or logic-based abort during M1 refinement.'),
            'stop_reasoning': 'N/A',
            'target_reasoning': 'N/A',
        }

    # Extract final values
    entry_val = float(data.get('entry', consensus.entry))
    stop_val = float(data.get('stop', consensus.stop))
    target_val = float(data.get('target', consensus.target))

    # RULE: Minimum Stop Loss Distance (40 ticks / 10 points)
    # Prevent tight stop-outs from noise by enforcing a structural floor.
    MIN_STOP_TICKS = 40
    NQ_TICK_SIZE = 0.25
    MIN_STOP_DIST = MIN_STOP_TICKS * NQ_TICK_SIZE
    
    actual_stop_dist = abs(entry_val - stop_val)
    if actual_stop_dist < MIN_STOP_DIST:
        direction = consensus.direction
        print(f"  [PRECISION SAFETY] Adjusting ultra-tight stop ({actual_stop_dist:.2f} < {MIN_STOP_DIST:.2f}) to minimum {MIN_STOP_TICKS} ticks floor.", flush=True)
        if direction == 'long':
            stop_val = entry_val - MIN_STOP_DIST
        elif direction == 'short':
            stop_val = entry_val + MIN_STOP_DIST

    return {
        'entry': entry_val,
        'stop': stop_val,
        'target': target_val,
        'abort': False,
        'entry_reasoning': data.get('entry_reasoning', ''),
        'stop_reasoning': data.get('stop_reasoning', '') + f" [Safety stop floor applied if adjusted]",
        'target_reasoning': data.get('target_reasoning', ''),
    }


def get_m1_context(bars_1min: list[Bar], m5_bar: Bar,
                   context_before: int = 1, context_after: int = 10) -> list[Bar]:
    """Extract M1 bars around the M5 candidate bar timestamp.

    By default, focuses on 1 min before and 10 mins after the M5 bar start, 
    ensuring we capture the "Initiative" window after the M5 close.
    """
    from datetime import timedelta
    m5_start = m5_bar.timestamp
    m5_end = m5_start + timedelta(minutes=5)
    window_start = m5_start - timedelta(minutes=context_before)
    window_end = m5_end + timedelta(minutes=context_after)

    return [b for b in bars_1min
            if window_start <= b.timestamp < window_end]
