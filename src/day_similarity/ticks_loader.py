"""Load Databento NQ tick files into 1-minute OHLCV bars with full side info.

This module reads the raw ``glbx-mdp3-YYYYMMDD.trades.csv`` files that
Fabio's backtest uses and produces a tidy DataFrame with the same schema
as :func:`src.day_similarity.data_loader.load_all_bars` **plus** the
microstructural columns we need for richer day-similarity features.

Output columns
---------------
ts                UTC timestamp of the bar open
date_et           trading date in America/New_York
minute_et         minutes since 00:00 ET
open, high, low, close   bar OHLC
volume            total contracts traded
buy_volume        contracts where side='A' (aggressive buy)
sell_volume       contracts where side='B' (aggressive sell)
delta             buy_volume - sell_volume
delta_pct         abs(delta) / volume * 100
vwap              dollar-volume weighted average price
n_big_trades      number of trades with size >= NQ_BIG_TRADE_THRESHOLD
big_trade_volume  total size of those big trades
big_trade_buy     big-trade size on buy side
big_trade_sell    big-trade size on sell side
big_trade_delta   big_trade_buy - big_trade_sell
bar_range_ticks   (high-low)/0.25
bar_body_ticks    abs(close-open)/0.25
ret_1m_pct        (close/open - 1) * 100

Memory-efficient
----------------
We use ``usecols`` to load only the columns we need, then aggregate to
1-min bars with vectorized pandas groupby / resample.  A full 400k-trade
day fits in ~30 MB and aggregates in <0.5 s.
"""
from __future__ import annotations

import glob
import os
from typing import List, Optional

import numpy as np
import pandas as pd

from src import NQ_BIG_TRADE_THRESHOLD, NQ_TICK_SIZE
from src.day_similarity.data_loader import _minute_et

ET_TZ = "America/New_York"
TICK_SIZE = NQ_TICK_SIZE  # 0.25


# ──────────────────────────────────────────────────────────────────────────
# Single-day loader
# ──────────────────────────────────────────────────────────────────────────
def _load_one_file(filepath: str) -> pd.DataFrame:
    """Module-level wrapper for multiprocessing (Windows-safe)."""
    try:
        return _finalize(_load_one_day(filepath))
    except Exception:
        return pd.DataFrame()


def _load_one_day(filepath: str) -> pd.DataFrame:
    """Read one Databento tick file and return 1-min OHLCV bars."""
    cols = ["ts_event", "side", "price", "size", "symbol"]
    df = pd.read_csv(filepath, usecols=cols)
    # Filter to trades only (action column not strictly needed if file is trades-only)
    df = df[df["side"].isin(["A", "B", "N"])].copy()
    # Strip calendar spreads (e.g. NQM5-NQU5)
    df = df[~df["symbol"].str.contains("-", na=False)]
    if df.empty:
        return pd.DataFrame()

    # Pick the most-traded symbol (front month)
    sym_counts = df["symbol"].value_counts()
    if sym_counts.empty:
        return pd.DataFrame()
    front = sym_counts.idxmax()
    df = df[df["symbol"] == front].copy()
    if df.empty:
        return pd.DataFrame()

    df["ts"] = pd.to_datetime(df["ts_event"], utc=True)
    df["is_big"] = df["size"] >= NQ_BIG_TRADE_THRESHOLD
    # Vectorized aggregate columns
    df["buy_v"]    = np.where(df["side"] == "A", df["size"], 0)
    df["sell_v"]   = np.where(df["side"] == "B", df["size"], 0)
    df["b_buy_v"]  = np.where(df["is_big"] & (df["side"] == "A"), df["size"], 0)
    df["b_sell_v"] = np.where(df["is_big"] & (df["side"] == "B"), df["size"], 0)
    df["dollar"]   = df["price"] * df["size"]

    df["b_vol_v"] = np.where(df["is_big"], df["size"], 0)
    df["ts"] = df["ts"].dt.floor("1min")
    g = df.groupby("ts", sort=True)

    bars = pd.DataFrame({
        "open":     g["price"].first(),
        "high":     g["price"].max(),
        "low":      g["price"].min(),
        "close":    g["price"].last(),
        "volume":   g["size"].sum(),
        "buy_volume":  g["buy_v"].sum(),
        "sell_volume": g["sell_v"].sum(),
        "vwap":     g["dollar"].sum() / g["size"].sum(),
        "n_big_trades":    g["is_big"].sum().astype(np.int64),
        "big_trade_volume": g["b_vol_v"].sum(),
        "big_trade_buy":   g["b_buy_v"].sum(),
        "big_trade_sell":  g["b_sell_v"].sum(),
    })
    bars = bars.dropna(subset=["open"])
    bars = bars.reset_index()
    return bars


