"""Open-signal API: the one call the live bot makes at 10:00 ET.

Usage from ``live_trading_loop.py`` after the IB closes::

    from src.day_similarity.open_signal import compute_open_signal, OpenSignal
    sig: OpenSignal = compute_open_signal(
        pre_bars=...            # 1-min bars 00:00..09:30 ET for today
        ib_bars=...             # 1-min bars 09:30..10:00 ET for today
        current_price=...,      # float, last price observed
        account_equity=...,     # float, account size
        base_risk_pct=0.005,    # 0.5% per trade default
        min_contracts=1,
        max_contracts=20,
        symbol="MNQ",           # MNQ or NQ
    )
    # Then:
    if sig.skip_trade:
        return
    bot.send_bracket_order(
        direction=sig.direction,
        contracts=sig.suggested_contracts,
        entry=sig.entry_price,
        sl=sig.stop_price,
        tp=sig.target_price,
    )

The function is *pure* (no global state, no LLM, no IO) and returns a
typed ``OpenSignal`` dataclass that the bot can serialize to a log
line or a Telegram message.
"""
from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.day_similarity.config import TICK_SIZE
from src.day_similarity.data_loader import (
    bars_for_date, load_all_bars, slice_phase,
    MIN_IB_END, MIN_PRE_START, MIN_RTH_OPEN,
)
from src.day_similarity.predict import DaySimilarityPredictor
from src.day_similarity.integration import RegimeFilter, RegimeSnapshot


# ──────────────────────────────────────────────────────────────────────────
# Result dataclass
# ──────────────────────────────────────────────────────────────────────────
@dataclass
class OpenSignal:
    """The structured decision the live bot consumes at 10:00 ET.

    Direction / sizing / stop / target are all derived from the
    pre-market + IB regime combined with the historical-similar-days
    distribution.  All values are absolute NQ points (not ticks).
    """
    date: pd.Timestamp
    is_ready: bool
    skip_trade: bool
    skip_reason: str

    # regime
    dominant_cluster: int
    cluster_probs: dict
    is_volatile: bool
    is_quiet: bool

    # outcome forecast
    predicted_range_pct: float
    predicted_range_p10: float
    predicted_range_p90: float
    predicted_direction: float          # in [-1, 1], use with caution
    confidence: float                  # = |predicted_direction| (0..1)

    # sizing (based on predicted range)
    size_multiplier: float             # 0.5..1.5
    suggested_contracts: int

    # trade plan (only if !skip_trade)
    direction: str                     # 'long' | 'short' | 'none'
    entry_price: float
    stop_price: float
    target_price: float
    stop_distance_ticks: float
    target_distance_ticks: float
    r_ratio: float

    # similar days for explainability
    similar_dates: List[pd.Timestamp]
    similar_outcomes: List[dict]
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = asdict(self)
        # JSON-friendly conversions
        d["date"] = str(self.date.date())
        d["similar_dates"] = [str(d.date()) for d in self.similar_dates]
        return d

    def summary_line(self) -> str:
        """One-line status for live logs / Telegram."""
        if not self.is_ready:
            return f"[{self.date.date()}] ⚠ not ready: {self.skip_reason}"
        if self.skip_trade:
            return (f"[{self.date.date()}] SKIP — {self.skip_reason}  "
                    f"cluster={self.dominant_cluster}  "
                    f"range={self.predicted_range_pct:.2f}%")
        return (
            f"[{self.date.date()}] {self.direction.upper()}  "
            f"size={self.suggested_contracts}  "
            f"entry={self.entry_price:.2f}  "
            f"sl={self.stop_distance_ticks:.0f}t  "
            f"tp={self.target_distance_ticks:.0f}t  "
            f"R={self.r_ratio:.2f}  "
            f"range={self.predicted_range_pct:.2f}%  "
            f"conf={self.confidence:.2f}"
        )


