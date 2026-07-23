"""Constants for the day-similarity engine.

RULE: NQ has moved from ~14k (2024) to ~30k (2026).  Volume regimes also
shift.  No absolute price, point, dollar, or fixed-tick thresholds here.
Everything is expressed via rolling z-scores, percentages, ratios, or
ATR-multiples computed from the actual data at runtime.

The only constants are structural (number of minutes in a phase, number of
HVN/LVN kept, rolling-window lengths in calendar or session units).
"""
from __future__ import annotations

# --- Session structure (ET) ---------------------------------------------------
# We work in America/New_York.  These are wall-clock minute offsets, not
# absolute NQ points.
PRE_MARKET_START_H_ET      = 0    # 00:00 ET
RTH_OPEN_H_ET              = 9
RTH_OPEN_M_ET              = 30   # 9:30 ET
IB_END_H_ET                = 10   # Initial Balance ends 10:00 ET (30 min)
IB_END_M_ET                = 0
IB_LEN_MIN                 = 30
PRED_HORIZON_END_H_ET      = 10   # first 30m prediction: 10:00-10:30
PRED_HORIZON_END_M_ET      = 30
RTH_END_H_ET               = 16   # 16:00 ET
RTH_END_M_ET               = 0

# --- Profile structure (TPO, in ticks) ---------------------------------------
# NQ tick size is 0.25 (NqBacktest's NQ_TICK_SIZE), but we do NOT hardcode
# the dollar value: at 0.25/tick = $5/tick.  We always express price
# distances in "ticks" as a unitless count, and convert to % at output.
TICK_SIZE                  = 0.25

# How many HVN / LVN to keep from each profile.
HVN_KEEP                   = 5
LVN_KEEP                   = 5

# --- Rolling normalization windows -------------------------------------------
# History for rolling z-scores.  60 sessions ~= 3 months.
ROLLING_WINDOW_SESSIONS    = 60
ROLLING_WINDOW_SHORT       = 20  # short-term baseline

# --- Prediction / outcomes ---------------------------------------------------
# Targets to predict (in % of the reference price at the moment of prediction).
# All defined here so features and labels stay in sync.
OUTCOME_HORIZONS_MIN = {
    "next_30m":   30,    # 10:00 -> 10:30
    "next_60m":   60,    # 10:00 -> 11:00
    "rest_of_day": None, # 10:00 -> 16:00 (set below as a marker)
}
# A special marker; the rest-of-day horizon is filled at runtime because it
# has no fixed minute count.
REST_OF_DAY_MARKER = "rest_of_day"

# --- Path fan settings --------------------------------------------------------
PATH_FAN_N_PATHS          = 100      # number of historical paths to draw
PATH_FAN_QUANTILES        = (0.10, 0.50, 0.90)

# --- Day of week categorical mapping (one-hot at runtime) -------------------
DOW_LIST = ("Mon", "Tue", "Wed", "Thu", "Fri")

# --- Schemas (column names) --------------------------------------------------
# Outcome columns
OUTCOME_RET_COL    = "ret_pct"
OUTCOME_MFE_COL    = "mfe_pct"
OUTCOME_MAE_COL    = "mae_pct"
OUTCOME_RANGE_COL  = "range_pct"
OUTCOME_DIR_COL    = "dir_sign"   # -1, 0, +1

# Pre-market phase columns
PM_PREFIX = "pm_"
# Initial-balance phase columns
IB_PREFIX = "ib_"
# Calendar / context columns
CTX_PREFIX = "ctx_"
# Volatility / regime
VOL_PREFIX = "vol_"
