import pandas as pd
from datetime import datetime, timedelta
from src import Bar, Trade
from src.volume_profile import build_profile_from_trades

def detect_balance_area(bars: list[Bar], window_size: int = 8, max_range_points: float = 15.0) -> tuple[bool, float, float]:
    """
    Check if the last window_size bars form a Balance Area (sideways consolidation).
    Returns (is_in_balance, balance_bottom, balance_top)
    """
    if len(bars) < window_size:
        return False, 0.0, 0.0
        
    recent_bars = bars[-window_size:]
    highs = [b.high for b in recent_bars]
    lows = [b.low for b in recent_bars]
    
    overall_high = max(highs)
    overall_low = min(lows)
    current_range = overall_high - overall_low
    
    is_balanced = current_range <= max_range_points
    return is_balanced, overall_low, overall_high

def check_balance_breakout(bar: Bar, balance_bottom: float, balance_top: float, delta_threshold: int = 26, break_buffer: float = 2.5) -> str:
    """
    Verify if the current bar broke out of the balance area with strong delta.
    Returns: 'up', 'down', or 'none'
    """
    # Breakout up: Close is well above top, and delta is strongly positive
    if bar.close > (balance_top + break_buffer) and bar.delta >= delta_threshold:
        return 'up'
    # Breakout down: Close is well below bottom, and delta is strongly negative
    elif bar.close < (balance_bottom - break_buffer) and bar.delta <= -delta_threshold:
        return 'down'
        
    return 'none'

def get_composite_lvn_zones(bars: list[Bar], current_ts: datetime, lookback_minutes: int = 60) -> list[float]:
    """
    Build a Composite Volume Profile of the last lookback_minutes using Bar footprints
    and extract the Low Volume Nodes (LVNs).
    """
    if not bars:
        return []
        
    start_time = current_ts - timedelta(minutes=lookback_minutes)
    
    # Filter bars in the lookback window
    window_bars = [b for b in bars if start_time <= b.timestamp <= current_ts]
    
    if not window_bars:
        return []
        
    from src.volume_profile import build_profile_from_bars
    vp = build_profile_from_bars(window_bars)
    if not vp:
        return []
        
    # Return the strongest LVN levels
    return vp.lvn_levels

