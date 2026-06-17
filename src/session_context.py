import pytz
from datetime import datetime, timezone, timedelta
from typing import List
from src import (
    Bar, SessionContext, VolumeProfile,
    NY_WINDOW_START_H, NY_WINDOW_START_M,
    NY_WINDOW_END_H, NY_WINDOW_END_M,
    FABIO_ACTIVE_H, FABIO_ACTIVE_M, IB_DURATION_MIN,
)

ET = pytz.timezone('America/New_York')

def _to_et(bar: Bar) -> datetime:
    return bar.timestamp.astimezone(ET)

def filter_ny_window(bars: list) -> list:
    """Keep bars strictly within [09:25, 11:30) ET."""
    result = []
    for b in bars:
        t = _to_et(b)
        start = t.replace(hour=NY_WINDOW_START_H, minute=NY_WINDOW_START_M,
                          second=0, microsecond=0)
        end   = t.replace(hour=NY_WINDOW_END_H,   minute=NY_WINDOW_END_M,
                          second=0, microsecond=0)
        if start <= t < end:
            result.append(b)
    return result

def filter_rth_session(bars: list) -> list:
    """Keep bars strictly within the RTH session [09:30, 16:00) ET."""
    result = []
    for b in bars:
        t = _to_et(b)
        start = t.replace(hour=9, minute=30, second=0, microsecond=0)
        end   = t.replace(hour=16, minute=0, second=0, microsecond=0)
        if start <= t < end:
            result.append(b)
    return result

def filter_full_ny_session(bars: list) -> list:
    """Keep bars for the full NY session [09:00, 16:15) ET for visualization."""
    result = []
    for b in bars:
        t = _to_et(b)
        start = t.replace(hour=9, minute=0, second=0, microsecond=0)
        end   = t.replace(hour=16, minute=15, second=0, microsecond=0)
        if start <= t < end:
            result.append(b)
    return result

def filter_overnight_window(bars: list) -> list:
    """Keep bars before NY open (09:30 ET)."""
    result = []
    for b in bars:
        t = _to_et(b)
        ny_open = t.replace(hour=9, minute=30, second=0, microsecond=0)
        if t < ny_open:
            result.append(b)
    return result

def compute_ib(bars: list) -> tuple:
    """Return (ib_high, ib_low) from first IB_DURATION_MIN of NY open."""
    ib_bars = []
    for b in bars:
        t = _to_et(b)
        ny_open = t.replace(hour=9, minute=30, second=0, microsecond=0)
        ib_end  = ny_open + timedelta(minutes=IB_DURATION_MIN)
        if ny_open <= t < ib_end:
            ib_bars.append(b)
    if not ib_bars:
        return (0.0, 0.0)
    return (max(b.high for b in ib_bars), min(b.low for b in ib_bars))

def is_fabio_active(bar: Bar, ctx: SessionContext = None) -> bool:
    t = _to_et(bar)
    # Fabio's Core Window: 09:31 ET to 11:00 ET (Catching the open)
    start_time = t.replace(hour=9, minute=31, second=0, microsecond=0)
    end_time   = t.replace(hour=11, minute=0, second=0, microsecond=0)
    
    if ctx:
        if ctx.day_type in ['trend_up', 'trend_down']:
            # For expansive imbalance days, stop early at 10:30 ET
            end_time = t.replace(hour=10, minute=30, second=0, microsecond=0)
        elif ctx.day_type in ['balance', 'transition_state']:
            # For choppy/manipulation days, extend to 12:00 ET
            end_time = t.replace(hour=12, minute=0, second=0, microsecond=0)
        
    return start_time <= t < end_time

def classify_day_type(bars: list) -> str:
    if len(bars) < 3:
        return 'unknown'
    closes = [b.close for b in bars]
    slope  = closes[-1] - closes[0]
    spread = max(closes) - min(closes)
    if spread == 0:
        return 'balance'
    ratio = abs(slope) / spread
    if ratio > 0.6 and slope > 0:
        return 'trend_up'
    if ratio > 0.6 and slope < 0:
        return 'trend_down'
    if 0.4 <= ratio <= 0.6:
        return 'transition_state'
    return 'balance'

def update_day_type(ctx: SessionContext, bars: list) -> str:
    """Recompute day type based on bars processed so far and store history.
    Keeps a limited history of the last 200 updates to avoid unbounded growth.
    """
    new_type = classify_day_type(bars)
    ctx.day_type = new_type
    if not hasattr(ctx, 'day_type_history') or ctx.day_type_history is None:
        ctx.day_type_history = []  # type: List[str]
    ctx.day_type_history.append(new_type)
    # keep only the last 200 entries
    MAX_HISTORY = 200
    if len(ctx.day_type_history) > MAX_HISTORY:
        ctx.day_type_history = ctx.day_type_history[-MAX_HISTORY:]
    return new_type

def build_session_context(date_str: str, bars: list, vp, prev_day_vp=None, historical_days=None) -> SessionContext:
    ib_high, ib_low = compute_ib(bars)
    initial_day_type = classify_day_type(bars)
    
    # IB is complete if the latest bar's time is >= NY open + IB_DURATION_MIN
    is_complete = False
    if bars:
        latest_t = _to_et(bars[-1])
        ny_open = latest_t.replace(hour=9, minute=30, second=0, microsecond=0)
        ib_end = ny_open + timedelta(minutes=IB_DURATION_MIN)
        if latest_t >= ib_end:
            is_complete = True

    ctx = SessionContext(
        date=date_str,
        ib_high=ib_high,
        ib_low=ib_low,
        ib_range=round(ib_high - ib_low, 2) if ib_high > 0 else 0.0,
        ib_complete=is_complete,
        vp=vp,
        prev_day_vp=prev_day_vp,
        historical_days=historical_days or [],
        day_type=initial_day_type,
        # initialize history list
        day_type_history=[initial_day_type],
        session_memory=[],
    )
    # Internal trackers for session memory filters
    ctx._last_level_test = {}
    ctx._last_wall_logged = {}
    ctx._logged_ib_comp = False
    return ctx