def _finalize(bars: pd.DataFrame) -> pd.DataFrame:
    """Add the derived columns that downstream code expects."""
    if bars.empty:
        return bars
    bars["date_et"] = bars["ts"].dt.tz_convert(ET_TZ).dt.date
    bars["date_et"] = pd.to_datetime(bars["date_et"])
    bars["minute_et"] = _minute_et(bars["ts"])
    bars["delta"] = bars["buy_volume"] - bars["sell_volume"]
    bars["delta_pct"] = np.where(
        bars["volume"] > 0, bars["delta"].abs() / bars["volume"] * 100.0, 0.0
    )
    bars["big_trade_delta"] = bars["big_trade_buy"] - bars["big_trade_sell"]
    bars["bar_range_ticks"] = (bars["high"] - bars["low"]) / TICK_SIZE
    bars["bar_body_ticks"]  = (bars["close"] - bars["open"]).abs() / TICK_SIZE
    bars["ret_1m_pct"] = (bars["close"] / bars["open"] - 1.0) * 100.0
    return bars[[
        "ts", "date_et", "minute_et",
        "open", "high", "low", "close",
        "volume", "buy_volume", "sell_volume", "delta", "delta_pct", "vwap",
        "n_big_trades", "big_trade_volume", "big_trade_buy", "big_trade_sell",
        "big_trade_delta",
        "bar_range_ticks", "bar_body_ticks", "ret_1m_pct",
    ]]


# ──────────────────────────────────────────────────────────────────────────
# Multi-day loader
# ──────────────────────────────────────────────────────────────────────────
def load_all_bars_from_ticks(databento_dir: str = r"C:/Users/Mauro/Documents/databento-data",
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             verbose: bool = True,
                             n_jobs: int = 4) -> pd.DataFrame:
    """Read every Databento tick file in ``databento_dir`` and concatenate
    into one 1-min OHLCV frame.

    Parameters
    ----------
    databento_dir   folder containing glbx-mdp3-YYYYMMDD.trades.csv files
    start_date      optional YYYYMMDD filter (inclusive)
    end_date        optional YYYYMMDD filter (inclusive)
    n_jobs          number of worker processes (1 = sequential)
    """
    pattern = os.path.join(databento_dir, "glbx-mdp3-*.trades.csv")
    files = sorted(glob.glob(pattern))
    if start_date:
        files = [f for f in files if os.path.basename(f).split("-")[2].split(".")[0] >= start_date]
    if end_date:
        files = [f for f in files if os.path.basename(f).split("-")[2].split(".")[0] <= end_date]
    if not files:
        raise FileNotFoundError(f"No Databento trades files in {databento_dir}")

    if verbose:
        print(f"Loading {len(files)} days of Databento ticks from {databento_dir} "
              f"(n_jobs={n_jobs}) ...")

    if n_jobs <= 1:
        frames: List[pd.DataFrame] = []
        for i, f in enumerate(files):
            d = _load_one_file(f)
            if not d.empty:
                frames.append(d)
            if verbose and ((i + 1) % 50 == 0 or i == len(files) - 1):
                print(f"  {i + 1}/{len(files)} days processed "
                      f"({sum(len(x) for x in frames):,} bars so far)")
    else:
        import multiprocessing as mp
        ctx = mp.get_context("spawn")  # windows-safe
        with ctx.Pool(processes=n_jobs) as pool:
            results = pool.map(_load_one_file, files)
        frames = [r for r in results if not r.empty]
        if verbose:
            total = sum(len(r) for r in frames)
            print(f"  {len(frames)} days kept, {total:,} bars total")

    if not frames:
        raise RuntimeError("No usable days in the selected range")

    out = pd.concat(frames, ignore_index=True).sort_values("ts").reset_index(drop=True)
    return out


# ──────────────────────────────────────────────────────────────────────────
# CLI: build the cached bars parquet
# ──────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--databento-dir", default=r"C:/Users/Mauro/Documents/databento-data")
    p.add_argument("--out", default="data/similarity/bars_from_ticks.parquet")
    p.add_argument("--n-jobs", type=int, default=4)
    args = p.parse_args()

    import time as _t
    t0 = _t.time()
    bars = load_all_bars_from_ticks(
        databento_dir=args.databento_dir,
        n_jobs=args.n_jobs,
        verbose=True,
    )
    print(f"Done in {_t.time() - t0:.1f}s, {len(bars):,} bars")
    out_path = args.out
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    bars.to_parquet(out_path, index=False)
    print(f"Wrote {out_path}")
