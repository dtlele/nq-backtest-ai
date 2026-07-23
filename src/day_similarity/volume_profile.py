"""Real volume profile built from 1-min bars with buy/sell volume.

This module replaces the TPO fallback when microstructural data is
available.  It is structurally similar to :mod:`tpo`, but uses *actual*
contract volume (and optionally buy/sell breakdown) per tick bucket.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence

import numpy as np
import pandas as pd

from src.day_similarity.config import HVN_KEEP, LVN_KEEP, TICK_SIZE


@dataclass
class VolumeProfileResult:
    poc: float
    vah: float
    val: float
    hvn_levels: List[float] = field(default_factory=list)
    lvn_levels: List[float] = field(default_factory=list)
    hi: float = np.nan
    lo: float = np.nan
    total_volume: float = 0.0
    delta_total: float = 0.0      # signed: buy - sell
    delta_pct: float = 0.0        # abs(delta) / total_vol * 100


def _round(x: float) -> float:
    return round(x / TICK_SIZE) * TICK_SIZE


def build_volume_profile(bars: pd.DataFrame) -> VolumeProfileResult:
    """Build a true volume profile from a 1-min bar DataFrame.

    Expected columns: ``low, high, volume`` (required), ``buy_volume`` and
    ``sell_volume`` (optional, for delta stats).
    """
    if bars is None or bars.empty:
        return VolumeProfileResult(poc=np.nan, vah=np.nan, val=np.nan)
    if "volume" not in bars.columns:
        # fall back to a no-volume profile
        return VolumeProfileResult(poc=np.nan, vah=np.nan, val=np.nan)
    hi = float(bars["high"].max())
    lo = float(bars["low"].min())
    if hi <= lo:
        return VolumeProfileResult(poc=np.nan, vah=np.nan, val=np.nan)

    lo_tick = _round(lo)
    hi_tick = _round(hi)
    n_ticks = int(round((hi_tick - lo_tick) / TICK_SIZE)) + 1
    if n_ticks <= 0:
        return VolumeProfileResult(poc=np.nan, vah=np.nan, val=np.nan)

    visits = np.zeros(n_ticks, dtype=np.float64)
    for _, b in bars.iterrows():
        start_idx = int(round((_round(b["low"]) - lo_tick) / TICK_SIZE))
        end_idx   = int(round((_round(b["high"]) - lo_tick) / TICK_SIZE))
        start_idx = max(0, start_idx)
        end_idx   = min(n_ticks - 1, end_idx)
        if end_idx >= start_idx:
            ticks = end_idx - start_idx + 1
            per_tick = b["volume"] / ticks
            visits[start_idx:end_idx + 1] += per_tick

    total = float(visits.sum())
    if total == 0:
        return VolumeProfileResult(poc=np.nan, vah=np.nan, val=np.nan)

    poc_idx = int(np.argmax(visits))
    poc = lo_tick + poc_idx * TICK_SIZE
    target = 0.70 * total

    lo_idx = hi_idx = poc_idx
    captured = float(visits[poc_idx])
    while captured < target and (lo_idx > 0 or hi_idx < n_ticks - 1):
        add_lo = float(visits[lo_idx - 1]) if lo_idx > 0 else -1
        add_hi = float(visits[hi_idx + 1]) if hi_idx < n_ticks - 1 else -1
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

    # HVN/LVN
    hvn: List[tuple] = []
    lvn: List[tuple] = []
    i = 1
    while i < n_ticks - 1:
        start_i = i
        while i < n_ticks - 1 and visits[i] == visits[i + 1]:
            i += 1
        end_i = i
        left = visits[start_i - 1]
        right = visits[end_i + 1] if end_i + 1 < n_ticks else visits[end_i]
        mid_idx = (start_i + end_i) // 2
        v = float(visits[mid_idx])
        price = lo_tick + mid_idx * TICK_SIZE
        if v > left and v >= right:
            hvn.append((price, v - max(left, right)))
        elif v < left and v <= right:
            lvn.append((price, min(left, right) - v))
        i += 1
    hvn.sort(key=lambda x: x[1], reverse=True)
    lvn.sort(key=lambda x: x[1], reverse=True)
    hvn_levels = [p for p, _ in hvn[:HVN_KEEP]]
    lvn_levels = [p for p, _ in lvn[:LVN_KEEP]]

    # Delta stats
    delta_total = 0.0
    if "buy_volume" in bars.columns and "sell_volume" in bars.columns:
        delta_total = float((bars["buy_volume"] - bars["sell_volume"]).sum())

    return VolumeProfileResult(
        poc=poc, vah=vah, val=val,
        hvn_levels=hvn_levels, lvn_levels=lvn_levels,
        hi=hi, lo=lo, total_volume=total,
        delta_total=delta_total,
        delta_pct=abs(delta_total) / total * 100 if total else 0.0,
    )
