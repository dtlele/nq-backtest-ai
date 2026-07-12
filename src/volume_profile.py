import numpy as np
from src import Bar, VolumeProfile, VA_PERCENTAGE, TICK_BUCKET_SIZE, Trade

def compute_volume_profile(bars: list):
    if not bars:
        return None

    price_vol: dict = {}
    for bar in bars:
        p_low  = round(bar.low  / TICK_BUCKET_SIZE) * TICK_BUCKET_SIZE
        p_high = round(bar.high / TICK_BUCKET_SIZE) * TICK_BUCKET_SIZE
        ticks  = max(1, round((p_high - p_low) / TICK_BUCKET_SIZE) + 1)
        vol_per_tick = bar.volume / ticks
        price = p_low
        while price <= p_high + 1e-9:
            key = round(price / TICK_BUCKET_SIZE) * TICK_BUCKET_SIZE
            price_vol[key] = price_vol.get(key, 0) + vol_per_tick
            price += TICK_BUCKET_SIZE

    if not price_vol:
        return None

    sorted_prices = sorted(price_vol.keys())
    volumes       = [price_vol[p] for p in sorted_prices]
    total_vol     = sum(volumes)
    poc_idx       = int(np.argmax(volumes))
    poc           = sorted_prices[poc_idx]

    # Value Area: expand from POC until 70% captured
    va_vol = volumes[poc_idx]
    lo_idx = hi_idx = poc_idx
    while va_vol / total_vol < VA_PERCENTAGE:
        add_lo = volumes[lo_idx - 1] if lo_idx > 0 else 0
        add_hi = volumes[hi_idx + 1] if hi_idx < len(volumes) - 1 else 0
        if add_hi >= add_lo and hi_idx < len(volumes) - 1:
            hi_idx += 1; va_vol += add_hi
        elif lo_idx > 0:
            lo_idx -= 1; va_vol += add_lo
        else:
            break

    va_high = sorted_prices[hi_idx]
    va_low  = sorted_prices[lo_idx]

    hvn_candidates = []
    lvn_candidates = []
    
    n = len(volumes)
    i = 1
    while i < n - 1:
        start_i = i
        while i < n - 1 and volumes[i] == volumes[i+1]:
            i += 1
        end_i = i
        
        if end_i + 1 < n:
            left_val = volumes[start_i - 1]
            right_val = volumes[end_i + 1]
            mid_idx = (start_i + end_i) // 2
            v = volumes[mid_idx]
            price = sorted_prices[mid_idx]
            
            if v > left_val and v > right_val:
                prominence = v - max(left_val, right_val)
                hvn_candidates.append((price, prominence))
            elif v < left_val and v < right_val:
                depth = min(left_val, right_val) - v
                lvn_candidates.append((price, depth))
                
        i += 1

    # Sort by prominence (deepest gaps for LVN, highest peaks for HVN)
    hvn_candidates.sort(key=lambda x: x[1], reverse=True)
    lvn_candidates.sort(key=lambda x: x[1], reverse=True)
    
    hvn = [x[0] for x in hvn_candidates[:8]]
    lvn = [x[0] for x in lvn_candidates[:8]]

    return VolumeProfile(poc=poc, va_high=va_high, va_low=va_low,
                         hvn_levels=hvn, lvn_levels=lvn)

def compute_vwap(bars: list) -> tuple[float, float]:
    """Compute the VWAP and its Standard Deviation (VWAP, StdDev)."""
    if not bars:
        return 0.0, 0.0
    
    cum_pv = 0.0
    cum_vol = 0.0
    
    for bar in bars:
        hlc3 = (bar.high + bar.low + bar.close) / 3.0
        cum_pv += hlc3 * bar.volume
        cum_vol += bar.volume
        
    if cum_vol == 0:
        return bars[-1].close, 0.0
        
    vwap = cum_pv / cum_vol
    
    # Calculate Variance
    cum_var = 0.0
    for bar in bars:
        hlc3 = (bar.high + bar.low + bar.close) / 3.0
        cum_var += bar.volume * ((hlc3 - vwap) ** 2)
        
    std_dev = np.sqrt(cum_var / cum_vol)
    
    return vwap, std_dev

def classify_profile_shape(vp: VolumeProfile, high: float, low: float) -> str:
    """
    Classify the daily volume profile shape into P, B, or D based on MiniMax knowledge.
    - P-Shape: POC in the upper 35% of the range
    - B-Shape: POC in the lower 35% of the range
    - D-Shape: POC in the middle 30% of the range
    """
    if not vp or high <= low:
        return 'unknown'
    
    range_total = high - low
    poc_pct = (vp.poc - low) / range_total
    
    if poc_pct >= 0.65:
        return 'P'
    elif poc_pct <= 0.35:
        return 'B'
    else:
        return 'D'