# ──────────────────────────────────────────────────────────────────────────
# The one function
# ──────────────────────────────────────────────────────────────────────────
def compute_open_signal(
    pre_bars: pd.DataFrame,
    ib_bars: pd.DataFrame,
    current_price: float,
    account_equity: float,
    base_risk_pct: float = 0.005,
    min_contracts: int = 1,
    max_contracts: int = 20,
    symbol: str = "MNQ",
    min_range_pct: float = 0.20,
    max_range_pct: float = 2.50,
    min_confidence: float = 0.10,
    default_r_target: float = 1.5,
) -> OpenSignal:
    """Build an ``OpenSignal`` from the bars collected so far today.

    Parameters
    ----------
    pre_bars, ib_bars     1-min OHLC (and optionally volume) dataframes
                          for today's pre-market (00:00-09:30 ET) and
                          Initial Balance (09:30-10:00 ET).
    current_price         the last tick seen at decision time (~10:00 ET).
    account_equity        account size in USD, used for sizing.
    base_risk_pct         baseline per-trade risk as a fraction of equity.
    symbol                'MNQ' (default) or 'NQ' (tick values differ).
    min_range_pct         skip if predicted range is below this (too quiet).
    max_range_pct         skip if predicted range is above this (too wild).
    min_confidence        minimum |predicted_direction| to take a direction
                          trade.  Below this we *skip* the direction trade
                          (the range forecast is still useful for sizing
                          even if we skip the entry).
    """
    tick_value_usd = 0.50 if symbol.upper() == "MNQ" else 5.00

    # ---- Build the regime snapshot using the integration wrapper ----
    rf = RegimeFilter()  # uses default paths
    snap: RegimeSnapshot = rf._predictor_snapshot_from_bars(pre_bars, ib_bars)

    date = pd.Timestamp(pre_bars["date_et"].iloc[0]) if not pre_bars.empty \
        else pd.Timestamp.now(tz="America/New_York").normalize().tz_localize(None)
    notes = list(snap.notes) if hasattr(snap, "notes") else []

    if not snap.is_ready:
        return OpenSignal(
            date=date, is_ready=False, skip_trade=True,
            skip_reason="; ".join(snap.notes) or "snapshot not ready",
            dominant_cluster=getattr(snap, "dominant_cluster", -1),
            cluster_probs=dict(getattr(snap, "cluster_probs", {})),
            is_volatile=getattr(snap, "is_volatile", False),
            is_quiet=getattr(snap, "is_quiet", False),
            predicted_range_pct=float("nan"),
            predicted_range_p10=float("nan"),
            predicted_range_p90=float("nan"),
            predicted_direction=float("nan"),
            confidence=0.0,
            size_multiplier=1.0, suggested_contracts=0,
            direction="none", entry_price=current_price,
            stop_price=current_price, target_price=current_price,
            stop_distance_ticks=0.0, target_distance_ticks=0.0,
            r_ratio=0.0, similar_dates=[], similar_outcomes=[],
            notes=notes,
        )

    # ---- Decision logic ----
    pred_range = snap.predicted_range_pct
    pred_dir = snap.predicted_direction if np.isfinite(snap.predicted_direction) else 0.0
    confidence = abs(pred_dir)

    skip = False
    skip_reason = ""

    # Guard 1: range bounds (extremes are bad for trend trades)
    if not np.isfinite(pred_range):
        skip = True
        skip_reason = "predicted range is NaN"
    elif pred_range < min_range_pct:
        skip = True
        skip_reason = f"predicted range {pred_range:.2f}% < {min_range_pct:.2f}% (too quiet)"
    elif pred_range > max_range_pct:
        skip = True
        skip_reason = f"predicted range {pred_range:.2f}% > {max_range_pct:.2f}% (too volatile)"

    # Guard 2: direction confidence threshold.
    # We do NOT take a direction trade if confidence is below threshold.
    # The system explicitly does not predict direction.
    if not skip and confidence < min_confidence:
        skip = True
        skip_reason = (f"direction confidence {confidence:.2f} < "
                       f"{min_confidence:.2f} (range still useful for sizing)")

    # ---- Sizing ----
    # Inverse sizing: bigger predicted range -> smaller position.
    # Anchor: median historical range (0.55% from the data).
    median_range = 0.55
    if np.isfinite(pred_range) and pred_range > 0:
        size_mult = float(np.clip(median_range / max(pred_range, 0.05), 0.5, 1.5))
    else:
        size_mult = 1.0

    risk_usd = account_equity * base_risk_pct
    suggested_contracts = 0
    stop_distance_pts = 0.0
    target_distance_pts = 0.0
    r_ratio = 0.0
    direction = "none"
    entry = float(current_price)
    stop = entry
    target = entry

    if not skip:
        # Use a stop at the lower P10 of the predicted range (in %).
        # This is empirically calibrated: on similar days, 10% of the time
        # the range was smaller than this P10.
        stop_pct = max(snap.predicted_range_p10 * 0.6, 0.08)  # at least 0.08%
        target_pct = max(snap.predicted_range_p90 * 0.7, stop_pct * default_r_target)

        stop_distance_pts = entry * stop_pct / 100.0
        target_distance_pts = entry * target_pct / 100.0
        if stop_distance_pts > 0:
            stop_distance_ticks = stop_distance_pts / TICK_SIZE
            target_distance_ticks = target_distance_pts / TICK_SIZE
            risk_per_contract_usd = stop_distance_ticks * tick_value_usd
            if risk_per_contract_usd > 0:
                base_contracts = int(risk_usd / risk_per_contract_usd)
            else:
                base_contracts = max_contracts
            suggested_contracts = int(
                np.clip(base_contracts * size_mult, min_contracts, max_contracts)
            )
            r_ratio = float(target_distance_pts / stop_distance_pts)

        # Direction: ONLY take a trade if confidence is high enough.
        # Otherwise we just skip (the range is used for sizing, not for
        # direction).
        if confidence >= min_confidence:
            if pred_dir > 0:
                direction = "long"
                stop = entry - stop_distance_pts
                target = entry + target_distance_pts
            elif pred_dir < 0:
                direction = "short"
                stop = entry + stop_distance_pts
                target = entry - target_distance_pts
            else:
                direction = "none"
                skip = True
                skip_reason = "direction bias is exactly zero"

    return OpenSignal(
        date=date,
        is_ready=True,
        skip_trade=skip,
        skip_reason=skip_reason,
        dominant_cluster=snap.dominant_cluster,
        cluster_probs=dict(snap.cluster_probs),
        is_volatile=snap.is_volatile,
        is_quiet=snap.is_quiet,
        predicted_range_pct=float(pred_range),
        predicted_range_p10=float(snap.predicted_range_p10),
        predicted_range_p90=float(snap.predicted_range_p90),
        predicted_direction=float(pred_dir),
        confidence=float(confidence),
        size_multiplier=float(size_mult),
        suggested_contracts=int(suggested_contracts),
        direction=direction,
        entry_price=float(entry),
        stop_price=float(stop),
        target_price=float(target),
        stop_distance_ticks=float(stop_distance_pts / TICK_SIZE),
        target_distance_ticks=float(target_distance_pts / TICK_SIZE),
        r_ratio=float(r_ratio),
        similar_dates=list(snap.similar_dates),
        similar_outcomes=list(snap.similar_outcomes),
        notes=notes + [
            f"size_mult={size_mult:.2f} (median_range={median_range}% / pred={pred_range:.2f}%)",
        ],
    )


