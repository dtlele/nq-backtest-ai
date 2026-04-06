import numpy as np
from src import Bar, VolumeProfile, VA_PERCENTAGE, TICK_BUCKET_SIZE

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

    hvn, lvn = [], []
    for i in range(len(volumes)):
        lo_v = volumes[i - 1] if i > 0 else float('inf')
        hi_v = volumes[i + 1] if i < len(volumes) - 1 else float('inf')
        if volumes[i] > lo_v and volumes[i] > hi_v:
            hvn.append(sorted_prices[i])
        elif volumes[i] < lo_v and volumes[i] < hi_v:
            lvn.append(sorted_prices[i])

    hvn = sorted(hvn, key=lambda p: -price_vol[p])[:5]
    lvn = sorted(lvn, key=lambda p: price_vol[p])[:5]

    return VolumeProfile(poc=poc, va_high=va_high, va_low=va_low,
                         hvn_levels=hvn, lvn_levels=lvn)
