from src import Bar
from src.footprint_engine import detect_absorption_long, detect_absorption_short

def is_near_level(price: float, levels: list[float], proximity_pts: float = 2.5) -> bool:
    """Check if price is within proximity_pts points of any level in the list."""
    if not levels:
        return False
    return any(abs(price - lvl) <= proximity_pts for lvl in levels)

def detect_bullish_setup(
    c1: Bar, 
    c2: Bar, 
    lvn_zones: list[float], 
    session_val: float = None,
    delta_threshold: int = -26, 
    range_points: float = 10.0,
    proximity_pts: float = 3.5
) -> tuple[bool, str]:
    """
    Scan for the Bullish (Long) FST Setup:
    1. C1 shows bullish absorption (trapped sellers in the bottom wick).
    2. C1 low is near a key structural level (LVN zone or Session Value Area Low).
    3. C2 (Ignition Bar) closes near the high, has positive delta, and confirms the push.
    """
    # 1. Proximity check on C1 low
    valid_context = False
    context_reason = ""
    
    if lvn_zones and is_near_level(c1.low, lvn_zones, proximity_pts=proximity_pts):
        valid_context = True
        context_reason = "LVN Zone"
    elif session_val is not None and abs(c1.low - session_val) <= proximity_pts:
        valid_context = True
        context_reason = "Session VAL"
        
    if not valid_context:
        return False, "No Context Level"
        
    # 2. Bullish Absorption check on C1
    is_absorbed, trap_price, trap_delta = detect_absorption_long(c1, delta_threshold=delta_threshold)
    if not is_absorbed:
        return False, "No Absorption"
        
    # 3. Ignition Check on C2
    c2_range = c2.high - c2.low
    if c2_range <= 0:
        return False, "C2 Zero Range"
        
    # C2 must close in the upper 25% of its range
    is_c2_full = c2.close >= (c2.high - (range_points * 0.25))
    if not is_c2_full:
        return False, "C2 Not Full"
        
    # C2 must have positive total delta
    if c2.delta <= 0:
        return False, "C2 Negative Delta"
        
    return True, f"Bullish setup near {context_reason} (C1 Wick Delta: {trap_delta}, C2 Delta: {c2.delta})"

def detect_bearish_setup(
    c1: Bar, 
    c2: Bar, 
    hvn_zones: list[float], 
    session_vah: float = None,
    delta_threshold: int = 26, 
    range_points: float = 10.0,
    proximity_pts: float = 3.5
) -> tuple[bool, str]:
    """
    Scan for the Bearish (Short) FST Setup:
    1. C1 shows bearish absorption (trapped buyers in the top wick).
    2. C1 high is near a key structural level (HVN zone or Session Value Area High).
    3. C2 (Ignition Bar) closes near the low, has negative delta, and confirms the push.
    """
    # 1. Proximity check on C1 high
    valid_context = False
    context_reason = ""
    
    if hvn_zones and is_near_level(c1.high, hvn_zones, proximity_pts=proximity_pts):
        valid_context = True
        context_reason = "HVN Zone"
    elif session_vah is not None and abs(c1.high - session_vah) <= proximity_pts:
        valid_context = True
        context_reason = "Session VAH"
        
    if not valid_context:
        return False, "No Context Level"
        
    # 2. Bearish Absorption check on C1
    is_absorbed, trap_price, trap_delta = detect_absorption_short(c1, delta_threshold=delta_threshold)
    if not is_absorbed:
        return False, "No Absorption"
        
    # 3. Ignition Check on C2
    c2_range = c2.high - c2.low
    if c2_range <= 0:
        return False, "C2 Zero Range"
        
    # C2 must close in the lower 25% of its range
    is_c2_full = c2.close <= (c2.low + (range_points * 0.25))
    if not is_c2_full:
        return False, "C2 Not Full"
        
    # C2 must have negative total delta
    if c2.delta >= 0:
        return False, "C2 Positive Delta"
        
    return True, f"Bearish setup near {context_reason} (C1 Wick Delta: +{trap_delta}, C2 Delta: {c2.delta})"
