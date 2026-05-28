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

def is_fabio_active(bar: Bar) -> bool:
    t = _to_et(bar)
    # Fabio's Core Window: 09:35 ET to 12:30 ET for new entries
    start_time = t.replace(hour=9, minute=35, second=0, microsecond=0)
    end_time   = t.replace(hour=12, minute=30, second=0, microsecond=0)
    return start_time <= t <= end_time

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

def build_session_context(date_str: str, bars: list, vp, prev_day_vp=None) -> SessionContext:
    ib_high, ib_low = compute_ib(bars)
    initial_day_type = classify_day_type(bars)
    ctx = SessionContext(
        date=date_str,
        ib_high=ib_high,
        ib_low=ib_low,
        ib_range=round(ib_high - ib_low, 2),
        ib_complete=ib_high > 0,
        vp=vp,
        prev_day_vp=prev_day_vp,
        day_type=initial_day_type,
        # initialize history list
        day_type_history=[initial_day_type],
    )
    return ctx
