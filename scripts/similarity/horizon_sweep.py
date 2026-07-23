"""Benchmark predictability across multiple intraday horizons.

The user originally asked about 10:00->10:30 (after IB) and "after 30
minutes, what happens".  This script systematically evaluates all
common horizons and ranks them by out-of-sample predictability.

Output: prints a table sorted by correlation, saves the result as
``data/similarity/horizon_benchmark.csv`` and ``horizon_benchmark.md``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.day_similarity.data_loader import (
    MIN_IB_END, MIN_PRE_START, MIN_RTH_END, MIN_RTH_OPEN, bars_for_date,
    load_all_bars, slice_phase,
)
from src.day_similarity.features import (
    DayContext, build_day_context, compute_features_for_day,
)


# Horizons to evaluate.  Each entry is a label and a tuple of
# (start_min, end_min) in ET minutes since 00:00.
HORIZONS = [
    ("10:00->10:05",    10 * 60,       10 * 60 + 5),
    ("10:00->10:10",    10 * 60,       10 * 60 + 10),
    ("10:00->10:15",    10 * 60,       10 * 60 + 15),
    ("10:00->10:30",    10 * 60,       10 * 60 + 30),
    ("10:00->10:45",    10 * 60,       10 * 60 + 45),
    ("10:00->11:00",    10 * 60,       11 * 60),
    ("10:00->11:30",    10 * 60,       11 * 60 + 30),
    ("10:00->12:00",    10 * 60,       12 * 60),
    ("10:00->13:00",    10 * 60,       13 * 60),
    ("10:00->14:00",    10 * 60,       14 * 60),
    ("10:00->15:00",    10 * 60,       15 * 60),
    ("10:00->16:00",    10 * 60,       16 * 60),
    # Mid-day (post-lunch often different regime)
    ("12:00->13:00",    12 * 60,       13 * 60),
    ("13:00->14:00",    13 * 60,       14 * 60),
    ("14:00->15:00",    14 * 60,       15 * 60),
    # Close period (MOC imbalance)
    ("15:00->15:30",    15 * 60,       15 * 60 + 30),
    ("15:30->16:00",    15 * 60 + 30,  16 * 60),
    # First hour summary
    ("09:30->10:30",    9 * 60 + 30,   10 * 60 + 30),
]


def compute_horizon_outcome(day: pd.DataFrame, start_min: int, end_min: int,
                            ref: float) -> dict:
    """Return a dict of outcome metrics for a given intraday window."""
    win = slice_phase(day, start_min, end_min)
    if win.empty or len(win) < 2:
        return {"ret": float("nan"), "range": float("nan"),
                "mfe": float("nan"), "mae": float("nan"),
                "dir": float("nan"), "vol": float("nan")}
    r = float(win["open"].iloc[0])
    h = float(win["high"].max())
    l = float(win["low"].min())
    c = float(win["close"].iloc[-1])
    if r == 0:
        return {"ret": float("nan"), "range": float("nan"),
                "mfe": float("nan"), "mae": float("nan"),
                "dir": float("nan"), "vol": float("nan")}
    return {
        "ret":   (c - r) / r * 100.0,
        "range": (h - l) / r * 100.0,
        "mfe":   (h - r) / r * 100.0,
        "mae":   (r - l) / r * 100.0,
        "dir":   float(np.sign(c - r)),
        "vol":   float(win["volume"].sum()) if "volume" in win.columns else float("nan"),
    }


def main() -> None:
    out_dir = Path("data/similarity")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading ticks-bars cache ...")
    all_bars = load_all_bars("cache_ohlc")
    print(f"  {len(all_bars):,} bars, {all_bars['date_et'].nunique()} days")

    # We need features to use as predictors.  Re-build the day_features
    # frame so we have everything on hand, but here we shortcut: use the
    # existing day_features.parquet and just compute the new outcomes.
    df_feat = pd.read_parquet(out_dir / "day_features.parquet").sort_values("date").reset_index(drop=True)
    feat_cols = [c for c in df_feat.columns if c not in ["date"]
                 and not any(t in c for t in ("ret_pct", "mfe_pct", "mae_pct",
                                              "range_pct", "dir_sign"))]
    feat_cols = [c for c in feat_cols if pd.api.types.is_numeric_dtype(df_feat[c])]
    X = df_feat[feat_cols].to_numpy(dtype=float)
    X = pd.DataFrame(X).fillna(pd.DataFrame(X).median()).to_numpy()

    rows = []
    for label, start_min, end_min in HORIZONS:
        print(f"  computing outcomes for {label} ...")
        outcome_idx = []
        outcome_ret = []
        outcome_range = []
        outcome_mfe = []
        outcome_mae = []
        outcome_dir = []
        for _, row in df_feat.iterrows():
            d = row["date"]
            day = bars_for_date(all_bars, d)
            if day.empty:
                continue
            ref = float("nan")
            # use the close at start_min as the reference
            win = slice_phase(day, start_min, end_min)
            if win.empty or len(win) < 2:
                continue
            ref = float(win["open"].iloc[0])
            if ref == 0:
                continue
            out = compute_horizon_outcome(day, start_min, end_min, ref)
            if not np.isfinite(out["ret"]):
                continue
            outcome_idx.append(d)
            outcome_ret.append(out["ret"])
            outcome_range.append(out["range"])
            outcome_mfe.append(out["mfe"])
            outcome_mae.append(out["mae"])
            outcome_dir.append(out["dir"])
        if not outcome_ret:
            continue
        # Build a target array aligned to df_feat rows
        target_ret = pd.Series(outcome_ret, index=pd.to_datetime(outcome_idx))
        target_range = pd.Series(outcome_range, index=pd.to_datetime(outcome_idx))
        target_mfe = pd.Series(outcome_mfe, index=pd.to_datetime(outcome_idx))
        target_mae = pd.Series(outcome_mae, index=pd.to_datetime(outcome_idx))
        target_dir = pd.Series(outcome_dir, index=pd.to_datetime(outcome_idx))

        y_ret   = df_feat["date"].map(target_ret).to_numpy()
        y_range = df_feat["date"].map(target_range).to_numpy()
        y_mfe   = df_feat["date"].map(target_mfe).to_numpy()
        y_mae   = df_feat["date"].map(target_mae).to_numpy()
        y_dir   = df_feat["date"].map(target_dir).to_numpy()

        # Walk-forward evaluation (4 targets per horizon)
        from sklearn.ensemble import GradientBoostingRegressor
        results_for_horizon = {}
        for tgt_name, y in [("ret", y_ret), ("range", y_range),
                             ("mfe", y_mfe), ("mae", y_mae)]:
            preds = np.full(len(df_feat), np.nan)
            for i in range(80, len(df_feat)):
                mask = np.isfinite(y[:i])
                if mask.sum() < 30:
                    continue
                m = GradientBoostingRegressor(
                    n_estimators=100, max_depth=3, learning_rate=0.05, random_state=0
                ).fit(X[:i][mask], y[:i][mask])
                preds[i] = m.predict(X[i:i+1])[0]
            valid = np.isfinite(y) & np.isfinite(preds)
            yv, pv = y[valid], preds[valid]
            if len(yv) < 30:
                continue
            cor = float(np.corrcoef(yv, pv)[0, 1])
            rmse = float(np.sqrt(((yv - pv) ** 2).mean()))
            rmse0 = float(np.sqrt(((yv - np.nanmean(yv)) ** 2).mean()))
            results_for_horizon[tgt_name] = {
                "n": int(valid.sum()),
                "cor": cor,
                "rmse": rmse,
                "rmse_base": rmse0,
                "improv_pct": (rmse0 - rmse) / rmse0 * 100 if rmse0 else float("nan"),
            }
        # Direction accuracy using a directional classifier
        valid_dir = np.isfinite(y_dir)
        if valid_dir.any():
            dir_acc = float((y_dir[valid_dir] == np.sign(_)).mean())  # placeholder
        # Use the GBR ret prediction to evaluate directional hit rate
        preds = np.full(len(df_feat), np.nan)
        for i in range(80, len(df_feat)):
            mask = np.isfinite(y_ret[:i])
            if mask.sum() < 30:
                continue
            m = GradientBoostingRegressor(
                n_estimators=100, max_depth=3, learning_rate=0.05, random_state=0
            ).fit(X[:i][mask], y_ret[:i][mask])
            preds[i] = m.predict(X[i:i+1])[0]
        valid = np.isfinite(y_ret) & np.isfinite(preds) & (y_ret != 0)
        if valid.sum() > 30:
            dir_acc = float((np.sign(y_ret[valid]) == np.sign(preds[valid])).mean())
        else:
            dir_acc = float("nan")

        row = {
            "horizon": label,
            "start_min": start_min,
            "end_min": end_min,
            "duration_min": end_min - start_min,
            "dir_acc": dir_acc,
            **{f"{k}_{m}": v for k, d in results_for_horizon.items()
               for m, v in d.items()},
        }
        rows.append(row)
        print(f"    -> range cor={results_for_horizon.get('range', {}).get('cor', float('nan')):+.3f} "
              f"ret cor={results_for_horizon.get('ret',   {}).get('cor', float('nan')):+.3f} "
              f"dir_acc={dir_acc:.3f}")

    bench = pd.DataFrame(rows)
    bench.to_csv(out_dir / "horizon_benchmark.csv", index=False)

    # Pretty markdown
    pretty = bench[[
        "horizon", "duration_min", "dir_acc",
        "range_cor", "range_improv_pct",
        "ret_cor", "ret_improv_pct",
        "mfe_cor", "mae_cor",
    ]].copy()
    pretty = pretty.rename(columns={
        "horizon": "Horizon",
        "duration_min": "Dur (min)",
        "dir_acc": "Dir-acc",
        "range_cor": "R-corr",
        "range_improv_pct": "R-improv%",
        "ret_cor": "Ret-corr",
        "ret_improv_pct": "Ret-improv%",
        "mfe_cor": "MFE-corr",
        "mae_cor": "MAE-corr",
    })
    pretty = pretty.sort_values("R-corr", ascending=False)
    md = ["# Horizon predictability benchmark", "",
          "All targets are out-of-sample walk-forward, GBR-100 trees, d=3.",
          "Sorted by R-corr (range predictability).", "",
          "```", pretty.to_string(index=False), "```"]
    (out_dir / "horizon_benchmark.md").write_text("\n".join(md))

    print()
    print("=" * 80)
    print("Sorted by range correlation (best -> worst):")
    print(pretty.to_string(index=False))


if __name__ == "__main__":
    main()
