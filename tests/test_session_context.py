import pytest
from datetime import datetime, timezone, timedelta
import pytz
from src import Bar, IB_DURATION_MIN
from src.session_context import (
    filter_ny_window, compute_ib, classify_day_type,
    build_session_context, is_fabio_active
)

ET = pytz.timezone('America/New_York')

def _bar_et(h: int, m: int, price: float, vol: int = 5000) -> Bar:
    dt_et = ET.localize(datetime(2025, 4, 30, h, m, 0))
    dt_utc = dt_et.astimezone(timezone.utc)
    return Bar(dt_utc, price, price+1, price-1, price,
               vol, vol//2, vol//2, 0, 0.0, 0, price)

def test_filter_ny_window_keeps_09_25_to_12_30():
    bars = [
        _bar_et(9, 20, 20000.0),   # before → excluded
        _bar_et(9, 25, 20000.0),   # start  → included
        _bar_et(11, 29, 20000.0),  # inside → included
        _bar_et(12, 29, 20000.0),  # end    → included (strict < 12:30)
        _bar_et(12, 30, 20000.0),  # after  → excluded
    ]
    result = filter_ny_window(bars)
    assert len(result) == 3

def test_compute_ib_uses_first_60min():
    bars = [
        _bar_et(9, 30, 20000.0),
        _bar_et(9, 35, 20050.0),
        _bar_et(9, 40, 19980.0),
        _bar_et(9, 44, 20020.0),
        _bar_et(9, 55, 20100.0),   # inside 60-min IB
        _bar_et(9, 59, 19970.0),   # inside 60-min IB
        _bar_et(10, 0, 20200.0),   # inside 60-min IB
    ]
    ib_high, ib_low = compute_ib(bars)
    assert ib_high == pytest.approx(20201.0)  # bar high = price+1
    assert ib_low  == pytest.approx(19969.0)  # bar low = price-1

def test_is_fabio_active_after_09_31():
    bar_before = _bar_et(9, 30, 20000.0)
    bar_after  = _bar_et(9, 31, 20000.0)
    assert is_fabio_active(bar_before) is False
    assert is_fabio_active(bar_after)  is True

def test_classify_day_type_trend_up():
    bars = [_bar_et(9, 30 + i, 20000.0 + i * 10, 5000) for i in range(10)]
    assert classify_day_type(bars) == 'trend_up'

def test_session_memory_lookahead_bias_free():
    from src.session_context import update_session_memory, get_session_memory_up_to
    from src import VolumeProfile
    vp = VolumeProfile(20000.0, 20050.0, 19950.0)
    ctx = build_session_context("2025-04-30", [], vp)
    
    bar1 = _bar_et(9, 35, 20000.0)
    bar2 = _bar_et(10, 0, 20100.0)
    
    # Update on bar1
    update_session_memory(ctx, bar1, [bar1])
    
    # Update on bar2 (IB completion occurs at 10:00 ET)
    # Let's manually trigger day type history transitions or other triggers
    ctx.ib_high = 20200.0
    ctx.ib_low = 19900.0
    ctx.ib_range = 300.0
    update_session_memory(ctx, bar2, [bar1, bar2])
    
    # Verify at bar1 time, no IB completion message is visible
    mem_bar1 = get_session_memory_up_to(ctx, bar1.timestamp)
    assert not any("IB" in m for m in mem_bar1)
    
    # Verify at bar2 time, IB completion is visible
    mem_bar2 = get_session_memory_up_to(ctx, bar2.timestamp)
    assert any("IB" in m for m in mem_bar2)
