"""Day-similarity feature engineering.

Output schema (per day, in pandas-friendly dict):

  Pre-market (00:00 - 9:30 ET)
    pm_gap_pct               : (00:00 open vs prior RTH close)  in %
    pm_close_gap_pct         : (9:29 close vs prior RTH close)  in %
    pm_high_above_close_pct  : (pm_high - pm_close) / pm_close
    pm_low_below_close_pct   : (pm_close - pm_low) / pm_close
    pm_range_pct             : (pm_high - pm_low) / pm_close
    pm_drift_pct             : (pm_close - pm_open) / pm_open
    pm_path_efficiency       : |close-open|/(high-low)   in [0,1]
    pm_position_in_prior_day : (pm_close - prior_lo)/(prior_hi-prior_lo)
    pm_mean_abs_ret_pct      : mean |1m return|  (vol proxy)
    pm_total_range_ticks     : sum of 1m bar ranges in ticks
    pm_n_up_bars, pm_n_down_bars
    pm_directional_consistency: fraction of 30-min chunks with same sign
    pm_vp_width_pct          : (pm_vah - pm_val)/pm_close
    pm_poc_close_pct         : (pm_poc - pm_close)/pm_close
    pm_poc_in_va_pct         : (pm_poc - pm_val)/(pm_vah - pm_val)
    pm_close_in_va_pct       : (pm_close - pm_val)/(pm_vah - pm_val)
    pm_skew                  : signed POC distance from VA midpoint  in [-1,1]
    pm_hvn_count, pm_lvn_count
    pm_hvn_density           : HVN count per 1 % of price range
    pm_lvn_max_gap_pct       : biggest gap between consecutive LVNs as % of range
    pm_dist_to_nearest_hvn_pct
    pm_dist_to_nearest_lvn_pct
    pm_dist_to_pm_high_pct   : (pm_high - pm_close)/pm_close
    pm_dist_to_pm_low_pct    : (pm_close - pm_low)/pm_close

  Initial Balance (9:30 - 10:00 ET)
    ib_range_pct             : (ib_high - ib_low)/ib_open
    ib_close_position        : (ib_close - ib_low)/(ib_high - ib_low)
    ib_drift_pct             : (ib_close - ib_open)/ib_open
    ib_vs_pm_range_pct       : ib_range / pm_range
    ib_vs_prior_day_range_pct
    ib_vs_adr_pct            : ib_range / 20-day median daily range
    ib_high_vs_pm_vah_pct    : (ib_high - pm_vah)/ib_open
    ib_low_vs_pm_val_pct     : (pm_val - ib_low)/ib_open
    ib_close_vs_pm_poc_pct   : (ib_close - pm_poc)/ib_open
    ib_close_vs_pm_vah_pct
    ib_close_vs_pm_val_pct
    ib_close_vs_pm_close_pct
    ib_vp_width_pct
    ib_poc_close_pct
    ib_poc_in_va_pct
    ib_close_in_va_pct
    ib_skew
    ib_hvn_count, ib_lvn_count
    ib_dist_to_nearest_hvn_pct
    ib_dist_to_nearest_lvn_pct
    ib_total_range_ticks

  Calendar / context
    dow                      : 0=Mon..4=Fri
    week_of_month
    is_opex_week             : 1 if 3rd Friday falls in this Mon-Fri
    is_month_end             : 1 if in the last 3 sessions of month
    is_turn_of_month         : 1 if within 2 sessions of month start

  Volatility / regime (rolling z-scores, 60-day window)
    z_pm_range_pct
    z_ib_range_pct
    z_gap_pct
    z_pm_drift_pct

  Outcomes  (labels, computed at the end)
    ret_pct_next_30m, mfe_pct_next_30m, mae_pct_next_30m,
    range_pct_next_30m, dir_sign_next_30m
    ret_pct_eod,     mfe_pct_eod,     mae_pct_eod,
    range_pct_eod,   dir_sign_eod

ALL values are dimensionless (% or ratios).  No hardcoded price levels.
"""
from __future__ import annotations

