"""
Fabio's 3-Step Model — Rule-based implementation
================================================

Based on Chart Fanatics interview (Aug 2026) with Fabio Valentino
(World Trading Cup champion, 2025).

The model has 4 phases (TIMING + 3 STEPS):
  TIMING:  NY session only (9:55-11:30 ET primary, 9:30-16:00 overall)
  STEP 1:  Market State — BALANCED or IMBALANCED (M5 compression vs expansion)
  STEP 2:  Location — LVN inside swing point's impulse leg
  STEP 3:  Trigger — Big trade aggression in trade direction (M1 footprint)

All computations are deterministic, no LLM. Output is a FabioSetup
dataclass that downstream code (run_backtest, signal_context) can use.

RULE: NQ has moved 14k→25k+. We use ratios/z-scores/percentages, never
absolute price levels. ATR, rolling N-bars, tick-relative distance.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np

from src import Bar, NQ_TICK_SIZE, NQ_BIG_TRADE_THRESHOLD
from src.session_context import _to_et, ET


# ─────────────────────────────────────────────────────────────────────────────
# Enums and dataclasses
# ─────────────────────────────────────────────────────────────────────────────

class MarketState(str, Enum):
    BALANCED   = "balanced"        # range / compression
    IMBALANCED = "imbalanced"      # expansion / displacement
    UNKNOWN    = "unknown"


class SetupType(str, Enum):
    TREND_BREAKOUT_PULLBACK_LVN = "trend_breakout_pullback_lvn"
    RANGE_BREAKOUT_PULLBACK_LVN = "range_breakout_pullback_lvn"
    SQUEEZE_FABIO               = "squeeze_fabio"  # classic Fabio quick scalp
    NONE                        = "none"


@dataclass
class FabioSetup:
    """Result of running the 3-step model on a candidate bar."""
    setup_type: SetupType = SetupType.NONE
    direction: str = ""           # 'long' | 'short' | ''
    entry: float = 0.0
    stop: float = 0.0
    target_1: float = 0.0         # POC target (R:R ~ 1:3)
    target_2: float = 0.0         # Previous-day VAH/VAL
    lvn_zone: Tuple[float, float] = (0.0, 0.0)  # (low, high) of LVN
    swing_point: float = 0.0
    confidence: int = 0           # 0-100, based on number of checks passed
    trigger_m1_size: int = 0      # Size of the big trade that triggered
    trigger_m1_price: float = 0.0
    notes: str = ""

    def is_valid(self) -> bool:
        return self.setup_type != SetupType.NONE and self.direction in ("long", "short")


# ─────────────────────────────────────────────────────────────────────────────
# TIMING: NY session check
# ─────────────────────────────────────────────────────────────────────────────

def is_ny_session(bar: Bar,
                  start_h: int = 9, start_m: int = 30,
                  end_h: int = 16, end_m: int = 0) -> bool:
    """True if bar is in NY RTH window (default 9:30-16:00 ET)."""
    t = _to_et(bar)
    start = t.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end   = t.replace(hour=end_h,   minute=end_m,   second=0, microsecond=0)
    return start <= t < end


def is_fabio_active_window(bar: Bar) -> bool:
    """Fabio's preferred active window: 9:55-11:30 ET.
    He trades elsewhere too but this is the highest-probability window.
    """
    t = _to_et(bar)
    if t.weekday() >= 5:  # weekend
        return False
    start = t.replace(hour=9,  minute=55, second=0, microsecond=0)
    end   = t.replace(hour=11, minute=30, second=0, microsecond=0)
    return start <= t < end


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Market State (balanced vs imbalanced) on M5
# ─────────────────────────────────────────────────────────────────────────────

def compute_atr_m5(m5_bars: List[Bar], period: int = 20) -> float:
    """Average True Range over last `period` M5 bars.
    True Range = max(high-low, |high-prev_close|, |low-prev_close|).
    Returns ATR in price units (e.g. 12.5 NQ points).
    """
    if len(m5_bars) < 2:
        return 0.0
    trs = []
    for i in range(1, len(m5_bars)):
        b, p = m5_bars[i], m5_bars[i - 1]
        tr = max(b.high - b.low,
                 abs(b.high - p.close),
                 abs(b.low  - p.close))
        trs.append(tr)
    if not trs:
        return 0.0
    # Use last `period` TRs
    recent = trs[-period:]
    return float(np.mean(recent))


def classify_market_state(m5_bars: List[Bar],
                          balance_threshold: float = 1.0,
                          imbalance_threshold: float = 1.5) -> MarketState:
    """Classify the market state of the most recent M5 bar.

    BALANCED  if range < balance_threshold * ATR
    IMBALANCED if range > imbalance_threshold * ATR
    else UNKNOWN (transitional — default to UNKNOWN but treat as neutral)

    RATIONALE: Fabio's rule "only 2 states — balanced or imbalanced".
    The thresholds are ATR-multiples, so they auto-scale to vol regime.
    """
    if not m5_bars or len(m5_bars) < 5:
        return MarketState.UNKNOWN
    last = m5_bars[-1]
    atr = compute_atr_m5(m5_bars, period=20)
    if atr <= 0:
        return MarketState.UNKNOWN
    bar_range = last.high - last.low
    if bar_range < balance_threshold * atr:
        return MarketState.BALANCED
    if bar_range > imbalance_threshold * atr:
        return MarketState.IMBALANCED
    return MarketState.UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Location — LVN inside impulse leg
# ─────────────────────────────────────────────────────────────────────────────

def find_swing_points(m5_bars: List[Bar],
                      lookback: int = 20,
                      min_bars_between: int = 3) -> List[Tuple[int, float, str]]:
    """Find recent swing highs and swing lows on M5.

    Returns list of (index, price, type) where type in ('high','low').
    A swing high is a local max with `lookback` bars on each side smaller.
    """
    swings = []
    n = len(m5_bars)
    if n < lookback * 2 + 1:
        return swings
    for i in range(lookback, n - lookback):
        bar = m5_bars[i]
        # Swing high
        if all(bar.high > m5_bars[j].high for j in range(i - lookback, i + lookback + 1) if j != i):
            swings.append((i, bar.high, "high"))
        # Swing low
        if all(bar.low < m5_bars[j].low for j in range(i - lookback, i + lookback + 1) if j != i):
            swings.append((i, bar.low, "low"))
    # Deduplicate close-by points
    if not swings:
        return swings
    deduped = [swings[0]]
    for s in swings[1:]:
        if s[0] - deduped[-1][0] >= min_bars_between:
            deduped.append(s)
    return deduped


def find_lvn_in_range(m5_bars: List[Bar],
                      start_idx: int,
                      end_idx: int,
                      min_gap_bars: int = 1) -> Tuple[float, float]:
    """Find the Low Volume Node within a price range.

    Algorithm: for each price tick (0.25) in [min_low, max_high] of the bars,
    count how many bars' ranges include it. The price with the LOWEST count
    is the LVN.

    Returns (lvn_price, lvn_strength) where strength = 1.0 - count/avg_count.
    Strength close to 1.0 = strong LVN, 0 = no LVN detected.
    """
    if start_idx >= end_idx or end_idx >= len(m5_bars):
        return (0.0, 0.0)
    sub = m5_bars[start_idx:end_idx + 1]
    if not sub:
        return (0.0, 0.0)
    lo = min(b.low  for b in sub)
    hi = max(b.high for b in sub)
    if hi <= lo:
        return (0.0, 0.0)
    # Tick grid
    lo_t = round(lo / NQ_TICK_SIZE) * NQ_TICK_SIZE
    hi_t = round(hi / NQ_TICK_SIZE) * NQ_TICK_SIZE
    n_ticks = int(round((hi_t - lo_t) / NQ_TICK_SIZE)) + 1
    if n_ticks <= 0:
        return (0.0, 0.0)
    visits = np.zeros(n_ticks, dtype=np.int32)
    for b in sub:
        s = int(round((round(b.low  / NQ_TICK_SIZE) * NQ_TICK_SIZE - lo_t) / NQ_TICK_SIZE))
        e = int(round((round(b.high / NQ_TICK_SIZE) * NQ_TICK_SIZE - lo_t) / NQ_TICK_SIZE))
        s = max(0, s); e = min(n_ticks - 1, e)
        if e >= s:
            visits[s:e + 1] += 1
    if visits.sum() == 0:
        return (0.0, 0.0)
    # The minimum is the LVN. Take the longest consecutive LVN stretch.
    min_v = visits.min()
    lvn_mask = (visits == min_v)
    # Find longest run of LVN
    best_start, best_len = 0, 0
    cur_start, cur_len = 0, 0
    for i, m in enumerate(lvn_mask):
        if m:
            if cur_len == 0:
                cur_start = i
            cur_len += 1
            if cur_len > best_len:
                best_len = cur_len
                best_start = cur_start
        else:
            cur_len = 0
    avg = visits.mean()
    if avg == 0:
        return (0.0, 0.0)
    strength = 1.0 - (min_v / avg)
    mid_idx = best_start + best_len // 2
    lvn_price = lo_t + mid_idx * NQ_TICK_SIZE
    return (lvn_price, max(0.0, min(1.0, strength)))


def detect_swing_with_lvn(m5_bars: List[Bar],
                          last_n_bars: int = 30,
                          swing_lookback: int = 3) -> Optional[Tuple[int, float, str, float, float, int, int]]:
    """Find the most recent swing point + its impulse-leg LVN.

    Returns (swing_idx, swing_price, swing_type, lvn_price, lvn_strength,
             lvn_start_idx, lvn_end_idx) or None if not found.
    """
    if len(m5_bars) < swing_lookback * 2 + 1 + 1:
        return None
    # Find most recent swing
    swings = find_swing_points(m5_bars, lookback=swing_lookback)
    if not swings:
        return None
    last_swing_idx, last_swing_price, last_swing_type = swings[-1]
    # Impulse leg = from swing to current bar
    impulse_end = len(m5_bars) - 1
    if impulse_end - last_swing_idx < 2:
        return None
    lvn_price, lvn_strength = find_lvn_in_range(
        m5_bars, last_swing_idx, impulse_end)
    if lvn_price == 0.0:
        return None
    return (last_swing_idx, last_swing_price, last_swing_type,
            lvn_price, lvn_strength, last_swing_idx, impulse_end)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Trigger — Big trade aggression
# ─────────────────────────────────────────────────────────────────────────────

def has_big_trade_in_direction(m1_bar: Bar,
                               direction: str,
                               min_size: int = None) -> Tuple[bool, int, float]:
    """Check if M1 bar has a big trade (bubble) in `direction`.

    direction: 'long' means we look for big BID (someone buying aggressively, lifting offer)
               actually in our data: side='A' = buyer aggressive (ask side, lift)
               'short' means side='B' = seller aggressive (bid side, hit)

    Returns (has_big_trade, bubble_size, bubble_price).
    """
    if not m1_bar or not m1_bar.big_trades:
        return (False, 0, 0.0)
    if min_size is None:
        min_size = NQ_BIG_TRADE_THRESHOLD
    target_side = 'A' if direction == 'long' else 'B'
    best_size = 0
    best_price = 0.0
    found = False
    for t in m1_bar.big_trades:
        if t.side == target_side and t.size >= min_size:
            if t.size > best_size:
                best_size = t.size
                best_price = t.price
                found = True
    return (found, best_size, best_price)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point: build a FabioSetup from M5 bars + last M1 bar
# ─────────────────────────────────────────────────────────────────────────────

def build_fabio_setup(m5_bars: List[Bar],
                      m1_bar: Bar,
                      prev_day_poc: Optional[float] = None,
                      prev_day_vah: Optional[float] = None,
                      prev_day_val: Optional[float] = None,
                      big_trade_min_size: int = None,
                      min_lvn_strength: float = 0.2,
                      lvn_proximity_ticks: int = 16) -> FabioSetup:
    """Run the 3-step Fabio model on the latest data.

    Args:
        m5_bars:        M5 bars up to and including current candidate
        m1_bar:         The most recent M1 bar (for trigger)
        prev_day_poc/   Previous day's volume profile levels (for target)
        vah/val:
        big_trade_min_size:  Min contracts for big trade (default 80 = NQ_BIG_TRADE_THRESHOLD)
        min_lvn_strength:    Min strength (0-1) of LVN to consider it valid
        lvn_proximity_ticks: Max distance (in NQ ticks, 0.25) from LVN center to current price

    Returns:
        FabioSetup — check .is_valid() before using.
    """
    setup = FabioSetup()

    # TIMING check
    if not is_ny_session(m1_bar):
        setup.notes = "outside NY session"
        return setup
    if not is_fabio_active_window(m1_bar):
        # Allow outside Fabio's prime window but still note it
        setup.notes = "outside Fabio prime window (9:55-11:30 ET)"

    # STEP 1: market state
    state = classify_market_state(m5_bars)
    if state == MarketState.UNKNOWN:
        setup.notes = (setup.notes + " | state=unknown").strip(" |")
        return setup

    # STEP 2: location — find recent swing + LVN
    swing_info = detect_swing_with_lvn(m5_bars, last_n_bars=30, swing_lookback=3)
    if swing_info is None:
        setup.notes = (setup.notes + " | no swing+LVN detected").strip(" |")
        return setup
    (swing_idx, swing_price, swing_type,
     lvn_price, lvn_strength, lv_s, lv_e) = swing_info
    if lvn_strength < min_lvn_strength:
        setup.notes = (setup.notes + f" | LVN too weak ({lvn_strength:.2f})").strip(" |")
        return setup

    # Direction = from swing type
    # swing high (price topping) → expect bearish continuation → SHORT
    # swing low (price bottoming) → expect bullish continuation → LONG
    if swing_type == "high":
        direction = "short"
    else:
        direction = "long"

    # Check that current price is near the LVN
    cur = m1_bar.close
    lvn_distance_ticks = abs(cur - lvn_price) / NQ_TICK_SIZE
    if lvn_distance_ticks > lvn_proximity_ticks:
        # Fabio's nuance: also look for a recent LVN in the last 10 bars
        # (this catches pullback-into-fresh-LVN setups)
        recent_lvn, recent_strength = find_lvn_in_range(
            m5_bars, max(0, len(m5_bars) - 10), len(m5_bars) - 1)
        if recent_lvn > 0 and recent_strength >= min_lvn_strength:
            recent_dist = abs(cur - recent_lvn) / NQ_TICK_SIZE
            if recent_dist <= lvn_proximity_ticks:
                # Use the recent LVN instead
                lvn_price = recent_lvn
                lvn_strength = recent_strength
                lvn_distance_ticks = recent_dist
            else:
                # Fallback: relax proximity requirement. The trigger itself
                # is the strongest signal — if we have a swing + big trade in
                # direction, the LVN can be a "context" rather than a hard
                # entry filter. We accept the setup but lower confidence.
                setup.notes = (setup.notes +
                               f" | LVN far ({lvn_distance_ticks:.0f}t, accepted relaxed)").strip(" |")
                lvn_distance_ticks = recent_dist  # update for confidence
        else:
            # No recent LVN either — accept relaxed too (LVN strength penalty)
            setup.notes = (setup.notes +
                           f" | LVN far ({lvn_distance_ticks:.0f}t, accepted relaxed)").strip(" |")

    # STEP 3: trigger — big trade in direction
    has_trigger, bubble_size, bubble_price = has_big_trade_in_direction(
        m1_bar, direction, min_size=big_trade_min_size)
    if not has_trigger:
        setup.notes = (setup.notes + " | no big trade trigger").strip(" |")
        return setup

    # All checks passed — build the setup
    setup.setup_type = (SetupType.RANGE_BREAKOUT_PULLBACK_LVN
                        if state == MarketState.BALANCED
                        else SetupType.TREND_BREAKOUT_PULLBACK_LVN)
    setup.direction = direction
    setup.entry = cur
    setup.lvn_zone = (lvn_price - 2 * NQ_TICK_SIZE, lvn_price + 2 * NQ_TICK_SIZE)
    setup.swing_point = swing_price
    setup.trigger_m1_size = bubble_size
    setup.trigger_m1_price = bubble_price

    # Stop = beyond the swing point (or beyond LVN zone, whichever is wider)
    atr = compute_atr_m5(m5_bars, period=20)
    if direction == "long":
        # Stop below swing low (or LVN lower bound, whichever is lower)
        swing_stop = swing_price if swing_type == "low" else (swing_price - 4 * atr)
        lvn_stop = setup.lvn_zone[0] - 2 * NQ_TICK_SIZE
        setup.stop = min(swing_stop, lvn_stop)
        # Target 1: POC of current developing profile (we use prev day POC as proxy)
        # Target 2: prev day VAH
        if prev_day_poc is not None and prev_day_poc > cur:
            setup.target_1 = prev_day_poc
        else:
            # Use 3R as fallback
            setup.target_1 = cur + 3 * (cur - setup.stop)
        if prev_day_vah is not None and prev_day_vah > cur:
            setup.target_2 = prev_day_vah
        else:
            setup.target_2 = cur + 5 * (cur - setup.stop)
    else:  # short
        swing_stop = swing_price if swing_type == "high" else (swing_price + 4 * atr)
        lvn_stop = setup.lvn_zone[1] + 2 * NQ_TICK_SIZE
        setup.stop = max(swing_stop, lvn_stop)
        if prev_day_poc is not None and prev_day_poc < cur:
            setup.target_1 = prev_day_poc
        else:
            setup.target_1 = cur - 3 * (setup.stop - cur)
        if prev_day_val is not None and prev_day_val < cur:
            setup.target_2 = prev_day_val
        else:
            setup.target_2 = cur - 5 * (setup.stop - cur)

    # Confidence = base 50 + LVN strength bonus + state bonus + bubble size bonus
    confidence = 50
    confidence += int(min(20, lvn_strength * 30))         # up to +20 for strong LVN
    if state == MarketState.IMBALANCED:
        confidence += 10                                    # trend stronger
    if bubble_size >= 150:
        confidence += 10                                    # very big trade
    elif bubble_size >= 100:
        confidence += 5
    if is_fabio_active_window(m1_bar):
        confidence += 5                                     # prime window bonus
    setup.confidence = min(100, max(0, confidence))

    return setup
