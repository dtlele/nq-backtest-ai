"""Load the 1-minute OHLC cache (cache_ohlc/*.csv) into a single tidy frame.

Schema in cache: ``timestamp, open, high, low, close`` (UTC).
We add:
  - ``date``     : trading date in America/New_York
  - ``minute_et`` : minutes since 00:00 ET (0..1439) for fast slicing
  - ``ret_1m_pct``: 1-minute log return in % (NaN on the first bar of the day)

Bars are kept in UTC; the caller slices by ``minute_et`` to isolate phases.
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd

from src.day_similarity.config import (
    IB_END_H_ET, IB_END_M_ET, PRE_MARKET_START_H_ET,
    RTH_END_H_ET, RTH_END_M_ET,
    RTH_OPEN_H_ET, RTH_OPEN_M_ET,
)

ET_TZ = "America/New_York"


def _minute_et(ts_utc: pd.Series) -> pd.Series:
    """Return minutes since 00:00 ET for a UTC timestamp series."""
    et = ts_utc.dt.tz_convert(ET_TZ)
    return et.dt.hour * 60 + et.dt.minute


def _bar_ohlc_from_row(row) -> "_Bar":
    return _Bar(low=float(row.low), high=float(row.high))


@dataclass
class _Bar:
    low: float
    high: float


def load_all_bars(cache_dir: str = "cache_ohlc") -> pd.DataFrame:
    """Load every CSV in ``cache_dir`` into one frame indexed by timestamp.

    If ``data/similarity/bars_from_ticks.parquet`` exists (built by
    :mod:`ticks_loader`), prefer it — it has full microstructural info
    (buy/sell volume, delta, big trades) that the OHLC cache lacks.
    """
    ticks_path = os.path.join("data", "similarity", "bars_from_ticks.parquet")
    if os.path.exists(ticks_path):
        return pd.read_parquet(ticks_path)

    files = sorted(glob.glob(os.path.join(cache_dir, "*.csv")))
    if not files:
        raise FileNotFoundError(f"No CSV files in {cache_dir}")

    frames = []
    for f in files:
        df = pd.read_csv(f)
        # Normalize column names to lower.
        df.columns = [c.lower() for c in df.columns]
        if "timestamp" in df.columns:
            df["ts"] = pd.to_datetime(df["timestamp"], utc=True)
        elif "ts" in df.columns:
            df["ts"] = pd.to_datetime(df["ts"], utc=True)
        else:
            raise ValueError(f"{f}: no timestamp/ts column")
        df["date_et"] = df["ts"].dt.tz_convert(ET_TZ).dt.date
        df["minute_et"] = _minute_et(df["ts"])
        df["bar_range_ticks"] = (df["high"] - df["low"]) / 0.25
        df["bar_body_ticks"] = (df["close"] - df["open"]).abs() / 0.25
        df["ret_1m_pct"] = (df["close"] / df["open"] - 1.0) * 100.0
        frames.append(df[[
            "ts", "date_et", "minute_et", "open", "high", "low", "close",
            "bar_range_ticks", "bar_body_ticks", "ret_1m_pct",
        ]])
    out = pd.concat(frames, ignore_index=True).sort_values("ts").reset_index(drop=True)
    out["date_et"] = pd.to_datetime(out["date_et"])
    return out


def slice_phase(bars: pd.DataFrame, start_min: int, end_min: int) -> pd.DataFrame:
    """Return rows whose ``minute_et`` is in [start_min, end_min)."""
    return bars[(bars["minute_et"] >= start_min) & (bars["minute_et"] < end_min)]


def bars_for_date(all_bars: pd.DataFrame, date) -> pd.DataFrame:
    return all_bars[all_bars["date_et"] == pd.Timestamp(date)].reset_index(drop=True)


def iter_trading_dates(all_bars: pd.DataFrame) -> List[pd.Timestamp]:
    return sorted(all_bars["date_et"].unique().tolist())


# Convenience: minute-of-day bounds for the phases
MIN_PRE_START   = PRE_MARKET_START_H_ET * 60
MIN_RTH_OPEN    = RTH_OPEN_H_ET * 60 + RTH_OPEN_M_ET          # 9:30  = 570
MIN_IB_END      = IB_END_H_ET * 60 + IB_END_M_ET              # 10:00 = 600
MIN_PRED_END    = 10 * 60 + 30                                # 10:30 = 630
MIN_RTH_END     = RTH_END_H_ET * 60 + RTH_END_M_ET            # 16:00 = 960
