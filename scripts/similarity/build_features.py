"""Build the per-day feature matrix.

Usage:
    python scripts/similarity/build_features.py
    python scripts/similarity/build_features.py --cache-dir cache_ohlc --out data/similarity

It walks the trading calendar, computes features for every day that has a
prior day and a complete post-10:00 history, and writes a parquet to
``data/similarity/day_features.parquet``.  The rolling z-score columns
are added at the end in a second pass so that we don't leak the *current*
day's value into the rolling statistics.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.day_similarity.data_loader import (
    bars_for_date, iter_trading_dates, load_all_bars,
)
from src.day_similarity.features import (
    ROLLING_WINDOW_SESSIONS, build_day_context, build_history_stats,
    compute_features_for_day,
)


ZSCORE_COLS = [
    "pm_gap_pct", "pm_close_gap_pct", "pm_range_pct", "pm_drift_pct",
    "pm_mean_abs_ret_pct", "pm_total_range_ticks", "ib_range_pct",
    "ib_drift_pct", "ib_vs_pm_range_pct",
    "pm_vp_width_pct", "ib_vp_width_pct", "pm_skew", "ib_skew",
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--cache-dir", default="cache_ohlc")
    p.add_argument("--out", default="data/similarity")
    p.add_argument("--min-history", type=int, default=ROLLING_WINDOW_SESSIONS,
                   help="Days of history required before keeping a row (default = window).")
    args = p.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Loading 1-min bars from {args.cache_dir} ...")
    all_bars = load_all_bars(args.cache_dir)
    dates = iter_trading_dates(all_bars)
    print(f"      {len(dates)} trading days from {dates[0].date()} to {dates[-1].date()}")

    print("[2/4] Building per-day features ...")
    rows = []
    for idx, date in enumerate(dates):
        if idx == 0:
            prior_bars = None
        else:
            prior_bars = bars_for_date(all_bars, dates[idx - 1])
        # rolling history of *prior* daily range (only days strictly before today)
        hist_ranges = pd.Series(
            [r["ib_vs_adr_pct"] for r in rows[-ROLLING_WINDOW_SESSIONS:]],
            dtype=float,
        )
        # actually the ADR used in features is the median of the 20-day
        # daily range in *points*, not %.  Build that history instead.
        hist_range_pts = pd.Series(
            [r.get("_prior_day_range_pts", np.nan) for r in rows[-ROLLING_WINDOW_SESSIONS:]],
            dtype=float,
        )
        ctx = build_day_context(date, all_bars, prior_bars, history_ranges=hist_range_pts)
        if ctx is None:
            continue
        feat = compute_features_for_day(ctx)
        feat["_prior_day_range_pts"] = ctx.prior_day_range
        rows.append(feat)
        if (idx + 1) % 50 == 0 or idx == len(dates) - 1:
            print(f"      {idx + 1}/{len(dates)} days processed")

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    print(f"      raw feature frame: {df.shape}")

    print("[3/4] Adding rolling z-score columns ...")
    keep = [c for c in ZSCORE_COLS if c in df.columns]
    df = build_history_stats(df, keep, window=ROLLING_WINDOW_SESSIONS)

    # Drop days without enough history (no z-scores available)
    z_required = [f"z_{c}" for c in keep]
    n_before = len(df)
    df = df.dropna(subset=z_required, how="all").reset_index(drop=True)
    n_after = len(df)
    print(f"      dropped {n_before - n_after} days without enough history "
          f"(kept {n_after})")

    # Drop the helper column we used for ADR computation
    if "_prior_day_range_pts" in df.columns:
        df = df.drop(columns=["_prior_day_range_pts"])

    out_path = out_dir / "day_features.parquet"
    df.to_parquet(out_path, index=False)
    print(f"[4/4] Wrote {df.shape[0]} rows x {df.shape[1]} cols to {out_path}")

    # Sanity: list NaN rate per column
    nan_rate = df.isna().mean().sort_values(ascending=False)
    print("\nTop NaN-rate columns:")
    print(nan_rate.head(15).round(3).to_string())


if __name__ == "__main__":
    main()
