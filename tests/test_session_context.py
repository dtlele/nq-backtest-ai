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

def test_filter_ny_window_keeps_09_25_to_16_00():
    bars = [
        _bar_et(9, 20, 20000.0),   # before → excluded
        _bar_et(9, 25, 20000.0),   # start  → included
        _bar_et(11, 29, 20000.0),  # inside → included
        _bar_et(15, 59, 20000.0),  # end    → included (strict < 16:00)
        _bar_et(16, 0,  20000.0),  # after  → excluded
    ]
    result = filter_ny_window(bars)
    assert len(result) == 3

def test_compute_ib_uses_first_30min():
    bars = [
        _bar_et(9, 30, 20000.0),
        _bar_et(9, 35, 20050.0),
        _bar_et(9, 40, 19980.0),
        _bar_et(9, 44, 20020.0),
        _bar_et(9, 55, 20100.0),   # inside 30-min IB
        _bar_et(9, 59, 19970.0),   # last bar inside IB
        _bar_et(10, 0, 20200.0),   # outside IB (>= 10:00)
    ]
    ib_high, ib_low = compute_ib(bars)
    assert ib_high == pytest.approx(20101.0)  # bar high = price+1
    assert ib_low  == pytest.approx(19969.0)  # bar low = price-1

def test_is_fabio_active_after_09_35():
    bar_before = _bar_et(9, 34, 20000.0)
    bar_after  = _bar_et(9, 35, 20000.0)
    assert is_fabio_active(bar_before) is False
    assert is_fabio_active(bar_after)  is True

def test_classify_day_type_trend_up():
    bars = [_bar_et(9, 30 + i, 20000.0 + i * 10, 5000) for i in range(10)]
    assert classify_day_type(bars) == 'trend_up'
