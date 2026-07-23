"""TPO (Time-Price-Opportunity) profile.

Why TPO instead of Volume Profile?  ``cache_ohlc`` ships 1-minute OHLC bars
without per-side volume.  TPO reconstructs a profile from price+time alone:
every minute the market *visits* every tick between the bar's low and high,
and we count visits per tick.  This is the standard CBOT/CME market-profile
approach and is structurally close to a volume profile in shape.

All price levels are returned in the input unit (NQ points).  Widths and
distances are converted to PERCENTAGES by the caller (no hardcoded
multipliers here).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Sequence, Tuple

import numpy as np

from src.day_similarity.config import HVN_KEEP, LVN_KEEP, TICK_SIZE


@dataclass
class TPOProfile:
    """Time-Price-Opportunity profile.

    All levels are absolute NQ points.  Conversion to % is done by the
    feature engineer to keep this module self-contained and unit-free.
    """
    poc: float                       # Point Of Control (modal tick)
    vah: float                       # Value Area High
    val: float                       # Value Area Low
    hvn_levels: List[float] = field(default_factory=list)  # up to HVN_KEEP
    lvn_levels: List[float] = field(default_factory=list)  # up to LVN_KEEP
    hi: float = np.nan               # raw high of the phase
    lo: float = np.nan               # raw low of the phase
    n_tpos: int = 0                  # total TPOs (sum of all visit counts)


def _round_to_tick(x: float) -> float:
    return round(x / TICK_SIZE) * TICK_SIZE


def build_tpo(bars: Sequence) -> TPOProfile:
    """Build a TPO profile from a sequence of bar-like objects.

    Each bar must expose ``.low`` and ``.high`` (absolute price).  The
    function does NOT need volume.  TPO count per tick = number of minutes
    that visited that tick.
    """
    if not bars:
        return TPOProfile(poc=np.nan, vah=np.nan, val=np.nan)

    hi = max(b.high for b in bars)
    lo = min(b.low for b in bars)

    lo_tick = _round_to_tick(lo)
    hi_tick = _round_to_tick(hi)
    if hi_tick < lo_tick:
        return TPOProfile(poc=np.nan, vah=np.nan, val=np.nan)

    n_ticks = int(round((hi_tick - lo_tick) / TICK_SIZE)) + 1
    if n_ticks <= 0:
        return TPOProfile(poc=np.nan, vah=np.nan, val=np.nan)

    visits = np.zeros(n_ticks, dtype=np.int64)
    for b in bars:
        # Mark every tick from low to high as visited by this bar.
        start_idx = int(round((_round_to_tick(b.low) - lo_tick) / TICK_SIZE))
        end_idx   = int(round((_round_to_tick(b.high) - lo_tick) / TICK_SIZE))
        start_idx = max(0, start_idx)
        end_idx   = min(n_ticks - 1, end_idx)
        if end_idx >= start_idx:
            visits[start_idx:end_idx + 1] += 1

    if visits.sum() == 0:
        return TPOProfile(poc=np.nan, vah=np.nan, val=np.nan)

    poc_idx = int(np.argmax(visits))
    poc = lo_tick + poc_idx * TICK_SIZE
    total = visits.sum()
    target = int(0.70 * total)  # 70 % value area

    # Expand from POC outward, choosing the side with more TPOs.
    lo_idx = hi_idx = poc_idx
    captured = int(visits[poc_idx])
    while captured < target and (lo_idx > 0 or hi_idx < n_ticks - 1):
        add_lo = int(visits[lo_idx - 1]) if lo_idx > 0 else -1
        add_hi = int(visits[hi_idx + 1]) if hi_idx < n_ticks - 1 else -1
        # Tie-break: prefer expanding upward to keep stable Value Area.
        if add_hi >= add_lo and hi_idx < n_ticks - 1:
            hi_idx += 1
            captured += add_hi
        elif lo_idx > 0:
            lo_idx -= 1
            captured += add_lo
        else:
            break

    vah = lo_tick + hi_idx * TICK_SIZE
    val = lo_tick + lo_idx * TICK_SIZE

    # Find HVN / LVN: a local max / min in visits with a "valley" on at
    # least one side.  We collapse plateaus to their midpoint.
    hvn: List[Tuple[float, int]] = []
    lvn: List[Tuple[float, int]] = []
    i = 1
    while i < n_ticks - 1:
        start_i = i
        while i < n_ticks - 1 and visits[i] == visits[i + 1]:
            i += 1
        end_i = i
        left = visits[start_i - 1]
        right = visits[end_i + 1] if end_i + 1 < n_ticks else visits[end_i]
        mid_idx = (start_i + end_i) // 2
        v = int(visits[mid_idx])
        price = lo_tick + mid_idx * TICK_SIZE
        if v > left and v >= right:
            prominence = v - max(left, right)
            hvn.append((price, prominence))
        elif v < left and v <= right:
            depth = min(left, right) - v
            lvn.append((price, depth))
        i += 1

    hvn.sort(key=lambda x: x[1], reverse=True)
    lvn.sort(key=lambda x: x[1], reverse=True)
    hvn_levels = [p for p, _ in hvn[:HVN_KEEP]]
    lvn_levels = [p for p, _ in lvn[:LVN_KEEP]]

    return TPOProfile(
        poc=poc, vah=vah, val=val,
        hvn_levels=hvn_levels, lvn_levels=lvn_levels,
        hi=hi, lo=lo, n_tpos=int(total),
    )


def level_to_pct(level: float, ref: float) -> float:
    """Express a level (in NQ points) as % distance from a reference price.

    Returns NaN if either is NaN.  Used to convert *every* price-based
    feature into a unit-free number.  ``ref`` is normally the close at the
    moment of observation (e.g. 9:29 ET for the pre-market profile).
    """
    if not np.isfinite(level) or not np.isfinite(ref) or ref == 0:
        return float("nan")
    return (level - ref) / ref * 100.0
