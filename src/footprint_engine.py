from src import Bar

def get_bar_poc(bar: Bar) -> tuple[float, int]:
    """
    Find the Point of Control (POC) price level and its volume for a given Bar.
    POC is the price level with the highest total volume (bid + ask).
    """
    if not bar.footprint:
        return bar.close, 0
    
    max_vol = -1
    poc_price = bar.close
    for price, vols in bar.footprint.items():
        vol = vols['bid'] + vols['ask']
        if vol > max_vol:
            max_vol = vol
            poc_price = price
            
    return poc_price, max_vol

def get_wick_nodes(bar: Bar, wick_ratio: float = 0.25) -> tuple[list[float], list[float]]:
    """
    Get lists of price levels that fall within the top and bottom wicks.
    wick_ratio: percentage of the bar's range from high/low considered to be the wick (default 25%)
    """
    h = bar.high
    l = bar.low
    r = h - l
    if r <= 0:
        return [], []
        
    bottom_threshold = l + (r * wick_ratio)
    top_threshold = h - (r * wick_ratio)
    
    bottom_nodes = []
    top_nodes = []
    for price in bar.footprint.keys():
        if price <= bottom_threshold:
            bottom_nodes.append(price)
        elif price >= top_threshold:
            top_nodes.append(price)
            
    return bottom_nodes, top_nodes

def detect_absorption_long(bar: Bar, delta_threshold: int = -26, wick_ratio: float = 0.25) -> tuple[bool, float, int]:
    """
    Detect bullish absorption (trapped sellers at the bottom wick).
    Returns (is_absorbed, trap_price, trap_delta)
    """
    h = bar.high
    l = bar.low
    r = h - l
    if r <= 0:
        return False, 0.0, 0
        
    # Condition 1: Candle must not close at the lows (close in upper 50%)
    if bar.close < l + (r * 0.50):
        return False, 0.0, 0
        
    bottom_nodes, _ = get_wick_nodes(bar, wick_ratio)
    
    max_trap_delta = 0
    trap_price = 0.0
    is_absorbed = False
    
    for p in bottom_nodes:
        vols = bar.footprint[p]
        delta = vols['ask'] - vols['bid'] # negative delta = aggressive selling
        if delta <= delta_threshold:
            is_absorbed = True
            if delta < max_trap_delta:
                max_trap_delta = delta
                trap_price = p
                
    return is_absorbed, trap_price, max_trap_delta

def detect_absorption_short(bar: Bar, delta_threshold: int = 26, wick_ratio: float = 0.25) -> tuple[bool, float, int]:
    """
    Detect bearish absorption (trapped buyers at the top wick).
    Returns (is_absorbed, trap_price, trap_delta)
    """
    h = bar.high
    l = bar.low
    r = h - l
    if r <= 0:
        return False, 0.0, 0
        
    # Condition 1: Candle must not close at the highs (close in lower 50%)
    if bar.close > h - (r * 0.50):
        return False, 0.0, 0
        
    _, top_nodes = get_wick_nodes(bar, wick_ratio)
    
    max_trap_delta = 0
    trap_price = 0.0
    is_absorbed = False
    
    for p in top_nodes:
        vols = bar.footprint[p]
        delta = vols['ask'] - vols['bid'] # positive delta = aggressive buying
        if delta >= delta_threshold:
            is_absorbed = True
            if delta > max_trap_delta:
                max_trap_delta = delta
                trap_price = p
                
    return is_absorbed, trap_price, max_trap_delta