def build_profile_from_trades(trades: list[Trade]) -> VolumeProfile:
    """
    Build a high-precision VolumeProfile directly from a list of Trade objects.
    Also identifies local peaks (HVN) and valleys/low volume areas (LVN).
    """
    if not trades:
        return None
        
    price_vol = {}
    for t in trades:
        price = round(t.price / 0.25) * 0.25
        price_vol[price] = price_vol.get(price, 0.0) + t.size
        
    if not price_vol:
        return None
        
    sorted_prices = sorted(price_vol.keys())
    volumes = [price_vol[p] for p in sorted_prices]
    total_vol = sum(volumes)
    poc_idx = int(np.argmax(volumes))
    poc = sorted_prices[poc_idx]
    
    # Value Area: 70% of volume
    va_vol = volumes[poc_idx]
    lo_idx = hi_idx = poc_idx
    while va_vol / total_vol < 0.70:
        add_lo = volumes[lo_idx - 1] if lo_idx > 0 else 0
        add_hi = volumes[hi_idx + 1] if hi_idx < len(volumes) - 1 else 0
        if add_hi >= add_lo and hi_idx < len(volumes) - 1:
            hi_idx += 1
            va_vol += add_hi
        elif lo_idx > 0:
            lo_idx -= 1
            va_vol += add_lo
        else:
            break
            
    va_high = sorted_prices[hi_idx]
    va_low = sorted_prices[lo_idx]
    
    # Identify HVN and LVN
    avg_vol = total_vol / len(volumes) if len(volumes) > 0 else 0.0
    lvn_candidates = []
    hvn_candidates = []
    
    # 1. Peak & Valley detection
    for i in range(1, len(volumes) - 1):
        v = volumes[i]
        p = sorted_prices[i]
        if v < volumes[i-1] and v < volumes[i+1]:
            # Valley (LVN)
            lvn_candidates.append((p, min(volumes[i-1], volumes[i+1]) - v))
        elif v > volumes[i-1] and v > volumes[i+1]:
            # Peak (HVN)
            hvn_candidates.append((p, v - max(volumes[i-1], volumes[i+1])))
            
    # 2. Add absolute Low Volume Nodes (less than 30% of average session node volume)
    for p, v in price_vol.items():
        if v < avg_vol * 0.30:
            # The lower the volume, the higher the priority as an LVN
            lvn_candidates.append((p, avg_vol * 0.30 - v))
            
    # Sort by prominence
    lvn_candidates.sort(key=lambda x: x[1], reverse=True)
    hvn_candidates.sort(key=lambda x: x[1], reverse=True)
    
    # Unique lists
    seen_lvns = set()
    lvns = []
    for item in lvn_candidates:
        if item[0] not in seen_lvns:
            seen_lvns.add(item[0])
            lvns.append(item[0])
            
    seen_hvns = set()
    hvns = []
    for item in hvn_candidates:
        if item[0] not in seen_hvns:
            seen_hvns.add(item[0])
            hvns.append(item[0])
            
    return VolumeProfile(
        poc=poc,
        va_high=va_high,
        va_low=va_low,
        hvn_levels=hvns[:5],
        lvn_levels=lvns[:5]
    )

def build_profile_from_bars(bars: list[Bar]) -> VolumeProfile:
    """
    Build a VolumeProfile by aggregating the footprints of a list of Bar objects.
    This is extremely fast compared to rebuilding from raw ticks.
    """
    if not bars:
        return None
        
    price_vol = {}
    for bar in bars:
        for price, vols in bar.footprint.items():
            tot = vols['bid'] + vols['ask']
            price_vol[price] = price_vol.get(price, 0.0) + tot
            
    if not price_vol:
        return None
        
    sorted_prices = sorted(price_vol.keys())
    volumes = [price_vol[p] for p in sorted_prices]
    total_vol = sum(volumes)
    poc_idx = int(np.argmax(volumes))
    poc = sorted_prices[poc_idx]
    
    # Value Area: 70% of volume
    va_vol = volumes[poc_idx]
    lo_idx = hi_idx = poc_idx
    while va_vol / total_vol < 0.70:
        add_lo = volumes[lo_idx - 1] if lo_idx > 0 else 0
        add_hi = volumes[hi_idx + 1] if hi_idx < len(volumes) - 1 else 0
        if add_hi >= add_lo and hi_idx < len(volumes) - 1:
            hi_idx += 1
            va_vol += add_hi
        elif lo_idx > 0:
            lo_idx -= 1
            va_vol += add_lo
        else:
            break
            
    va_high = sorted_prices[hi_idx]
    va_low = sorted_prices[lo_idx]
    
    # Identify HVN and LVN
    avg_vol = total_vol / len(volumes) if len(volumes) > 0 else 0.0
    lvn_candidates = []
    hvn_candidates = []
    
    # 1. Peak & Valley detection
    for i in range(1, len(volumes) - 1):
        v = volumes[i]
        p = sorted_prices[i]
        if v < volumes[i-1] and v < volumes[i+1]:
            # Valley (LVN)
            lvn_candidates.append((p, min(volumes[i-1], volumes[i+1]) - v))
        elif v > volumes[i-1] and v > volumes[i+1]:
            # Peak (HVN)
            hvn_candidates.append((p, v - max(volumes[i-1], volumes[i+1])))
            
    # 2. Add absolute Low Volume Nodes
    for p, v in price_vol.items():
        if v < avg_vol * 0.30:
            lvn_candidates.append((p, avg_vol * 0.30 - v))
            
    # Sort by prominence
    lvn_candidates.sort(key=lambda x: x[1], reverse=True)
    hvn_candidates.sort(key=lambda x: x[1], reverse=True)
    
    # Unique lists
    seen_lvns = set()
    lvns = []
    for item in lvn_candidates:
        if item[0] not in seen_lvns:
            seen_lvns.add(item[0])
            lvns.append(item[0])
            
    seen_hvns = set()
    hvns = []
    for item in hvn_candidates:
        if item[0] not in seen_hvns:
            seen_hvns.add(item[0])
            hvns.append(item[0])
            
    return VolumeProfile(
        poc=poc,
        va_high=va_high,
        va_low=va_low,
        hvn_levels=hvns[:5],
        lvn_levels=lvns[:5]
    )


