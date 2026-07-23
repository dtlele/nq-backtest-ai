"""Integration glue between the day-similarity engine and the rest of
nq-backtest-clean.

This module wraps :class:`DaySimilarityPredictor` behind a tiny, *production*
API that the live bot, the risk manager, the consensus engine, and the
candidate detector can all call without learning the engine's internals.

Typical use (e.g. from ``live_trading_loop.py`` after the IB is complete):

    from src.day_similarity.integration import RegimeFilter
    rf = RegimeFilter("data/similarity")
    rf.refresh_if_needed(bars_1min_today)        # pulls fresh M1 from MT5
    snap = rf.snapshot()
    if snap.is_volatile:
        # shrink position size, etc.
        position_size = base_size * (target_vol / snap.predicted_range_pct)

The class is **stateless across calls** — you can construct it once at
startup and call ``snapshot()`` whenever the IB completes.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.day_similarity.data_loader import (
    bars_for_date, load_all_bars, slice_phase,
    MIN_IB_END, MIN_PRE_START, MIN_RTH_OPEN,
)
from src.day_similarity.predict import DaySimilarityPredictor


# ──────────────────────────────────────────────────────────────────────────
# Snapshot — the small object everything else consumes
# ──────────────────────────────────────────────────────────────────────────
@dataclass
class RegimeSnapshot:
    """Compact view of where 'today' sits in the regime map.

    Attributes
    ----------
    date              trading date
    is_ready          True if the IB is complete and the snapshot is valid
    dominant_cluster  GMM cluster with the highest probability (-1 if unknown)
    cluster_probs     dict cluster_id -> probability
    predicted_range_pct    expected 10:00→10:30 RANGE in %
    predicted_range_p10    lower band (P10 of similar days)
    predicted_range_p90    upper band (P90 of similar days)
    predicted_direction    bias in [-1, 1]  (use with caution)
    is_volatile       True if predicted range > 1.3 * history median
    is_quiet          True if predicted range < 0.7 * history median
    similar_dates     list of top-K similar historical dates
    similar_distances distances in feature space
    similar_outcomes  list of outcome dicts for similar days
    notes             list of human-readable notes
    """
    date: pd.Timestamp
    is_ready: bool = False
    dominant_cluster: int = -1
    cluster_probs: dict = field(default_factory=dict)
    predicted_range_pct: float = float("nan")
    predicted_range_p10: float = float("nan")
    predicted_range_p90: float = float("nan")
    predicted_direction: float = float("nan")
    is_volatile: bool = False
    is_quiet: bool = False
    similar_dates: List[pd.Timestamp] = field(default_factory=list)
    similar_distances: List[float] = field(default_factory=list)
    similar_outcomes: List[dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def confidence_in_direction(self) -> float:
        """Return |predicted_direction| in [0, 1] — a coarse 'edge' strength."""
        if not np.isfinite(self.predicted_direction):
            return 0.0
        return float(abs(self.predicted_direction))

    def as_dict(self) -> dict:
        return {
            "date": self.date,
            "is_ready": self.is_ready,
            "dominant_cluster": self.dominant_cluster,
            "predicted_range_pct": self.predicted_range_pct,
            "predicted_range_p10": self.predicted_range_p10,
            "predicted_range_p90": self.predicted_range_p90,
            "predicted_direction": self.predicted_direction,
            "is_volatile": self.is_volatile,
            "is_quiet": self.is_quiet,
        }


# ──────────────────────────────────────────────────────────────────────────
# Main wrapper
# ──────────────────────────────────────────────────────────────────────────
class RegimeFilter:
    """Lightweight wrapper around DaySimilarityPredictor for the live system."""

    def __init__(self, artefact_dir: str = "data/similarity",
                 cache_dir: str = "cache_ohlc",
                 k_similar: int = 7,
                 fan_n_paths: int = 20) -> None:
        self.artefact_dir = Path(artefact_dir)
        self.cache_dir = cache_dir
        self.k_similar = k_similar
        self.fan_n_paths = fan_n_paths
        self._predictor: Optional[DaySimilarityPredictor] = None
        self._bars: Optional[pd.DataFrame] = None
        self._history_median_range: Optional[float] = None
        self._last_refresh: Optional[pd.Timestamp] = None

    # ---------- loading ----------
    def _ensure_loaded(self) -> None:
        if self._predictor is not None:
            return
        self._predictor = DaySimilarityPredictor()
        self._predictor.load(str(self.artefact_dir))
        try:
            self._bars = load_all_bars(self.cache_dir)
        except FileNotFoundError:
            self._bars = None
        # Cache the median range for volatility buckets
        try:
            hist = pd.read_parquet(self.artefact_dir / "day_features.parquet")
            self._history_median_range = float(hist["range_pct_next_30m"].median())
        except Exception:
            self._history_median_range = None

    def refresh_if_needed(self, bars_1min_today: Optional[pd.DataFrame] = None,
                          force: bool = False) -> None:
        """Re-load bars and (optionally) ingest fresh M1 bars for today.

        ``bars_1min_today`` is a DataFrame with the same columns as
        ``load_all_bars`` output (ts, date_et, minute_et, ohlc, ...).  It is
        used to update the pre-market and IB slices for the current session.
        """
        self._ensure_loaded()
        if bars_1min_today is not None and not bars_1min_today.empty:
            if self._bars is None:
                self._bars = bars_1min_today.copy()
            else:
                # Remove today's previous rows and append the fresh ones
                today = bars_1min_today["date_et"].iloc[0]
                self._bars = self._bars[self._bars["date_et"] != today]
                self._bars = pd.concat([self._bars, bars_1min_today], ignore_index=True)
                self._bars = self._bars.sort_values("ts").reset_index(drop=True)
            self._last_refresh = pd.Timestamp.utcnow()
        elif force:
            self._bars = load_all_bars(self.cache_dir)
            self._last_refresh = pd.Timestamp.utcnow()

    # ---------- snapshot ----------
    def snapshot(self, today: Optional[pd.Timestamp] = None) -> RegimeSnapshot:
        self._ensure_loaded()
        if today is None:
            today = pd.Timestamp.now(tz="America/New_York").normalize().tz_localize(None)
        snap = RegimeSnapshot(date=today)
        if self._bars is None:
            snap.notes.append("bars not loaded - call refresh_if_needed() first")
            return snap

        day = bars_for_date(self._bars, today)
        if day.empty:
            snap.notes.append(f"no bars for {today.date()} yet")
            return snap

        pre = slice_phase(day, MIN_PRE_START, MIN_RTH_OPEN)
        ib  = slice_phase(day, MIN_RTH_OPEN, MIN_IB_END)
        if pre.empty or ib.empty:
            snap.notes.append(
                f"insufficient bars: pre={len(pre)} ib={len(ib)} "
                f"(need pre>=570 ib=30)"
            )
            return snap

        snap.is_ready = True
        result = self._predictor.predict_for_today(
            today, pre, ib=ib,
            k_similar=self.k_similar, fan_n_paths=self.fan_n_paths,
        )
        snap.dominant_cluster = result.dominant_cluster
        snap.cluster_probs = dict(result.cluster_assignments)
        snap.predicted_range_pct = result.predicted_range_pct
        snap.predicted_range_p10 = result.predicted_range_p10
        snap.predicted_range_p90 = result.predicted_range_p90
        snap.predicted_direction = result.predicted_direction
        snap.similar_dates = list(result.similar_dates)
        snap.similar_distances = list(result.similar_distances)
        snap.similar_outcomes = list(result.similar_outcomes)
        snap.notes = list(result.notes)

        # Volatility buckets (vs history median range)
        med = self._history_median_range
        if med and np.isfinite(snap.predicted_range_pct):
            snap.is_volatile = snap.predicted_range_pct > 1.3 * med
            snap.is_quiet   = snap.predicted_range_pct < 0.7 * med

        return snap

    # ---------- helpers used by the rest of the system ----------
    def size_multiplier(self, snap: RegimeSnapshot, base: float = 1.0) -> float:
        """Translate a predicted range into a position-size multiplier.

        Default policy: target a *constant* risk budget by scaling
        inversely with predicted range.

        - quiet regime  -> up to 1.4x  (small range, can size up)
        - normal regime -> 1.0x
        - volatile      -> down to 0.6x
        """
        if not snap.is_ready or not np.isfinite(snap.predicted_range_pct):
            return base
        med = self._history_median_range or 0.55
        ratio = med / max(snap.predicted_range_pct, 0.05)
        return float(np.clip(ratio, 0.5, 1.5))

    def cluster_outcome_summary(self, snap: RegimeSnapshot) -> dict:
        """Return a small dict with the mean/median outcomes of the days
        in the dominant cluster.  Useful for the consensus engine to give
        an evidence-based vote."""
        if not snap.is_ready or self._predictor is None:
            return {}
        target_cols = [
            "ret_pct_next_30m", "range_pct_next_30m",
            "mfe_pct_next_30m", "mae_pct_next_30m",
            "ret_pct_eod", "dir_sign_next_30m",
        ]
        gmm = self._predictor.gmm
        hist = self._predictor.history
        if gmm is None:
            return {}
        merged = hist.merge(gmm[["date", "label_gmm"]], on="date", how="inner")
        sub = merged.loc[merged["label_gmm"] == snap.dominant_cluster]
        if sub.empty:
            return {}
        return {
            "n_days": int(len(sub)),
            "cluster_id": int(snap.dominant_cluster),
            **{c: float(sub[c].mean()) for c in target_cols if c in sub.columns},
        }
