import json
from pathlib import Path
from datetime import timezone
import pytz
from src import CandidateBar, FabioSignal, Bar

ET = pytz.timezone('America/New_York')
STRATEGY_FILE = Path(__file__).parent.parent / 'strategies' / 'fabio_andrea_hybrid.json'

def _load_templates() -> dict:
    try:
        with open(STRATEGY_FILE, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Strategy file not found: {STRATEGY_FILE}") from None
    except json.JSONDecodeError as e:
        raise ValueError(f"Strategy file is invalid JSON ({STRATEGY_FILE}): {e}") from e

def _format_m5_sequence(bars: list) -> str:
    """Format a list of M5 bars as a readable sequence for agent context."""
    lines = ["M5 bar sequence (oldest -> newest):"]
    for b in bars:
        t_et = b.timestamp.astimezone(ET)
        big_info = ""
        if b.big_trades:
            total_big = sum(t.size for t in b.big_trades)
            sides = {'A': 0, 'B': 0}
            for t in b.big_trades:
                sides[t.side] = sides.get(t.side, 0) + t.size
            big_info = f" | BIG={total_big} (buy={sides.get('A',0)} sell={sides.get('B',0)})"
        marker = " <-- CANDIDATE" if b is bars[-1] else ""
        lines.append(
            f"  {t_et.strftime('%H:%M')} O={b.open:.2f} H={b.high:.2f} "
            f"L={b.low:.2f} C={b.close:.2f} V={b.volume} "
            f"delta={b.delta:+d}{big_info}{marker}"
        )
    return "\n".join(lines)

def _format_m1_sequence(bars: list[Bar], hide_historical_delta: bool = False) -> str:
    """Format M1 bars with aggregated big trade detail for token efficiency."""
    lines = ["M1 bar sequence (oldest -> newest):"]
    for i, b in enumerate(bars):
        t_et = b.timestamp.astimezone(ET)
        big_info = ""
        if b.big_trades:
            buy_trades = [t for t in b.big_trades if t.side == 'A']
            sell_trades = [t for t in b.big_trades if t.side == 'B']
            
            zones = []
            if buy_trades:
                min_p = min(t.price for t in buy_trades)
                max_p = max(t.price for t in buy_trades)
                vol = sum(t.size for t in buy_trades)
                zones.append(f"{vol} BUY (Zone {min_p:.2f}-{max_p:.2f})" if min_p != max_p else f"{vol} BUY @ {min_p:.2f}")
            if sell_trades:
                min_p = min(t.price for t in sell_trades)
                max_p = max(t.price for t in sell_trades)
                vol = sum(t.size for t in sell_trades)
                zones.append(f"{vol} SELL (Zone {min_p:.2f}-{max_p:.2f})" if min_p != max_p else f"{vol} SELL @ {min_p:.2f}")
                
            big_info = f" | BIG_TRADES=[{', '.join(zones)}]"
            
        is_last = (i == len(bars) - 1)
        delta_str = f" delta={b.delta:+d}" if (is_last or not hide_historical_delta) else ""
        
        lines.append(
            f"  {t_et.strftime('%H:%M:%S')} O={b.open:.2f} H={b.high:.2f} "
            f"L={b.low:.2f} C={b.close:.2f} V={b.volume}"
            f"{delta_str}{big_info}"
        )
        if is_last:
            lines.append(f"\n---> CURRENT CANDIDATE BAR DELTA: {b.delta:+d} <---")
            
    return "\n".join(lines)

def build_fabio_question(candidate: CandidateBar, session_context: list = None, m1_bars: list[Bar] = None, market_narrative: str = "", bars_since_last: list[Bar] = None) -> str:
    templates = _load_templates()
    bar = candidate.bar
    ctx = candidate.session_ctx
    t_et = bar.timestamp.astimezone(ET)
    bar_et_time = t_et
    ib_end_time = bar_et_time.replace(hour=10, minute=30, second=0, microsecond=0)
    
    if bar_et_time >= ib_end_time:
        ib_pos = 'above IVB' if bar.close > ctx.ib_high else \
                 'below IVB' if bar.close < ctx.ib_low  else 'inside IVB'
    else:
        if ctx.vp:
            ib_pos = 'above Overnight VA' if bar.close > ctx.vp.va_high else \
                     'below Overnight VA' if bar.close < ctx.vp.va_low else 'inside Overnight VA'
        else:
            ib_pos = 'Price Discovery (First Hour)'
    suggested = 'long' if candidate.wall_side == 'ask' else 'short'
    # FIX: When price is OUTSIDE the IB, suggested_direction must follow the IB breakout trend,
    # NOT the wall_side of the single bar (which can point in any direction).
    # Exception: 'reversal' setups are deliberately counter-trend — keep wall_side for those.
    if candidate.setup_category != 'reversal':
        if 'above' in ib_pos:
            suggested = 'long'   # above IB → uptrend → long continuation bias
        elif 'below' in ib_pos:
            suggested = 'short'  # below IB → downtrend → short continuation bias
        # inside IB: wall_side is the correct hint (no IB directional bias)
    m5_sequence = _format_m5_sequence(candidate.recent_bars) if candidate.recent_bars else ""
    m1_sequence = _format_m1_sequence(m1_bars) if m1_bars else ""
    
    # Select appropriate template: imbalance_hunting gets a trend-continuation framing
    if candidate.setup_category == 'imbalance_hunting' and 'fabio_imbalance_question_template' in templates:
        tpl = templates['fabio_imbalance_question_template']
    else:
        tpl = templates['fabio_nlm_question_template']
    question = tpl.format(
        date            = bar.timestamp.strftime('%Y-%m-%d'),
        bar_time_et     = t_et.strftime('%H:%M'),
        close           = bar.close,
        ib_high         = ctx.ib_high,
        ib_low          = ctx.ib_low,
        ib_range        = ctx.ib_range,
        poc             = ctx.vp.poc if ctx.vp else 'N/A',
        va_high         = ctx.vp.va_high if ctx.vp else 'N/A',
        va_low          = ctx.vp.va_low if ctx.vp else 'N/A',
        lvn_levels      = str(ctx.vp.lvn_levels if ctx.vp else []),
        lookback        = 3,
        wall_trade_count= candidate.wall_trade_count,
        wall_total_size = sum(t.size for t in bar.big_trades),
        wall_level      = candidate.wall_level,
        wall_side       = candidate.wall_side,
        wall_max_size   = candidate.wall_max_size,
        bar_volume      = bar.volume,
        bar_delta       = bar.delta,
        ib_position     = ib_pos,
        day_type        = ctx.day_type,
        suggested_direction = suggested,
    )
    # Add previous day VP context for reference levels
    if ctx.prev_day_vp:
        pvp = ctx.prev_day_vp
        question += (
            f"\n\nPrevious day VP: POC={pvp.poc:.2f} VAH={pvp.va_high:.2f} "
            f"VAL={pvp.va_low:.2f} HVN={pvp.hvn_levels} LVN={pvp.lvn_levels}"
        )
        
    # Multi-Day Structural Context
    if len(ctx.historical_days) >= 2:
        t1 = ctx.historical_days[0]
        t2 = ctx.historical_days[1]
        
        question += "\n\n## MULTI-DAY STRUCTURAL CONTEXT\n"
        question += f"T-2 (Day Before Yesterday): POC={t2.vp.poc:.2f}, Close={t2.close_price:.2f}\n"
        question += f"T-1 (Yesterday): POC={t1.vp.poc:.2f}, Close={t1.close_price:.2f}\n"
        question += f"T-0 (Today Live): POC={ctx.vp.poc:.2f} (developing)\n"
        
        if t1.vp.poc < t2.vp.poc and t1.close_price < t2.vp.poc:
            status = "[STRONG DOWNTREND MULTI-DAY] T-1 printed a lower POC and closed below T-2 POC. Sellers have Value Acceptance. Favour SHORT setups."
        elif t1.vp.poc > t2.vp.poc and t1.close_price > t2.vp.poc:
            status = "[STRONG UPTREND MULTI-DAY] T-1 printed a higher POC and closed above T-2 POC. Buyers have Value Acceptance. Favour LONG setups."
        else:
            status = "[MIXED / BALANCE MULTI-DAY] T-1 did not structurally break T-2 (e.g., lower POC but closed higher, or inside day). Market is in equilibrium or squeezing."
            
        question += f"Structural Status: {status}\n"
    
    if m1_sequence:
        # Calculate institutional stats for the M1 window
        all_bigs = [t for b in m1_bars for t in b.big_trades]
        buy_bigs = sum(t.size for t in all_bigs if t.side == 'A')
        sell_bigs = sum(t.size for t in all_bigs if t.side == 'B')
        
        question += f"\n\n## Institutional M1 Footprint (Real-time Flow)\n"
        question += f"Total big trades in window: {len(all_bigs)} ({buy_bigs} buy / {sell_bigs} sell contracts)\n"
        question += m1_sequence

    if m5_sequence:
        question += f"\n\n{m5_sequence}"
    if session_context:
        question += "\n\n## Session Context (your prior analyses today)\n"
        question += "\n".join(session_context)
        
    if market_narrative:
        question += f"\n\n## Current Market Narrative (Your continuous story of the day)\n{market_narrative}\n"
        
    if bars_since_last:
        question += f"\n\n## What happened since your last evaluation:\n"
        question += _format_m5_sequence(bars_since_last)
        
    # Inject Human Feedback (all setups, since Fabio determines the setup)
    from src.memory.feedback_injector import get_relevant_feedback
    from src.memory.quantitative_memory import build_fingerprint, get_fingerprint_stats
    
    candidate.context_fingerprint = build_fingerprint(candidate)
    stats_alert = get_fingerprint_stats(candidate)
    if stats_alert:
        question += stats_alert
        
    feedback = get_relevant_feedback(None)
    if feedback:
        question += feedback
        
    return question

def build_andrea_question(candidate: CandidateBar,
                           fabio_signal: FabioSignal,
                           m1_bars: list[Bar] = None) -> str:
    templates = _load_templates()
    bar = candidate.bar
    ctx = candidate.session_ctx
    t_et = bar.timestamp.astimezone(ET)
    m5_sequence = _format_m5_sequence(candidate.recent_bars) if candidate.recent_bars else ""
    m1_sequence = _format_m1_sequence(m1_bars, hide_historical_delta=True) if m1_bars else ""
    
    # Select appropriate template for Andrea
    if fabio_signal.setup_type == 'imbalance_hunting' and 'andrea_imbalance_question_template' in templates:
        tpl = templates['andrea_imbalance_question_template']
    else:
        tpl = templates['andrea_nlm_question_template']
        
    question = tpl.format(
        date            = bar.timestamp.strftime('%Y-%m-%d'),
        bar_time_et     = t_et.strftime('%H:%M'),
        close           = bar.close,
        open            = bar.open,
        high            = bar.high,
        low             = bar.low,
        ib_high         = ctx.ib_high,
        ib_low          = ctx.ib_low,
        fabio_setup     = fabio_signal.setup_type,
        fabio_direction = fabio_signal.direction,
        fabio_confidence= fabio_signal.confidence,
        wall_level      = candidate.wall_level,
        wall_side       = candidate.wall_side,
        wall_trade_count= candidate.wall_trade_count,
    )
    if ctx.prev_day_vp:
        pvp = ctx.prev_day_vp
        question += (
            f"\n\nPrevious day VP: POC={pvp.poc:.2f} VAH={pvp.va_high:.2f} "
            f"VAL={pvp.va_low:.2f}"
        )
    
    if m1_sequence:
        # Calculate institutional stats for the M1 window
        all_bigs = [t for b in m1_bars for t in b.big_trades]
        buy_bigs = sum(t.size for t in all_bigs if t.side == 'A')
        sell_bigs = sum(t.size for t in all_bigs if t.side == 'B')
        
        question += f"\n\n## Institutional Activity (M1 Footprint)\n"
        question += f"Total big trades: {len(all_bigs)} ({buy_bigs} buy / {sell_bigs} sell contracts)\n"
        question += m1_sequence

    if m5_sequence:
        question += f"\n\n{m5_sequence}"
        
    # Inject Human Feedback specific to Fabio's setup choice
    from src.memory.feedback_injector import get_relevant_feedback
    from src.memory.quantitative_memory import build_fingerprint, get_fingerprint_stats
    
    candidate.context_fingerprint = build_fingerprint(candidate)
    stats_alert = get_fingerprint_stats(candidate)
    if stats_alert:
        question += stats_alert
        
    feedback = get_relevant_feedback(fabio_signal.setup_type)
    if feedback:
        question += feedback
        
    return question