import calendar
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from src.day_similarity.config import (
    IB_PREFIX, OUTCOME_DIR_COL, OUTCOME_MAE_COL, OUTCOME_MFE_COL,
    OUTCOME_RANGE_COL, OUTCOME_RET_COL, PM_PREFIX, ROLLING_WINDOW_SESSIONS,
)
from src.day_similarity.data_loader import (
    MIN_IB_END, MIN_PRED_END, MIN_PRE_START, MIN_RTH_END, MIN_RTH_OPEN,
    bars_for_date, slice_phase,
)
from src.day_similarity.tpo import TPOProfile, build_tpo, level_to_pct


# ──────────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────────
def _safe_pct(num: float, den: float) -> float:
    if not np.isfinite(num) or not np.isfinite(den) or den == 0:
        return float("nan")
    return num / den * 100.0


def _safe_ratio(num: float, den: float) -> float:
    if not np.isfinite(num) or not np.isfinite(den) or den == 0:
        return float("nan")
    return num / den


def _n_bars_up_down(returns: Sequence[float]) -> tuple:
    if returns is None or len(returns) == 0:
        return (0, 0)
    a = np.asarray(returns, dtype=float)
    a = a[np.isfinite(a) & (a != 0)]
    return int((a > 0).sum()), int((a < 0).sum())