def get_session_memory_up_to(ctx: SessionContext, timestamp: datetime) -> List[str]:
    """Return all session memory event strings up to the given UTC timestamp."""
    if not ctx.session_memory:
        return []
    return [item['text'] for item in ctx.session_memory if item['timestamp'] <= timestamp]

def update_session_memory(ctx: SessionContext, current_bar: Bar, bars_processed: list) -> None:
    """Evaluate current bar for key session events (interactions, big trades, day type)
    and append formatted entries (with timestamps) to ctx.session_memory.
    """
    t_et = _to_et(current_bar)
    time_str = t_et.strftime("%H:%M")
    
    # 1. Day Type transition
    if len(ctx.day_type_history) >= 2:
        prev_day_type = ctx.day_type_history[-2]
        if ctx.day_type != prev_day_type:
            ctx.session_memory.append({
                'timestamp': current_bar.timestamp,
                'text': f"[{time_str} ET] Market structure transitioned from {prev_day_type.upper()} to {ctx.day_type.upper()}."
            })

    # 2. IB Range Completion (at 10:00 ET)
    if t_et.hour == 10 and t_et.minute == 0 and not getattr(ctx, '_logged_ib_comp', False):
        ctx.session_memory.append({
            'timestamp': current_bar.timestamp,
            'text': f"[{time_str} ET] Initial Balance (IB) range completed. High={ctx.ib_high:.2f}, Low={ctx.ib_low:.2f}, Range={ctx.ib_range:.2f} points."
        })
        ctx._logged_ib_comp = True

    # 3. Big Trade Walls (total volume >= 300 or single >= 150)
    if current_bar.big_trades:
        total_size = sum(t.size for t in current_bar.big_trades)
        max_size = max(t.size for t in current_bar.big_trades)
        if total_size >= 300 or max_size >= 150:
            prices = [t.price for t in current_bar.big_trades]
            min_p = min(prices)
            max_p = max(prices)
            buy_v = sum(t.size for t in current_bar.big_trades if t.side == 'A')
            sell_v = sum(t.size for t in current_bar.big_trades if t.side == 'B')
            side = "Buy" if buy_v > sell_v else "Sell"
            
            # Group by 5 points range to prevent spamming
            rounded_price = round(min_p / 5.0) * 5
            last_logged_time = ctx._last_wall_logged.get(rounded_price)
            if last_logged_time is None or (current_bar.timestamp - last_logged_time).total_seconds() > 300:
                ctx._last_wall_logged[rounded_price] = current_bar.timestamp
                ctx.session_memory.append({
                    'timestamp': current_bar.timestamp,
                    'text': f"[{time_str} ET] Institutional order wall of {total_size} contracts ({side}) detected at {min_p:.2f}-{max_p:.2f}."
                })

    # 4. Level Interactions (Yesterday VAH/VAL/POC, Today IBH/IBL, Today VAH/VAL/POC)
    levels = []
    if ctx.prev_day_vp:
        levels.append(("Yesterday VAH", ctx.prev_day_vp.va_high))
        levels.append(("Yesterday VAL", ctx.prev_day_vp.va_low))
        levels.append(("Yesterday POC", ctx.prev_day_vp.poc))
    if ctx.ib_high > 0:
        levels.append(("IB High", ctx.ib_high))
        levels.append(("IB Low", ctx.ib_low))
    if ctx.vp:
        levels.append(("Overnight VAH", ctx.vp.va_high))
        levels.append(("Overnight VAL", ctx.vp.va_low))
        levels.append(("Overnight POC", ctx.vp.poc))

    for name, val in levels:
        if val is None or val <= 0:
            continue
        
        # Check if current bar touches the level
        if current_bar.low <= val <= current_bar.high:
            last_tested = ctx._last_level_test.get(name)
            
            # Limit interaction logs to once every 10 minutes per level
            if last_tested is None or (current_bar.timestamp - last_tested).total_seconds() > 600:
                ctx._last_level_test[name] = current_bar.timestamp
                
                # Determine outcome: Close relative to level, delta, wicks
                bar_range = current_bar.high - current_bar.low
                top_w = ((current_bar.high - max(current_bar.open, current_bar.close)) / bar_range * 100) if bar_range > 0 else 0
                bot_w = ((min(current_bar.open, current_bar.close) - current_bar.low) / bar_range * 100) if bar_range > 0 else 0
                
                # Check for rejection vs acceptance
                is_above = current_bar.close > val
                close_dist = abs(current_bar.close - val)
                
                outcome = "Touched"
                if "Low" in name or "VAL" in name:
                    if is_above and bot_w >= 35:
                        outcome = "Rejected (Strong buying wicks)"
                    elif not is_above and close_dist > 5:
                        outcome = "Accepted (Closed below)"
                elif "High" in name or "VAH" in name:
                    if not is_above and top_w >= 35:
                        outcome = "Rejected (Strong selling wicks)"
                    elif is_above and close_dist > 5:
                        outcome = "Accepted (Closed above)"
                
                ctx.session_memory.append({
                    'timestamp': current_bar.timestamp,
                    'text': f"[{time_str} ET] Tested {name} ({val:.2f}). Result: {outcome}. Close={current_bar.close:.2f}, Delta={current_bar.delta:+d}."
                })
