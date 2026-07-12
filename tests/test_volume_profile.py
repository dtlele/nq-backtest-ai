import pytest
from datetime import datetime, timezone
from src import Bar, VA_PERCENTAGE
from src.volume_profile import compute_volume_profile

def _bar(price: float, vol: int) -> Bar:
    return Bar(datetime(2025,4,30,14,0,tzinfo=timezone.utc),
               price, price+0.25, price-0.25, price,
               vol, vol//2, vol//2, 0, 0.0, 0, price)

def test_poc_highest_volume():
    bars = [_bar(100.00, 100), _bar(100.25, 200), _bar(100.50, 50)]
    vp = compute_volume_profile(bars)
    assert vp.poc == pytest.approx(100.25)

def test_va_contains_70pct():
    bars = [_bar(99.75, 10), _bar(100.00, 700), _bar(100.25, 10), _bar(100.50, 10)]
    vp = compute_volume_profile(bars)
    assert vp.va_low <= 100.00 <= vp.va_high

def test_empty_returns_none():
    assert compute_volume_profile([]) is None

def test_hvn_lvn_returned():
    bars = [_bar(99.75,10), _bar(100.00,500), _bar(100.25,10), _bar(100.50,400)]
    vp = compute_volume_profile(bars)
    assert len(vp.hvn_levels) >= 1
    assert len(vp.lvn_levels) >= 1