def _directional_consistency(returns: Sequence[float], chunk: int = 30) -> float:
    returns = list(returns) if returns is not None else []
    if len(returns) < chunk:
        return float("nan")
    a = np.asarray(returns[: chunk * (len(returns) // chunk)], dtype=float)
    if a.size == 0:
        return float("nan")
    a = a.reshape(-1, chunk)
    sums = a.sum(axis=1)
    pos = (sums > 0).sum()
    neg = (sums < 0).sum()
    if pos + neg == 0:
        return float("nan")
    return max(pos, neg) / (pos + neg)


def _profile_features(profile: TPOProfile, ref: float, prefix: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    if not np.isfinite(profile.poc) or not np.isfinite(profile.vah) or not np.isfinite(profile.val):
        for k in (
            "vp_width_pct", "poc_close_pct", "poc_in_va_pct", "close_in_va_pct",
            "skew", "hvn_density", "lvn_max_gap_pct",
            "dist_to_nearest_hvn_pct", "dist_to_nearest_lvn_pct",
        ):
            out[f"{prefix}{k}"] = float("nan")
        out[f"{prefix}hvn_count"] = 0
        out[f"{prefix}lvn_count"] = 0
        return out
    width = profile.vah - profile.val
    out[f"{prefix}vp_width_pct"] = _safe_pct(width, ref)
    out[f"{prefix}poc_close_pct"] = level_to_pct(profile.poc, ref)
    if width > 0:
        out[f"{prefix}poc_in_va_pct"] = (profile.poc - profile.val) / width
        out[f"{prefix}close_in_va_pct"] = (ref - profile.val) / width
        mid = (profile.vah + profile.val) / 2.0
        out[f"{prefix}skew"] = (profile.poc - mid) / (width / 2.0)  # [-1, 1]
    else:
        out[f"{prefix}poc_in_va_pct"] = float("nan")
        out[f"{prefix}close_in_va_pct"] = float("nan")
        out[f"{prefix}skew"] = float("nan")
    hvn = profile.hvn_levels
    lvn = profile.lvn_levels
    out[f"{prefix}hvn_count"] = len(hvn)
    out[f"{prefix}lvn_count"] = len(lvn)
    if width > 0 and hvn:
        out[f"{prefix}hvn_density"] = len(hvn) / (_safe_pct(width, ref) or float("nan"))
        # If width% is NaN, leave NaN
        if not np.isfinite(out[f"{prefix}hvn_density"]):
            out[f"{prefix}hvn_density"] = float("nan")
    else:
        out[f"{prefix}hvn_density"] = float("nan")
    if len(lvn) >= 2 and width > 0:
        gaps = np.diff(sorted(lvn))
        out[f"{prefix}lvn_max_gap_pct"] = _safe_pct(float(np.max(np.abs(gaps))), ref)
    else:
        out[f"{prefix}lvn_max_gap_pct"] = float("nan")
    if hvn:
        nearest_hvn = min(hvn, key=lambda x: abs(x - ref))
        out[f"{prefix}dist_to_nearest_hvn_pct"] = level_to_pct(nearest_hvn, ref)
    else:
        out[f"{prefix}dist_to_nearest_hvn_pct"] = float("nan")
    if lvn:
        nearest_lvn = min(lvn, key=lambda x: abs(x - ref))
        out[f"{prefix}dist_to_nearest_lvn_pct"] = level_to_pct(nearest_lvn, ref)
    else:
        out[f"{prefix}dist_to_nearest_lvn_pct"] = float("nan")
    return out


def _calendar_flags(date: pd.Timestamp) -> Dict[str, float]:
    out: Dict[str, float] = {}
    out["dow"] = float(date.weekday())            # 0=Mon
    out["week_of_month"] = float((date.day - 1) // 7 + 1)
    # OPEX = 3rd Friday of the month (CBOE equity, but also a marker for futures)
    c = calendar.Calendar()
    month_cal = c.monthdayscalendar(date.year, date.month)
    fridays = [week[calendar.FRIDAY] for week in month_cal if week[calendar.FRIDAY] != 0]
    opex_day = fridays[2] if len(fridays) >= 3 else None
    if opex_day is not None:
        week_of_opex = (opex_day - 1) // 7 + 1
        out["is_opex_week"] = float(out["week_of_month"] == week_of_opex)
    else:
        out["is_opex_week"] = 0.0
    # Last 3 sessions of month ≈ last 5 calendar days
    last_day = calendar.monthrange(date.year, date.month)[1]
    out["is_month_end"] = float(date.day >= last_day - 4)
    # Turn of month: within 2 calendar days of the 1st
    out["is_turn_of_month"] = float(date.day <= 3)
    return out


# ──────────────────────────────────────────────────────────────────────────
# main
# ──────────────────────────────────────────────────────────────────────────
@dataclass
class DayContext:
    date: pd.Timestamp
    pre: pd.DataFrame
    ib: pd.DataFrame
    pred_window: pd.DataFrame   # 10:00 - 10:30 (the horizon we predict)
    eod_window: pd.DataFrame    # 10:00 - 16:00
    prior_rth_close: float
    prior_day_high: float
    prior_day_low: float
    prior_day_range: float     # (high - low) in points
    adr20: float                # 20-day median daily range in points


def build_day_context(date: pd.Timestamp,
                      all_bars: pd.DataFrame,
                      prior_bars: Optional[pd.DataFrame],
                      history_closes: Optional[pd.Series] = None,
                      history_ranges: Optional[pd.Series] = None) -> Optional[DayContext]:
    """Slice the bars for one day and its preconditions."""
    day = bars_for_date(all_bars, date)
    if day.empty:
        return None

    pre = slice_phase(day, MIN_PRE_START, MIN_RTH_OPEN)
    ib  = slice_phase(day, MIN_RTH_OPEN,   MIN_IB_END)
    p30 = slice_phase(day, MIN_IB_END,     MIN_PRED_END)
    eod = slice_phase(day, MIN_IB_END,     MIN_RTH_END)
    if pre.empty or ib.empty or p30.empty or eod.empty:
        return None

    if prior_bars is None or prior_bars.empty:
        prior_rth_close = float("nan")
        prior_day_high = float("nan")
        prior_day_low = float("nan")
        prior_day_range = float("nan")
    else:
        prior_rth = slice_phase(prior_bars, MIN_RTH_OPEN, MIN_RTH_END)
        if prior_rth.empty:
            return None
        prior_rth_close = float(prior_rth.iloc[-1]["close"])
        prior_day_high = float(prior_rth["high"].max())
        prior_day_low = float(prior_rth["low"].min())
        prior_day_range = prior_day_high - prior_day_low

    adr20 = float(np.nanmedian(history_ranges.iloc[-20:].to_numpy())) \
        if history_ranges is not None and len(history_ranges) else float("nan")

    return DayContext(
        date=date, pre=pre, ib=ib, pred_window=p30, eod_window=eod,
        prior_rth_close=prior_rth_close,
        prior_day_high=prior_day_high, prior_day_low=prior_day_low,
        prior_day_range=prior_day_range, adr20=adr20,
    )


def compute_features_for_day(ctx: DayContext) -> Dict[str, float]:
    pre, ib, p30, eod = ctx.pre, ctx.ib, ctx.pred_window, ctx.eod_window
    out: Dict[str, float] = {"date": ctx.date.normalize()}

    # Reference prices used for normalizations
    pm_open  = float(pre.iloc[0]["open"])
    pm_close = float(pre.iloc[-1]["close"])
    pm_high  = float(pre["high"].max())
    pm_low   = float(pre["low"].min())
    ib_open  = float(ib.iloc[0]["open"])
    ib_close = float(ib.iloc[-1]["close"])
    ib_high  = float(ib["high"].max())
    ib_low   = float(ib["low"].min())
    prior_rth_close = ctx.prior_rth_close

    # ---- pre-market price structure ----
    if np.isfinite(prior_rth_close) and prior_rth_close != 0:
        out["pm_gap_pct"] = _safe_pct(pm_open - prior_rth_close, prior_rth_close)
        out["pm_close_gap_pct"] = _safe_pct(pm_close - prior_rth_close, prior_rth_close)
    else:
        out["pm_gap_pct"] = float("nan")
        out["pm_close_gap_pct"] = float("nan")
    out["pm_high_above_close_pct"] = _safe_pct(pm_high - pm_close, pm_close)
    out["pm_low_below_close_pct"]  = _safe_pct(pm_close - pm_low, pm_close)
    out["pm_range_pct"]            = _safe_pct(pm_high - pm_low, pm_close)
    out["pm_drift_pct"]            = _safe_pct(pm_close - pm_open, pm_open)
    pm_range_pts = pm_high - pm_low
    out["pm_path_efficiency"] = (
        abs(pm_close - pm_open) / pm_range_pts if pm_range_pts > 0 else float("nan")
    )
    if np.isfinite(ctx.prior_day_range) and ctx.prior_day_range > 0 \
            and np.isfinite(ctx.prior_day_low) and np.isfinite(prior_rth_close):
        out["pm_position_in_prior_day"] = (pm_close - ctx.prior_day_low) / ctx.prior_day_range
    else:
        out["pm_position_in_prior_day"] = float("nan")

    # ---- pre-market micro (no volume, but we have bar-level stats) ----
    rets = pre["ret_1m_pct"].to_numpy()
    out["pm_mean_abs_ret_pct"] = float(np.nanmean(np.abs(rets))) if rets.size else float("nan")
    out["pm_total_range_ticks"] = float(pre["bar_range_ticks"].sum())
    n_up, n_dn = _n_bars_up_down(rets)
    out["pm_n_up_bars"] = float(n_up)
    out["pm_n_down_bars"] = float(n_dn)
    out["pm_directional_consistency"] = _directional_consistency(rets.tolist(), chunk=30)

    # ---- pre-market TPO profile ----
    pm_profile = build_tpo([type("B", (), {"low": r.low, "high": r.high}) for r in pre.itertuples()])
    out.update(_profile_features(pm_profile, pm_close, PM_PREFIX))

    # ---- initial balance ----
    ib_range_pts = ib_high - ib_low
    out["ib_range_pct"] = _safe_pct(ib_range_pts, ib_open)
    out["ib_close_position"] = (
        (ib_close - ib_low) / ib_range_pts if ib_range_pts > 0 else float("nan")
    )
    out["ib_drift_pct"] = _safe_pct(ib_close - ib_open, ib_open)
    out["ib_vs_pm_range_pct"] = (
        ib_range_pts / pm_range_pts if pm_range_pts > 0 else float("nan")
    )
    if np.isfinite(ctx.prior_day_range) and ctx.prior_day_range > 0:
        out["ib_vs_prior_day_range_pct"] = ib_range_pts / ctx.prior_day_range
    else:
        out["ib_vs_prior_day_range_pct"] = float("nan")
    if np.isfinite(ctx.adr20) and ctx.adr20 > 0:
        out["ib_vs_adr_pct"] = ib_range_pts / ctx.adr20
    else:
        out["ib_vs_adr_pct"] = float("nan")

    # IB vs PM levels
    if np.isfinite(pm_profile.vah):
        out["ib_high_vs_pm_vah_pct"] = _safe_pct(ib_high - pm_profile.vah, ib_open)
    else:
        out["ib_high_vs_pm_vah_pct"] = float("nan")
    if np.isfinite(pm_profile.val):
        out["ib_low_vs_pm_val_pct"] = _safe_pct(pm_profile.val - ib_low, ib_open)
    else:
        out["ib_low_vs_pm_val_pct"] = float("nan")
    if np.isfinite(pm_profile.poc):
        out["ib_close_vs_pm_poc_pct"] = _safe_pct(ib_close - pm_profile.poc, ib_open)
    else:
        out["ib_close_vs_pm_poc_pct"] = float("nan")
    out["ib_close_vs_pm_vah_pct"]  = _safe_pct(ib_close - pm_profile.vah, ib_open) \
        if np.isfinite(pm_profile.vah) else float("nan")
    out["ib_close_vs_pm_val_pct"]  = _safe_pct(ib_close - pm_profile.val, ib_open) \
        if np.isfinite(pm_profile.val) else float("nan")
    out["ib_close_vs_pm_close_pct"] = _safe_pct(ib_close - pm_close, pm_close)
    out["ib_total_range_ticks"] = float(ib["bar_range_ticks"].sum())

    # ---- IB TPO profile ----
    ib_profile = build_tpo([type("B", (), {"low": r.low, "high": r.high}) for r in ib.itertuples()])
    out.update(_profile_features(ib_profile, ib_close, IB_PREFIX))

    # ---- calendar ----
    out.update(_calendar_flags(ctx.date))

    # ---- outcome labels ----
    ref_30 = float(p30.iloc[0]["open"])   # ~ 10:00 ET open
    hi_30  = float(p30["high"].max())
    lo_30  = float(p30["low"].min())
    cl_30  = float(p30.iloc[-1]["close"])
    out[f"{OUTCOME_RET_COL}_next_30m"]   = _safe_pct(cl_30 - ref_30, ref_30)
    out[f"{OUTCOME_MFE_COL}_next_30m"]   = _safe_pct(hi_30 - ref_30, ref_30)
    out[f"{OUTCOME_MAE_COL}_next_30m"]   = _safe_pct(ref_30 - lo_30, ref_30)
    out[f"{OUTCOME_RANGE_COL}_next_30m"] = _safe_pct(hi_30 - lo_30, ref_30)
    out[f"{OUTCOME_DIR_COL}_next_30m"]   = float(np.sign(out[f"{OUTCOME_RET_COL}_next_30m"])
                                                 if np.isfinite(out[f"{OUTCOME_RET_COL}_next_30m"])
                                                 else float("nan"))

    ref_eod = float(eod.iloc[0]["open"])
    hi_eod  = float(eod["high"].max())
    lo_eod  = float(eod["low"].min())
    cl_eod  = float(eod.iloc[-1]["close"])
    out[f"{OUTCOME_RET_COL}_eod"]   = _safe_pct(cl_eod - ref_eod, ref_eod)
    out[f"{OUTCOME_MFE_COL}_eod"]   = _safe_pct(hi_eod - ref_eod, ref_eod)
    out[f"{OUTCOME_MAE_COL}_eod"]   = _safe_pct(ref_eod - lo_eod, ref_eod)
    out[f"{OUTCOME_RANGE_COL}_eod"] = _safe_pct(hi_eod - lo_eod, ref_eod)
    out[f"{OUTCOME_DIR_COL}_eod"]   = float(np.sign(out[f"{OUTCOME_RET_COL}_eod"])
                                            if np.isfinite(out[f"{OUTCOME_RET_COL}_eod"])
                                            else float("nan"))
    return out


def build_history_stats(daily_summaries: pd.DataFrame,
                        cols: Sequence[str],
                        window: int = ROLLING_WINDOW_SESSIONS) -> pd.DataFrame:
    """Append rolling z-scores for the given feature columns to the frame.

    The function *adds* new columns to a copy and returns it.  For each
    column ``c`` it appends ``z_{c}`` = (c - rolling_mean(c)) / rolling_std(c)
    using only the previous ``window`` sessions (not including today).
    """
    out = daily_summaries.copy()
    for c in cols:
        mean = daily_summaries[c].shift(1).rolling(window=window, min_periods=20).mean()
        std  = daily_summaries[c].shift(1).rolling(window=window, min_periods=20).std()
        out[f"z_{c}"] = (daily_summaries[c] - mean) / std
    return out