# ──────────────────────────────────────────────────────────────────────────
# Integration glue: snapshot from raw bars (no need to reload from cache)
# ──────────────────────────────────────────────────────────────────────────
def _patch_integration_with_bars():
    """Add a method to RegimeFilter that builds a snapshot from raw bars
    (no reload from cache) — used by ``compute_open_signal``."""
    def snapshot_from_bars(self, pre_bars: pd.DataFrame, ib_bars: pd.DataFrame) -> RegimeSnapshot:
        self._ensure_loaded()
        if pre_bars.empty or ib_bars.empty:
            return RegimeSnapshot(date=pd.Timestamp.now(tz="America/New_York").normalize().tz_localize(None),
                                  notes=["empty bars passed to snapshot_from_bars"])
        date = pd.Timestamp(pre_bars["date_et"].iloc[0])
        # Run the predictor
        result = self._predictor.predict_for_today(
            date, pre_bars, ib=ib_bars, k_similar=5, fan_n_paths=0
        )
        snap = RegimeSnapshot(date=date)
        snap.is_ready = True
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
        med = self._history_median_range
        if med and np.isfinite(snap.predicted_range_pct):
            snap.is_volatile = snap.predicted_range_pct > 1.3 * med
            snap.is_quiet = snap.predicted_range_pct < 0.7 * med
        return snap

    RegimeFilter._predictor_snapshot_from_bars = snapshot_from_bars


_patch_integration_with_bars()
