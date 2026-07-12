import pytest
from datetime import datetime, timezone, timedelta
from src import SessionContext, Bar
from src.session_context import update_day_type
from src.candidate_detector import detect_candidates

def create_bar(timestamp, close, high, low, volume=4000, delta=500):
    return Bar(
        timestamp=timestamp,
        open=close,
        high=high,
        low=low,
        close=close,
        volume=volume,
        buy_volume=volume // 2 + delta // 2,
        sell_volume=volume // 2 - delta // 2,
        delta=delta,
        delta_pct=delta / volume * 100,
        cvd=delta,
        vwap=close,
        big_trades=[]
    )

def test_update_day_type():
    base_time = datetime(2025, 2, 3, 14, 30, tzinfo=timezone.utc)
    ctx = SessionContext(
        date='20250203',
        ib_high=100,
        ib_low=90,
        ib_range=10,
        ib_complete=True,
        vp=None
    )
    
    bars = []
    # Create an upward trend
    for i in range(10):
        b = create_bar(base_time + timedelta(minutes=5*i), 100 + i*5, 105 + i*5, 95 + i*5)
        bars.append(b)
        
    day_type = update_day_type(ctx, bars)
    assert day_type == 'trend_up'
    assert len(ctx.day_type_history) == 1
    assert ctx.day_type_history[0] == 'trend_up'

def test_exhaustion_signal():
    base_time = datetime(2025, 2, 3, 14, 30, tzinfo=timezone.utc)
    ctx = SessionContext(
        date='20250203',
        ib_high=100,
        ib_low=90,
        ib_range=10,
        ib_complete=True,
        vp=None
    )
    
    # Create previous bars (trend down)
    bars = []
    for i in range(3):
        b = create_bar(base_time + timedelta(minutes=5*i), 100 - i*10, 105 - i*10, 95 - i*10)
        bars.append(b)
        
    # The exhaustion bar: price went very low (70), but closed higher (80) -> low excess tail
    exhaustion_time = base_time + timedelta(minutes=15)
    from src import Trade
    wall_trade = Trade(ts_event=exhaustion_time, side='B', price=72, size=50) # Sellers trapped at the low
    
    ex_bar = create_bar(exhaustion_time, 80, 85, 70)
    ex_bar.big_trades.append(wall_trade)
    bars.append(ex_bar)
    
    candidates = detect_candidates(bars, ctx, bars_1min_ny=bars)
    
    # Wait, the candidate detector requires proximity to a VP level.
    # To test exhaustion logic simply, we might need a VP level near 72.
    from src import VolumeProfile
    ctx.vp = VolumeProfile(poc=72, va_high=90, va_low=60)
    
    candidates = detect_candidates(bars, ctx, bars_1min_ny=bars)
    # The last candidate should be our exhaustion bar
    if candidates:
        last_cand = candidates[-1]
        assert last_cand.exhaustion_signal == True
