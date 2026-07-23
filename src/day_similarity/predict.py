"""Predict module — the production-facing API.

Usage (from a script or notebook):
    from src.day_similarity.predict import DaySimilarityPredictor
    p = DaySimilarityPredictor()
    p.load("data/similarity")
    result = p.predict_for_today(
        pre_market_bars_df,   # 1-min OHLC of today's pre-market 00:00..9:29 ET
        ib_bars_df=None,      # 1-min OHLC of today's 9:30..10:00 ET  (optional)
        current_date=pd.Timestamp("2026-06-19"),
    )
    result.show()  # prints a textual summary + path fan

The class bundles all the artefacts we built:
  * day_features.parquet     (the 230-day history)
  * gmm_labels.parquet       (soft cluster assignments)
  * umap_2d.parquet          (2-D UMAP layout)
  * contrastive_emb.parquet  (supervised embedding)
  * scalers / model weights  (regression + classifiers)
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.day_similarity.config import (
    IB_PREFIX, OUTCOME_HORIZONS_MIN, PM_PREFIX, REST_OF_DAY_MARKER,
)
from src.day_similarity.data_loader import (
    bars_for_date, load_all_bars, slice_phase,
    MIN_IB_END, MIN_PRED_END, MIN_PRE_START, MIN_RTH_END, MIN_RTH_OPEN,
)
from src.day_similarity.features import (
    DayContext, build_day_context, build_history_stats,
    compute_features_for_day,
)
from src.day_similarity.tpo import TPOProfile, build_tpo


# ──────────────────────────────────────────────────────────────────────────
# Feature preparation
# ──────────────────────────────────────────────────────────────────────────
FEATURE_COLS_PATH = "feature_columns.json"


def _feature_columns() -> List[str]:
    """The features the user-facing API expects.

    These are the columns produced by ``compute_features_for_day`` plus the
    rolling z-scores added by ``build_history_stats``.  Order is fixed.
    """
    base = [
        # pre-market
        "pm_gap_pct", "pm_close_gap_pct", "pm_high_above_close_pct",
        "pm_low_below_close_pct", "pm_range_pct", "pm_drift_pct",
        "pm_path_efficiency", "pm_position_in_prior_day",
        "pm_mean_abs_ret_pct", "pm_total_range_ticks",
        "pm_n_up_bars", "pm_n_down_bars", "pm_directional_consistency",
        "pm_vp_width_pct", "pm_poc_close_pct", "pm_poc_in_va_pct",
        "pm_close_in_va_pct", "pm_skew", "pm_hvn_count", "pm_lvn_count",
        "pm_hvn_density", "pm_lvn_max_gap_pct",
        "pm_dist_to_nearest_hvn_pct", "pm_dist_to_nearest_lvn_pct",
        # initial balance
        "ib_range_pct", "ib_close_position", "ib_drift_pct",
        "ib_vs_pm_range_pct", "ib_vs_prior_day_range_pct", "ib_vs_adr_pct",
        "ib_high_vs_pm_vah_pct", "ib_low_vs_pm_val_pct",
        "ib_close_vs_pm_poc_pct", "ib_close_vs_pm_vah_pct",
        "ib_close_vs_pm_val_pct", "ib_close_vs_pm_close_pct",
        "ib_total_range_ticks",
        "ib_vp_width_pct", "ib_poc_close_pct", "ib_poc_in_va_pct",
        "ib_close_in_va_pct", "ib_skew", "ib_hvn_count", "ib_lvn_count",
        "ib_dist_to_nearest_hvn_pct", "ib_dist_to_nearest_lvn_pct",
        # calendar
        "dow", "week_of_month", "is_opex_week", "is_month_end",
        "is_turn_of_month",
    ]
    z = [
        "z_pm_gap_pct", "z_pm_close_gap_pct", "z_pm_range_pct",
        "z_pm_drift_pct", "z_pm_mean_abs_ret_pct", "z_pm_total_range_ticks",
        "z_ib_range_pct", "z_ib_drift_pct", "z_ib_vs_pm_range_pct",
        "z_pm_vp_width_pct", "z_ib_vp_width_pct", "z_pm_skew", "z_ib_skew",
    ]
    return base + z


def _bar_from_row(row):
    """Tiny adapter so build_tpo can use the dataframe rows."""
    class _B:
        pass
    b = _B()
    b.low = float(row.low)
    b.high = float(row.high)
    return b


# ──────────────────────────────────────────────────────────────────────────
# Result object
# ──────────────────────────────────────────────────────────────────────────
@dataclass
class PredictResult:
    date: pd.Timestamp
    n_similar_days: int
    similar_dates: List[pd.Timestamp]
    similar_distances: List[float]
    similar_outcomes: List[Dict[str, float]]
    predicted_range_pct: float
    predicted_range_p10: float
    predicted_range_p90: float
    predicted_direction: float   # in [-1, 1]  (mixture probability)
    cluster_assignments: Dict[str, float]   # cluster_id -> probability
    dominant_cluster: int
    path_fan: Dict[str, np.ndarray] = field(default_factory=dict)
    feature_snapshot: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)

    def show(self) -> None:
        print("=" * 70)
        print(f"PredictResult  date={self.date.date()}  "
              f"dominant cluster={self.dominant_cluster}")
        print("-" * 70)
        print(f"Top {self.n_similar_days} similar historical days:")
        for d, dist in zip(self.similar_dates, self.similar_distances):
            print(f"   {pd.Timestamp(d).date()}   d={dist:.3f}")
        print("-" * 70)
        print(f"Predicted 30m RANGE next: "
              f"{self.predicted_range_pct:.3f}%  "
              f"[P10={self.predicted_range_p10:.3f}%  "
              f"P90={self.predicted_range_p90:.3f}%]")
        print(f"Predicted direction bias: {self.predicted_direction:+.3f}  "
              f"(0 = no edge, 1 = strong up bias)")
        print("-" * 70)
        for n in self.notes:
            print(f"  * {n}")
        print("=" * 70)


# ──────────────────────────────────────────────────────────────────────────
# Main predictor
# ──────────────────────────────────────────────────────────────────────────
class DaySimilarityPredictor:
    """Stateless predictor loaded from a directory of artefacts."""

    def __init__(self) -> None:
        self.history: Optional[pd.DataFrame] = None      # day_features.parquet
        self.umap: Optional[pd.DataFrame] = None
        self.gmm: Optional[pd.DataFrame] = None
        self.contrastive: Optional[pd.DataFrame] = None
        self.bars: Optional[pd.DataFrame] = None
        self.feature_columns: List[str] = []
        self.horizon_target = "range_pct_next_30m"
        # GMM components (loaded from joblib if available)
        self._gmm_model = None
        self._umap_model = None
        self._range_model = None

    # ---------- loading ----------
    def load(self, artefact_dir: str | Path) -> None:
        artefact_dir = Path(artefact_dir)
        self.history = pd.read_parquet(artefact_dir / "day_features.parquet")
        self.history = self.history.sort_values("date").reset_index(drop=True)
        # Keep only the columns we use, and remember them in order
        self.feature_columns = [c for c in _feature_columns() if c in self.history.columns]
        if (artefact_dir / "umap_2d.parquet").exists():
            self.umap = pd.read_parquet(artefact_dir / "umap_2d.parquet")
        if (artefact_dir / "gmm_labels.parquet").exists():
            self.gmm = pd.read_parquet(artefact_dir / "gmm_labels.parquet")
        if (artefact_dir / "contrastive_emb.parquet").exists():
            self.contrastive = pd.read_parquet(artefact_dir / "contrastive_emb.parquet")
        # Optional: load the actual fitted models (joblib) if saved.
        # Map:  file 'gmm.joblib'        -> attribute self._gmm_model
        #       file 'umap.joblib'       -> attribute self._umap_model
        #       file 'range.joblib'      -> attribute self._range_model
        try:
            import joblib
            for filename, attr in (
                ("gmm.joblib",    "_gmm_model"),
                ("umap.joblib",   "_umap_model"),
                ("range.joblib",  "_range_model"),
            ):
                fp = artefact_dir / filename
                if fp.exists():
                    bundle = joblib.load(fp)
                    if isinstance(bundle, dict) and "model" in bundle:
                        setattr(self, attr, bundle["model"])
                        setattr(self, attr + "_meta", bundle)
                    else:
                        setattr(self, attr, bundle)
        except ImportError:
            pass

    # ---------- features for a new day ----------
    def features_for(self,
                     date: pd.Timestamp,
                     pre: pd.DataFrame,
                     ib: Optional[pd.DataFrame] = None,
                     pred_window: Optional[pd.DataFrame] = None,
                     eod_window: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """Compute features for a *partial* day.

        ``pre`` is required (00:00..9:30 ET 1-min bars).  ``ib`` is optional —
        if provided we use it; otherwise the IB features are set to NaN.
        """
        prior_dates = sorted(self.history["date"].unique().tolist())
        prior = None
        for d in prior_dates:
            if pd.Timestamp(d) < date:
                prior = d
        prior_bars = None
        if prior is not None and self.bars is not None:
            prior_bars = bars_for_date(self.bars, pd.Timestamp(prior))
        elif self.bars is not None:
            # If we have the bars loaded, look for the most recent prior day
            prior_bars = self.bars[self.bars["date_et"] < date].tail(1000)

        # Build a context
        class _FakeRange: ...
        # Re-use build_day_context with synthetic slices
        if ib is None:
            # make a fake empty frame for the IB slice
            ib = pre.iloc[0:0].copy()
        if pred_window is None:
            pred_window = pre.iloc[0:0].copy()
        if eod_window is None:
            eod_window = pre.iloc[0:0].copy()

        hist_range_pts = self.history["ib_vs_adr_pct"].iloc[-60:] * 0
        # we don't have the raw prior_day_range in the saved frame; use the
        # pm_total_range_ticks / 4 as a rough proxy scaled by the close.
        # In practice the caller should provide a richer history if needed.
        ctx = DayContext(
            date=pd.Timestamp(date),
            pre=pre, ib=ib, pred_window=pred_window, eod_window=eod_window,
            prior_rth_close=float("nan"),
            prior_day_high=float("nan"),
            prior_day_low=float("nan"),
            prior_day_range=float("nan"),
            adr20=float("nan"),
        )
        feat = compute_features_for_day(ctx)
        return feat

    # ---------- top-k similar days ----------
    def top_k_similar(self,
                      feat: Dict[str, float],
                      k: int = 5,
                      metric: str = "zscore") -> List[Tuple[pd.Timestamp, float, Dict[str, float]]]:
        """Return (date, distance, outcome_dict) for the k most similar history days.

        metric = "zscore"  -> euclidean on z-scored feature rows
        metric = "umap"    -> euclidean on UMAP 2-D coordinates
        """
        if self.history is None:
            raise RuntimeError("Call .load() first")
        cols = [c for c in self.feature_columns if c in self.history.columns]
        X = self.history[cols].to_numpy(dtype=float)
        # Impute + z-score using *history* statistics (no leak)
        means = np.nanmean(X, axis=0)
        stds = np.nanstd(X, axis=0)
        stds[stds == 0] = 1.0
        Xz = (X - means) / stds

        x = np.array([feat.get(c, np.nan) for c in cols], dtype=float)
        xz = (x - means) / stds
        xz = np.nan_to_num(xz, nan=0.0)

        if metric == "umap" and self.umap is not None and self._umap_model is not None:
            # Project the new day into UMAP space
            x_umap = self._umap_model.transform(xz.reshape(1, -1))[0]
            hist_umap = self.umap[["x", "y"]].to_numpy()
            d = np.linalg.norm(hist_umap - x_umap, axis=1)
        else:
            d = np.linalg.norm(Xz - xz, axis=1)

        idx = np.argsort(d)[:k]
        out: List[Tuple[pd.Timestamp, float, Dict[str, float]]] = []
        for i in idx:
            row = self.history.iloc[i]
            d_date = pd.Timestamp(row["date"])
            out.append((
                d_date,
                float(d[i]),
                {
                    "ret_pct_next_30m": float(row.get("ret_pct_next_30m", float("nan"))),
                    "range_pct_next_30m": float(row.get("range_pct_next_30m", float("nan"))),
                    "mfe_pct_next_30m": float(row.get("mfe_pct_next_30m", float("nan"))),
                    "mae_pct_next_30m": float(row.get("mae_pct_next_30m", float("nan"))),
                    "dir_sign_next_30m": float(row.get("dir_sign_next_30m", float("nan"))),
                    "ret_pct_eod": float(row.get("ret_pct_eod", float("nan"))),
                },
            ))
        return out

    # ---------- cluster assignment ----------
    def cluster_probability(self, feat: Dict[str, float]) -> Dict[int, float]:
        if self.gmm is None or self._gmm_model is None:
            return {}
        cols = [c for c in self.feature_columns if c in self.history.columns]
        means = np.nanmean(self.history[cols].to_numpy(dtype=float), axis=0)
        stds = np.nanstd(self.history[cols].to_numpy(dtype=float), axis=0)
        stds[stds == 0] = 1.0
        x = np.array([feat.get(c, np.nan) for c in cols], dtype=float)
        xz = (x - means) / stds
        xz = np.nan_to_num(xz, nan=0.0)
        # If we have a fitted UMAP, use that as input
        if self._umap_model is not None:
            x_emb = self._umap_model.transform(xz.reshape(1, -1))
        else:
            x_emb = xz.reshape(1, -1)
        probs = self._gmm_model.predict_proba(x_emb)[0]
        return {int(i): float(p) for i, p in enumerate(probs)}

    # ---------- range prediction ----------
    def predict_range(self,
                      feat: Dict[str, float],
                      similar_outcomes: List[Dict[str, float]]) -> Dict[str, float]:
        """Combine three sources of range prediction:
            - fitted GBR on the full feature vector (when available)
            - cluster-conditional mean weighted by soft cluster prob
            - k-NN mean of the K most similar historical days
        Final is a 0.5 * GBR + 0.25 * cluster + 0.25 * k-NN blend.
        P10/P90 are taken from the k similar days (intuitive & honest).
        """
        if self.history is None:
            raise RuntimeError("Call .load() first")
        target = "range_pct_next_30m"

        # --- GBR (most accurate when it loads) ---
        pred_gbr = float(self.history[target].mean())
        if self._range_model is not None and hasattr(self, "_range_model_meta"):
            meta = self._range_model_meta
            cols = meta["feat_cols"]
            mean = np.asarray(meta["mean"]); std = np.asarray(meta["std"])
            x = np.array([feat.get(c, np.nan) for c in cols], dtype=float)
            xz = (x - mean) / np.where(std == 0, 1.0, std)
            xz = np.nan_to_num(xz, nan=0.0)
            try:
                pred_gbr = float(self._range_model.predict(xz.reshape(1, -1))[0])
            except Exception:
                pass

        # --- cluster-conditional mean ---
        pred_cluster = pred_gbr
        if self.gmm is not None and self._gmm_model is not None:
            cluster_probs = self.cluster_probability(feat)
            hist = self.history.merge(
                self.gmm[["date", "label_gmm"]], on="date", how="inner"
            )
            p_c = 0.0; w_c = 0.0
            for c, p in cluster_probs.items():
                vals = hist.loc[hist["label_gmm"] == c, target].dropna()
                if len(vals) and p > 0.01:
                    p_c += float(vals.mean()) * p; w_c += p
            if w_c > 0:
                pred_cluster = p_c / w_c

        # --- k-NN mean ---
        sim_ranges = [o[target] for o in similar_outcomes
                      if o.get(target) is not None and np.isfinite(o[target])]
        pred_knn = float(np.mean(sim_ranges)) if sim_ranges else pred_gbr

        # Blend
        pred = 0.50 * pred_gbr + 0.25 * pred_cluster + 0.25 * pred_knn
        if sim_ranges:
            p10, p90 = float(np.quantile(sim_ranges, 0.10)), float(np.quantile(sim_ranges, 0.90))
        else:
            p10, p90 = pred * 0.5, pred * 1.6
        return {
            "predicted_range_pct": pred,
            "predicted_range_p10": p10,
            "predicted_range_p90": p90,
        }

    # ---------- direction prediction ----------
    def predict_direction(self,
                          feat: Dict[str, float],
                          similar_outcomes: List[Dict[str, float]]) -> float:
        """Probability-weighted direction bias in [-1, 1]."""
        if self.gmm is None or self._gmm_model is None:
            sims = [o["dir_sign_next_30m"] for o in similar_outcomes
                    if np.isfinite(o.get("dir_sign_next_30m", float("nan")))]
            return float(np.mean(sims)) if sims else 0.0
        cluster_probs = self.cluster_probability(feat)
        hist = self.history.merge(
            self.gmm[["date", "label_gmm"]], on="date", how="inner"
        )
        bias = 0.0
        total_w = 0.0
        for c, p in cluster_probs.items():
            vals = hist.loc[hist["label_gmm"] == c, "dir_sign_next_30m"].dropna()
            if len(vals) and p > 0.01:
                bias += float(vals.mean()) * p
                total_w += p
        return bias / total_w if total_w > 0 else 0.0

    # ---------- top-level predict ----------
    def predict_for_today(self,
                          date: pd.Timestamp,
                          pre: pd.DataFrame,
                          ib: Optional[pd.DataFrame] = None,
                          pred_window: Optional[pd.DataFrame] = None,
                          eod_window: Optional[pd.DataFrame] = None,
                          k_similar: int = 5,
                          fan_n_paths: int = 50,
                          ) -> PredictResult:
        feat = self.features_for(date, pre, ib, pred_window, eod_window)
        similar = self.top_k_similar(feat, k=k_similar)
        cluster_probs = self.cluster_probability(feat)
        dominant = max(cluster_probs, key=cluster_probs.get) if cluster_probs else -1
        range_pred = self.predict_range(feat, [s[2] for s in similar])
        dir_pred = self.predict_direction(feat, [s[2] for s in similar])

        # ----- Path fan from the k similar days -----
        path_fan = self._build_path_fan(similar, fan_n_paths, pre, ib)

        notes = []
        if not self._gmm_model:
            notes.append("GMM model not loaded (gmm.joblib missing) - cluster probs are 0")
        if abs(dir_pred) < 0.10:
            notes.append("Direction prediction is near zero: pre-market/IB features do NOT "
                         "carry a direction edge for 10:00-10:30 (empirical finding).")
        else:
            notes.append(f"Direction bias = {dir_pred:+.3f}: weak signal, use with caution.")

        return PredictResult(
            date=date,
            n_similar_days=len(similar),
            similar_dates=[s[0] for s in similar],
            similar_distances=[s[1] for s in similar],
            similar_outcomes=[s[2] for s in similar],
            predicted_range_pct=range_pred["predicted_range_pct"],
            predicted_range_p10=range_pred["predicted_range_p10"],
            predicted_range_p90=range_pred["predicted_range_p90"],
            predicted_direction=dir_pred,
            cluster_assignments=cluster_probs,
            dominant_cluster=dominant,
            path_fan=path_fan,
            feature_snapshot=feat,
            notes=notes,
        )

    def _build_path_fan(self,
                        similar: List[Tuple[pd.Timestamp, float, Dict[str, float]]],
                        n_paths: int,
                        pre: pd.DataFrame,
                        ib: Optional[pd.DataFrame]) -> Dict[str, np.ndarray]:
        """Build a 'path fan' from the actual 10:00-10:30 windows of the
        k similar days.

        Returns a dict with:
            times_min      : 0..30  (minutes since 10:00)
            paths          : (n_paths, 31)  cumulative return in % from 10:00 open
            p10, p50, p90  : (31,)  quantile bands
        If bars is not loaded, returns an empty dict.
        """
        if self.bars is None or not similar:
            return {}
        # Anchor price = close at 10:00 ET today (last IB bar close)
        if ib is not None and not ib.empty:
            anchor = float(ib.iloc[-1]["close"])
        else:
            anchor = float(pre.iloc[-1]["close"]) if not pre.empty else 100.0
        times = np.arange(0, 31, dtype=float)
        all_paths = []
        for date, dist, _ in similar:
            day = bars_for_date(self.bars, date)
            if day.empty:
                continue
            window = slice_phase(day, 10 * 60, 10 * 60 + 30)
            if window.empty or len(window) < 30:
                continue
            ref = float(window.iloc[0]["open"])
            if ref == 0:
                continue
            cumret = (window["close"].to_numpy()[:31] - ref) / ref * 100.0
            # pad if shorter than 31
            if len(cumret) < 31:
                cumret = np.concatenate([cumret, np.full(31 - len(cumret), cumret[-1])])
            all_paths.append(cumret)
        if not all_paths:
            return {}
        paths = np.array(all_paths)
        # If we want more paths, resample with replacement
        if len(paths) < n_paths:
            idx = np.random.choice(len(paths), size=n_paths, replace=True)
            paths = paths[idx]
        elif len(paths) > n_paths:
            # pick the n_paths closest to the median range
            ranges = paths[:, -1].ptp() if False else np.abs(paths[:, -1])
            idx = np.argsort(ranges)[:n_paths]
            paths = paths[idx]
        return {
            "times_min": times,
            "paths": paths,
            "p10": np.quantile(paths, 0.10, axis=0),
            "p50": np.quantile(paths, 0.50, axis=0),
            "p90": np.quantile(paths, 0.90, axis=0),
        }
