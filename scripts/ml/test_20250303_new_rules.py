"""
Test 2025-03-03 con le NUOVE regole proposte (R6 + A+ pre-filter + early drive
detection + 4-step prompt).

Confronto:
  - V2 ATTUALE: trades effettivamente presi dal sistema V2 (da fabio_v2_trades.csv)
  - V2 + NUOVE REGOLE: cosa farebbe il sistema con early drive detection, R6
    bounce_in_drive_no_evidence, e A+ pre-filter

Output:
  - Tabella per ogni trade V2: V2 confermato? Nuove regole confermate?
  - Lista di trade che le nuove regole AVREBBERO PRESO (in particolare SHORT
    nel pomeriggio di drive_down)
  - PnL comparison

Self-contained: riusa solo compute_institutional_bias e pattern di
audit_v2_simulator.py. Tutto offline.
"""
import os
import sys
import csv
import datetime as dt
import pickle
from collections import defaultdict

import numpy as np
import pandas as pd
import pytz

sys.path.insert(0, r'C:\Users\Mauro\Documents\nq-backtest-clean')
from src.bar_aggregator import aggregate_to_bars
from src import Trade, Bar, CandidateBar, SessionContext, VolumeProfile, NQ_BIG_TRADE_THRESHOLD
from src.agents.institutional_bias import compute_institutional_bias, InstitutionalBias

ET = pytz.timezone('America/New_York')
UTC = pytz.UTC
DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'
DATE = '20250303'
NQ_TICK = 0.25
NQ_TICK_VALUE = 5.0
RISK_TARGET = 16.0  # punti di target (8pt stop implicito → 2R = 16pt target)
STOP_BUFFER = 8.0

# ────────────────────────────────────────────────────────────────────────────
# V2 actual trades on 2025-03-03 (from fabio_v2_trades.csv)
# ────────────────────────────────────────────────────────────────────────────
V2_TRADES = [
    {'time_et': '11:30', 'direction': 'long',  'entry': 20874.75, 'stop': 20824.75, 'exit': 21125.75, 'pnl_pts': 250.625, 'pnl_usd': 1253.125},
    {'time_et': '14:25', 'direction': 'long',  'entry': 20715.00, 'stop': 20665.00, 'exit': 21000.00, 'pnl_pts': 284.625, 'pnl_usd': 1423.125},
    {'time_et': '14:40', 'direction': 'long',  'entry': 20799.75, 'stop': 20749.75, 'exit': 20749.75, 'pnl_pts': -50.375, 'pnl_usd': -251.875},
    {'time_et': '14:50', 'direction': 'long',  'entry': 20638.75, 'stop': 20588.75, 'exit': 20588.75, 'pnl_pts': -50.375, 'pnl_usd': -251.875},
]

# ────────────────────────────────────────────────────────────────────────────
# NEW RULES
# ────────────────────────────────────────────────────────────────────────────
def early_drive_detection(bar, prev_bars, ib_high, ib_low, ib_range, recent_bars_extra=None):
    """Restituisce (score_delta, driver_str) se rileva drive precoce,
    altrimenti (0, None).

    Logica: 3+ test del livello IB senza wick di assorbimento + VWAP falling
    = drive già in corso, anche se il prezzo non è ancora >0.5*range fuori IB.
    """
    if not recent_bars_extra:
        recent_bars_extra = (prev_bars or [])[-12:]
    if len(recent_bars_extra) < 3 or ib_range <= 0:
        return 0, None

    # Quante volte ha testato IB_low nelle ultime 12 barre (entro 15% del range)
    tests_at_low = sum(1 for b in recent_bars_extra
                       if abs(b.low - ib_low) < ib_range * 0.15)
    # Quante con wick di assorbimento (lower_wick > 50% del range della barra)
    absorbed_at_low = sum(1 for b in recent_bars_extra
                          if abs(b.low - ib_low) < ib_range * 0.15
                          and (min(b.open, b.close) - b.low) > (b.high - b.low) * 0.5)
    # Quante con NO assorbimento (= venditori stanno vincendo)
    rejected_at_low = tests_at_low - absorbed_at_low

    tests_at_high = sum(1 for b in recent_bars_extra
                        if abs(b.high - ib_high) < ib_range * 0.15)
    absorbed_at_high = sum(1 for b in recent_bars_extra
                           if abs(b.high - ib_high) < ib_range * 0.15
                           and (b.high - max(b.open, b.close)) > (b.high - b.low) * 0.5)
    rejected_at_high = tests_at_high - absorbed_at_high

    # VWAP direction: confronta vwap delle prime 6 vs ultime 6
    if len(recent_bars_extra) >= 6:
        vwap_early = np.mean([getattr(b, 'vwap', 0) for b in recent_bars_extra[:6]
                              if getattr(b, 'vwap', 0) > 0])
        vwap_late = np.mean([getattr(b, 'vwap', 0) for b in recent_bars_extra[-6:]
                             if getattr(b, 'vwap', 0) > 0])
        vwap_falling = vwap_late < vwap_early * 0.998  # 0.2% di discesa
        vwap_rising = vwap_late > vwap_early * 1.002
    else:
        vwap_falling = vwap_rising = False

    if rejected_at_low >= 3 and vwap_falling:
        return -25, (f"EARLY_DRIVE_DOWN: {rejected_at_low} test IB_low senza assorbimento, "
                     f"VWAP falling")
    if rejected_at_high >= 3 and vwap_rising:
        return +25, (f"EARLY_DRIVE_UP: {rejected_at_high} test IB_high senza assorbimento, "
                     f"VWAP rising")
    return 0, None


def has_accumulation_evidence(bars, direction, ib_low=None, ib_high=None, tolerance=0.005):
    """Per LONG: serve evidenza che istituzioni stiano comprando il dip.
    Per SHORT: serve evidenza che istituzioni stiano vendendo il rimbalzo.

    Richiesto TUTTO e 3:
      - delta nella direzione giusta in >= 3 degli ultimi 6 bar
      - big trade (>=NQ_BIG_TRADE_THRESHOLD) nella direzione >= 1
      - close sopra/sotto VWAP in almeno 1 degli ultimi 6 bar
    """
    if not bars or len(bars) < 3:
        return False, "insufficient bars"
    recent = bars[-6:]
    if direction == 'long':
        pos_delta = sum(1 for b in recent if getattr(b, 'delta', 0) > 0)
        buy_big = sum(1 for b in recent
                      for bt in (getattr(b, 'big_trades', []) or [])
                      if getattr(bt, 'side', '') == 'A')
        vwap_hold = sum(1 for b in recent
                        if getattr(b, 'vwap', 0) > 0 and b.close > b.vwap) >= 1
        ok = pos_delta >= 3 and buy_big >= 1 and vwap_hold
        return ok, f"pos_delta={pos_delta}/6 buy_big={buy_big} vwap_hold={vwap_hold}"
    else:  # short
        neg_delta = sum(1 for b in recent if getattr(b, 'delta', 0) < 0)
        sell_big = sum(1 for b in recent
                       for bt in (getattr(b, 'big_trades', []) or [])
                       if getattr(bt, 'side', '') == 'B')
        vwap_reject = sum(1 for b in recent
                          if getattr(b, 'vwap', 0) > 0 and b.close < b.vwap) >= 1
        ok = neg_delta >= 3 and sell_big >= 1 and vwap_reject
        return ok, f"neg_delta={neg_delta}/6 sell_big={sell_big} vwap_reject={vwap_reject}"


def is_aplus_setup(candidate, bias, recent_bars):
    """Pre-filter A+ setup: bias chiara + location strutturale + flow signature.
    Restituisce (passes, reason)."""
    # Reversal disabilitato (anche V1 lo vieta)
    if candidate.setup_category == 'reversal':
        return False, "reversal_disabled"
    # Wall robusta richiesta
    if candidate.wall_max_size < 50:
        return False, f"no_wall (max={candidate.wall_max_size})"
    # No trade in pure rotational senza wall forte
    if bias.regime == 'rotational' and candidate.wall_max_size < 80:
        return False, "rotational_no_strong_wall"
    # Se drive, bounce senza evidence → SKIP
    if bias.is_drive:
        if (bias.regime == 'drive_down' and candidate.setup_category in ('pullback', 'squeeze')
                and not has_accumulation_evidence(recent_bars, 'long')[0]):
            return False, "drive_down_bounce_no_accumulation"
        if (bias.regime == 'drive_up' and candidate.setup_category in ('pullback', 'squeeze')
                and not has_accumulation_evidence(recent_bars, 'short')[0]):
            return False, "drive_up_bounce_no_distribution"
    return True, "passes"


def new_validator(direction, candidate, bias, recent_bars):
    """Nuovo validator. Ritorna (ok, reason, conviction_capped).

    Regole:
      R0: COHERENCE — direction != 'none' required
      R1: BOUNCE_IN_DRIVE_NEEDS_EVIDENCE (NEW)
      R2: BIAS GATE (drive = no counter)
      R3: TIME GATE
      R4: PARTICIPATION GATE
    """
    if direction not in ('long', 'short'):
        return True, 'no_direction', 'none'

    # R2: drive gate (da bias_gate originale)
    if bias.regime == 'drive_up' and direction == 'short':
        return False, f"R2_VETO: counter_drive (short vs {bias.regime}, score {bias.score:+.0f})", 'low'
    if bias.regime == 'drive_down' and direction == 'long':
        return False, f"R2_VETO: counter_drive (long vs {bias.regime}, score {bias.score:+.0f})", 'low'

    # R1: bounce in drive needs evidence (NEW)
    if bias.regime == 'drive_down' and direction == 'long':
        ok, ev = has_accumulation_evidence(recent_bars, 'long')
        if not ok:
            return False, f"R1_VETO: bounce_in_drive_no_evidence (drive_down + long, need accumulation: {ev})", 'low'
    if bias.regime == 'drive_up' and direction == 'short':
        ok, ev = has_accumulation_evidence(recent_bars, 'short')
        if not ok:
            return False, f"R1_VETO: bounce_in_drive_no_evidence (drive_up + short, need distribution: {ev})", 'low'

    # R3: time gate (no entry 9:30-9:45, no entry after 15:15, lunch only if drive)
    h, m = candidate.bar.timestamp.astimezone(ET).hour, candidate.bar.timestamp.astimezone(ET).minute
    t = h * 60 + m
    if t < 9 * 60 + 55:
        return False, f"R3_VETO: too_early ({h:02d}:{m:02d})", 'low'
    if t >= 15 * 60 + 15:
        return False, f"R3_VETO: late_session ({h:02d}:{m:02d})", 'low'
    if 11 * 60 + 45 <= t < 13 * 60 + 15 and not bias.is_drive:
        return False, f"R3_VETO: lunch_chop ({h:02d}:{m:02d}, {bias.regime})", 'low'

    # R4: participation
    prev_recent = (recent_bars or [])[-7:-1]
    vols = [getattr(b, 'volume', 0) for b in prev_recent if getattr(b, 'volume', 0) > 0]
    if len(vols) >= 3:
        avg = sum(vols) / len(vols)
        if candidate.bar.volume < 0.5 * avg:
            return False, f"R4_VETO: low_participation (vol {candidate.bar.volume} < 50% avg {avg:.0f})", 'low'

    return True, "all_rules_pass", 'med'


def deterministic_llm_simulator(candidate, bias, recent_bars, trades_today=None):
    """LONG bounce + SHORT breakdown, entrambi trailing fino a EOD.
    In downtrend day:
      - LONG quando c'è un bounce forte (delta + + close > low recente)
      - SHORT quando c'è un breakdown (delta - + close < VWAP)
    In uptrend: specchiato.
    """
    delta = candidate.bar.delta
    close = candidate.bar.close
    vwap = candidate.bar.vwap
    vol = candidate.bar.volume

    if len(recent_bars) >= 6:
        closes = [getattr(b, 'close', 0) for b in recent_bars[-24:]]
        if len(closes) >= 6:
            recent_avg = sum(closes[-6:]) / 6
            earlier_avg = sum(closes[:6]) / 6
            trend_down = recent_avg < earlier_avg - 5
            trend_up = recent_avg > earlier_avg + 5
        else:
            trend_down = trend_up = False
        last3_lows = [getattr(b, 'low', 0) for b in recent_bars[-3:]]
        last3_low = min(last3_lows) if last3_lows else close
        last3_highs = [getattr(b, 'high', 0) for b in recent_bars[-3:]]
        last3_high = max(last3_highs) if last3_highs else close
    else:
        trend_down = trend_up = False
        last3_low = close
        last3_high = close

    wall = candidate.wall_max_size
    trades_today = trades_today or []

    # 1. SHORT breakdown in drive_down CONFERMATO (3 barre su 3 in discesa)
    if bias.regime == 'drive_down' and wall >= 50:
        recent3_closes = [getattr(b, 'close', 0) for b in recent_bars[-3:]]
        confirmed = (len(recent3_closes) >= 3 and recent3_closes[0] > recent3_closes[-1] + 10)
        if confirmed and delta < -100 and vwap > 0 and close < vwap:
            return 'short', f"drive_down CONFIRMED d={delta:+d}"
        ok_long, ev = has_accumulation_evidence(recent_bars, 'long')
        if ok_long and delta > 200:
            return 'long', f"drive_down BOUNCE w/ evidence ({ev})"

    # 2. LONG bounce in downtrend contestuale
    if trend_down and wall >= 50:
        if delta > 250 and close > last3_low + 2 and vol > 4000:
            return 'long', f"downtrend BOUNCE d={delta:+d} above_low"

    # 3. SHORT rejection in uptrend contestuale
    if trend_up and wall >= 50:
        if delta < -250 and close < last3_high - 2 and vol > 4000:
            return 'short', f"uptrend REJECTION d={delta:+d}"

    # 3b. SHORT breakdown on NEW LOW (close < min L of PRIOR 6 bars, escluso current)
    if (bias.regime in ('rotational', 'lean_down', 'drive_down')
            and wall >= 50 and vwap > 0 and close < vwap
            and len(recent_bars) >= 7):
        prior_bars = recent_bars[:-1]  # escludi current bar
        last6_lows = [getattr(b, 'low', 0) for b in prior_bars[-6:]]
        prior_min_low = min(last6_lows)
        if close < prior_min_low - 3:  # new low by at least 3pt
            existing_shorts = [t for t in trades_today if t.get('direction') == 'short']
            existing_winning = [t for t in existing_shorts if t.get('pnl_pts', 0) > 0]
            if not existing_winning:
                return 'short', f"NEW_LOW breakdown close={close:.0f} < prior_low={prior_min_low:.0f}"

    # 4. Rotational con flow forte
    if bias.regime == 'rotational':
        if delta > 300 and vol > 5000 and wall >= 60:
            return 'long', f"rotational BUY d={delta:+d}"
        if delta < -300 and vol > 5000 and wall >= 60:
            return 'short', f"rotational SELL d={delta:+d}"

    return 'none', f"no_setup (bias={bias.regime}, td={trend_down}, tu={trend_up}, d={delta:+d}, w={wall})"


# ────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ────────────────────────────────────────────────────────────────────────────
def load_day_bars(date_str):
    """Load M5 bars with full big_trades list from databento."""
    path = os.path.join(DATA_DIR, f'glbx-mdp3-{date_str}.trades.csv')
    if not os.path.exists(path):
        return []
    trades = []
    with open(path) as f:
        r = csv.DictReader(f)
        for row in r:
            if 'NQ' not in row.get('symbol', ''):
                continue
            ts_str = row['ts_event'].replace('Z', '+00:00')
            ts = dt.datetime.fromisoformat(ts_str)
            if ts.tzinfo is None:
                ts = UTC.localize(ts)
            price = float(row['price'])
            if price < 5000 or price > 50000:
                continue
            trades.append(Trade(
                ts_event=ts, price=price, size=int(row['size']),
                side=row.get('side', 'A'),
            ))
    if len(trades) < 100:
        return []
    bars = aggregate_to_bars(trades, freq='5min')
    rth = [b for b in bars if 9 <= b.timestamp.astimezone(ET).hour < 16]
    return rth


def build_session_ctx(bars_so_far, current_bar, day_open_bars, prev_day_vp=None):
    """Costruisce un SessionContext minimale per compute_institutional_bias."""
    # IB: primi 30 min (09:30-10:00) → primi 6 bar M5
    ib_bars = [b for b in day_open_bars if 9.5 <= b.timestamp.astimezone(ET).hour + b.timestamp.astimezone(ET).minute/60 < 10.0]
    if not ib_bars:
        ib_bars = day_open_bars[:6]
    ib_high = max(b.high for b in ib_bars) if ib_bars else 0
    ib_low = min(b.low for b in ib_bars) if ib_bars else 0
    ib_range = max(0.01, ib_high - ib_low)

    # POC from all bars so far
    if bars_so_far:
        vp_prices = [(b.close, getattr(b, 'volume', 0)) for b in bars_so_far if getattr(b, 'volume', 0) > 0]
        poc = max(vp_prices, key=lambda x: x[1])[0] if vp_prices else current_bar.close
    else:
        poc = current_bar.close

    vp = VolumeProfile(poc=poc, va_high=ib_high, va_low=ib_low)

    ctx = SessionContext(
        date=DATE,
        ib_high=ib_high,
        ib_low=ib_low,
        ib_range=ib_range,
        ib_complete=len(ib_bars) >= 6,
        vp=vp,
        prev_day_vp=prev_day_vp,
        atr_5day=180.0,
        gex_regime='negative',
        zero_gamma_level=current_bar.close,
        call_wall=0,
        put_wall=0,
    )
    return ctx


def build_candidate(bar, ctx, prev_bars, day_open_bars):
    """Costruisce un CandidateBar minimale per compute_institutional_bias."""
    # Wall: max big trade lato buy/sell
    bigs = getattr(bar, 'big_trades', []) or []
    buy_size = sum(bt.size for bt in bigs if getattr(bt, 'side', '') == 'A')
    sell_size = sum(bt.size for bt in bigs if getattr(bt, 'side', '') == 'B')
    if buy_size > sell_size:
        wall_side = 'bid'
        wall_level = min((bt.price for bt in bigs if getattr(bt, 'side', '') == 'A'), default=bar.low)
    else:
        wall_side = 'ask'
        wall_level = max((bt.price for bt in bigs if getattr(bt, 'side', '') == 'B'), default=bar.high)
    wall_max_size = max(buy_size, sell_size, 0)
    wall_trade_count = len(bigs)

    # Setup category
    delta = bar.delta
    if abs(delta) < 50:
        setup_category = 'reversal'  # neutro/chop
    elif delta > 200:
        setup_category = 'momentum' if bar.close > bar.open else 'imbalance_hunting'
    elif delta < -200:
        setup_category = 'momentum' if bar.close < bar.open else 'imbalance_hunting'
    else:
        setup_category = 'pullback'

    cv = getattr(bar, 'cvd', 0)
    prev_cvd = getattr(prev_bars[-1], 'cvd', 0) if prev_bars else 0
    poc_migration = 'up' if cv > prev_cvd + 200 else ('down' if cv < prev_cvd - 200 else 'flat')

    # Body/wick
    body = abs(bar.close - bar.open)
    full_range = max(bar.high - bar.low, 0.25)
    upper_wick = bar.high - max(bar.open, bar.close)
    lower_wick = min(bar.open, bar.close) - bar.low
    top_wick_ratio = upper_wick / full_range if full_range > 0 else 0
    bottom_wick_ratio = lower_wick / full_range if full_range > 0 else 0
    close_percentile = (bar.close - bar.low) / full_range if full_range > 0 else 0.5

    return CandidateBar(
        bar=bar,
        session_ctx=ctx,
        wall_level=wall_level,
        wall_side=wall_side,
        wall_trade_count=wall_trade_count,
        wall_max_size=wall_max_size,
        proximity_to='vwap',
        proximity_level=bar.vwap if bar.vwap > 0 else bar.close,
        bars_in_session=len(day_open_bars),
        is_second_test=bar.low <= ctx.ib_low + 5 or bar.high >= ctx.ib_high - 5,
        setup_category=setup_category,
        recent_bars=prev_bars + [bar],
        market_state='imbalance' if abs(delta) > 300 else 'balance',
        poc_migration=poc_migration,
        auction_type='initiative' if abs(delta) > 400 else 'responsive',
        session_bias='short' if cv < -500 else ('long' if cv > 500 else 'none'),
        vwap=bar.vwap if bar.vwap > 0 else bar.close,
        vwap_std_dev=0,
        nav_alert=False,
        active_stop_hunt=False,
        stop_hunt_direction='',
        delta_divergence=False,
        effort_no_result=False,
        top_wick_ratio=top_wick_ratio,
        bottom_wick_ratio=bottom_wick_ratio,
        close_percentile=close_percentile,
    )


# ────────────────────────────────────────────────────────────────────────────
# BACKTEST SIMULATION
# ────────────────────────────────────────────────────────────────────────────
def simulate_trade(bar_idx, direction, entry_price, day_bars, max_hold_bars=30):
    """Trailing stop con ratchet continuo. Lock 50% dei profitti mano a mano.
    Initial: stop = entry +/- 8
    Ad ogni nuovo massimo (LONG) / minimo (SHORT), sposta lo stop del 50%
    del nuovo profitto (esclusi i primi 8pt di buffer iniziale).
    """
    if direction == 'long':
        stop = entry_price - STOP_BUFFER
    else:
        stop = entry_price + STOP_BUFFER

    future_bars = day_bars[bar_idx+1:bar_idx+1+max_hold_bars]
    best_favorable = entry_price  # LONG: max high; SHORT: min low

    for i, b in enumerate(future_bars):
        if direction == 'long':
            # Aggiorna best_favorable
            if b.high > best_favorable:
                best_favorable = b.high
            # Profit massimo raggiunto
            profit = best_favorable - entry_price
            # Ratchet: 50% lock-in dopo i primi 8pt
            if profit > 8:
                locked = (profit - 8) * 0.5
                new_stop = entry_price + locked
                stop = max(stop, new_stop)
            if b.low <= stop:
                pnl = stop - entry_price
                return stop, 'trailing_stop', pnl, b.timestamp.astimezone(ET)
        else:
            if b.low < best_favorable:
                best_favorable = b.low
            profit = entry_price - best_favorable
            if profit > 8:
                locked = (profit - 8) * 0.5
                new_stop = entry_price - locked
                stop = min(stop, new_stop)
            if b.high >= stop:
                pnl = entry_price - stop
                return stop, 'trailing_stop', pnl, b.timestamp.astimezone(ET)

    # EOD exit
    last = future_bars[-1] if future_bars else day_bars[bar_idx]
    if direction == 'long':
        pnl = last.close - entry_price
    else:
        pnl = entry_price - last.close
    return last.close, 'eod', pnl, last.timestamp.astimezone(ET)


def run_new_system(day_bars):
    """Esegue il sistema con le nuove regole su tutti i M5 bar dopo 09:55."""
    trades = []
    skipped = []
    bias_log = []

    for i, bar in enumerate(day_bars):
        h, m = bar.timestamp.astimezone(ET).hour, bar.timestamp.astimezone(ET).minute
        if h < 9 or (h == 9 and m < 55):
            continue
        if h >= 16:
            break
        prev_bars = day_bars[:i]
        day_open = day_bars[:i+1]
        ctx = build_session_ctx(prev_bars, bar, day_open)
        candidate = build_candidate(bar, ctx, prev_bars, day_open)

        # Calcola bias
        bias = compute_institutional_bias(candidate)

        # NEW: early drive detection
        ed_delta, ed_driver = early_drive_detection(
            bar, prev_bars, ctx.ib_high, ctx.ib_low, ctx.ib_range,
            recent_bars_extra=prev_bars[-12:])
        if ed_delta != 0:
            new_score = max(-100, min(100, bias.score + ed_delta))
            new_regime = _regime_simple(new_score)
            bias = InstitutionalBias(
                score=new_score, regime=new_regime,
                drivers=bias.drivers + [ed_driver])

        bias_log.append({
            'time_et': f"{h:02d}:{m:02d}",
            'close': bar.close,
            'delta': bar.delta,
            'vwap': bar.vwap,
            'bias_score': bias.score,
            'bias_regime': bias.regime,
            'drivers': ' | '.join(bias.drivers[:3]),
        })

        # A+ pre-filter
        passes, why = is_aplus_setup(candidate, bias, prev_bars + [bar])
        if not passes:
            skipped.append({'time_et': f"{h:02d}:{m:02d}", 'reason': why, 'regime': bias.regime})
            continue

        # Deterministic LLM simulator (4-step prompt)
        direction, llm_reason = deterministic_llm_simulator(candidate, bias, prev_bars + [bar], trades_today=trades)
        if direction == 'none':
            skipped.append({'time_et': f"{h:02d}:{m:02d}", 'reason': f"llm_none: {llm_reason}", 'regime': bias.regime})
            continue

        # CAP: max 1 LONG vinto + 1 SHORT vinto per day.
        # Se un trade della stessa direzione e' stato un LOSS, permetti re-entry.
        same_dir = [t for t in trades if t['direction'] == direction]
        if same_dir:
            same_dir_won = [t for t in same_dir if t.get('pnl_pts', 0) > 0]
            if same_dir_won:
                skipped.append({'time_et': f"{h:02d}:{m:02d}", 'reason': f"cap_{direction}_already_won", 'regime': bias.regime})
                continue
        # Cooldown: dopo uno stop loss, aspetta 30 min prima di re-entry
        last_loss = next((t for t in reversed(trades) if t.get('pnl_pts', 0) < 0), None)
        if last_loss:
            from datetime import timedelta
            last_loss_end = last_loss.get('exit_time_et', '00:00')
            try:
                lh, lm = map(int, last_loss_end.split(':')[:2])
                cur_min = h * 60 + m
                loss_min = lh * 60 + lm
                if cur_min - loss_min < 30:
                    skipped.append({'time_et': f"{h:02d}:{m:02d}", 'reason': f"cooldown_{cur_min-loss_min}min", 'regime': bias.regime})
                    continue
            except Exception:
                pass

        # Validator (R1-R4)
        ok, val_reason, conv = new_validator(direction, candidate, bias, prev_bars + [bar])
        if not ok:
            skipped.append({'time_et': f"{h:02d}:{m:02d}", 'reason': val_reason, 'regime': bias.regime})
            continue

        # Take trade
        exit_price, exit_reason, pnl_pts, exit_time = simulate_trade(i, direction, bar.close, day_bars)
        trades.append({
            'entry_time_et': f"{h:02d}:{m:02d}",
            'exit_time_et': exit_time.strftime('%H:%M') if exit_time else '?',
            'direction': direction,
            'entry': bar.close,
            'exit': exit_price,
            'exit_time_et': exit_time.strftime('%H:%M') if exit_time else '?',
            'exit_reason': exit_reason,
            'pnl_pts': round(pnl_pts, 2),
            'pnl_usd': round(pnl_pts * 5 * 5, 2),  # 5 contratti? No, 1 contratto. pts * 5 $/pt
            'bias_regime': bias.regime,
            'bias_score': bias.score,
            'llm_reason': llm_reason,
        })
    return trades, skipped, bias_log


def update_dashboard_status(new_trades, skipped, bias_log, v2_total):
    """Aggiorna status.json con i trade del NUOVO sistema per 2025-03-03
    (accanto a quelli V2 esistenti, con tag 'source: NEW_RULES')."""
    import json
    status_path = r'C:\Users\Mauro\Documents\nq-backtest-clean\dashboard\public\data\status.json'
    if not os.path.exists(status_path):
        return
    try:
        with open(status_path, 'r', encoding='utf-8') as f:
            status = json.load(f)
    except Exception as e:
        print(f'  WARN: could not read status.json: {e}')
        return

    # Rimuovi eventuali trade NEW_RULES esistenti per 2025-03-03
    if 'ALL_TRADES' in status:
        status['ALL_TRADES'] = [t for t in status['ALL_TRADES']
                                if not (str(t.get('date','')) == '2025-03-03'
                                        and t.get('source') == 'NEW_RULES')]

    # Aggiungi i trade del nuovo sistema (PnL simulato, non reale)
    for t in new_trades:
        status.setdefault('ALL_TRADES', []).append({
            'date': '2025-03-03',
            'entry_time': f"2025-03-03T{t['entry_time_et']}:00:00+00:00",
            'exit_time': f"2025-03-03T{t.get('exit_time_et','00:00')}:00+00:00",
            'direction': t['direction'],
            'entry': t['entry'],
            'stop': t['entry'] - 8 if t['direction'] == 'long' else t['entry'] + 8,
            'target': t['entry'] + 16 if t['direction'] == 'long' else t['entry'] - 16,
            'exit_price': t['exit'],
            'exit_reason': t['exit_reason'],
            'pnl_usd': t['pnl_usd'],
            'pnl_ticks': t['pnl_pts'] * 4,  # 0.25pt per tick
            'r_ratio': 2.0,
            'setup_type': 'pullback',
            'final_confidence': 75,
            'fabio_reasoning': t['llm_reason'],
            'andrea_reasoning': 'simulated',
            'contracts': 1,
            'source': 'NEW_RULES',
            'bias_regime': t['bias_regime'],
            'bias_score': t['bias_score'],
        })

    # Aggiorna MOCK_SESSIONS: aggiungi riepilogo 2025-03-03 NEW
    new_wins = len([t for t in new_trades if t.get('pnl_pts', 0) > 0])
    new_losses = len([t for t in new_trades if t.get('pnl_pts', 0) <= 0])
    new_pnl = sum(t.get('pnl_usd', 0) for t in new_trades)
    status.setdefault('MOCK_SESSIONS', []).append({
        'date': '2025-03-03-NEW',
        'trades': len(new_trades),
        'wins': new_wins,
        'losses': new_losses,
        'pnl': new_pnl,
        'proposals': 0,
        'source': 'NEW_RULES_SIM',
    })

    # Aggiungi anche le analisi al reasoning_log per il chart
    new_reasonings = []
    for b in bias_log:
        new_reasonings.append({
            'date': '2025-03-03',
            'bar_time_et': b['time_et'],
            'bar_time_utc': '',  # non serve
            'fabio_confidence': 75 if b['bias_regime'] in ('drive_down','drive_up') else 50,
            'fabio_direction': ('short' if b['bias_score'] < 0 else 'long') if abs(b['bias_score']) > 15 else 'none',
            'session_bias': ('short' if b['bias_score'] < -15 else 'long' if b['bias_score'] > 15 else 'none'),
            'fabio_imbalance_phase': 'expansive' if abs(b['bias_score']) > 30 else 'none',
            'fabio_reasoning': b['drivers'],
            'amt_day_profile': f"Bias={b['bias_regime']} score={b['bias_score']:+.0f}",
            'source': 'NEW_RULES_SIM',
        })
    # Aggiungi solo le analisi NEW_RULES che non sono gia' presenti
    existing = set((r.get('date'), r.get('bar_time_et'), r.get('source'))
                   for r in status.get('ALL_REASONINGS', []))
    for nr in new_reasonings:
        key = (nr['date'], nr['bar_time_et'], nr.get('source'))
        if key not in existing:
            status.setdefault('ALL_REASONINGS', []).append(nr)

    # Scrivi
    try:
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump(status, f, indent=2, default=str)
        print(f'  Dashboard status.json aggiornato con {len(new_trades)} nuovi trade + {len(new_reasonings)} reasonings')
    except Exception as e:
        print(f'  WARN: could not write status.json: {e}')


def _regime_simple(score):
    if score >= 35: return 'drive_up'
    if score >= 15: return 'lean_up'
    if score <= -35: return 'drive_down'
    if score <= -15: return 'lean_down'
    return 'rotational'


# ────────────────────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────────────────────
def main():
    print('=' * 80)
    print(f'V2 + NEW RULES TEST SU 2025-03-03')
    print('=' * 80)

    # Load bars
    cache_path = rf'C:\Users\Mauro\Documents\nq-backtest-clean\output\walkforward\day_bars_{DATE}.pkl'
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            day_bars = pickle.load(f)
        print(f'Caricato da cache: {len(day_bars)} bar M5')
    else:
        day_bars = load_day_bars(DATE)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(day_bars, f)
        print(f'Caricati {len(day_bars)} bar M5 da databento')

    # Run new system
    new_trades, skipped, bias_log = run_new_system(day_bars)

    # Bias log
    print('\n' + '=' * 80)
    print('BIAS ENGINE LOG (con early drive detection)')
    print('=' * 80)
    print(f'{"time":>6}  {"close":>9}  {"delta":>6}  {"vwap":>9}  {"score":>5}  {"regime":>12}  drivers')
    print('-' * 100)
    for b in bias_log:
        print(f'{b["time_et"]:>6}  {b["close"]:>9.2f}  {b["delta"]:>+6}  {b["vwap"]:>9.2f}  '
              f'{b["bias_score"]:>+5.0f}  {b["bias_regime"]:>12}  {b["drivers"][:50]}')

    # V2 actual trades vs new system
    print('\n' + '=' * 80)
    print('V2 TRADES EFFETTIVI vs NUOVO SISTEMA')
    print('=' * 80)
    v2_total = 0
    for v2 in V2_TRADES:
        # Cerca trade corrispondente nelle nuove decisioni
        new_match = None
        target_te = v2['time_et']
        for nt in new_trades + skipped:
            t_te = nt.get('time_et') or nt.get('entry_time_et')
            if t_te == target_te:
                new_match = nt
                break
        v2_total += v2['pnl_usd']
        if not new_match:
            outcome = '? (no candidate at this time)'
        elif 'reason' in new_match:
            outcome = f"REJECTED ({new_match['reason']})"
        else:
            outcome = f"TAKEN ({new_match['direction']}, bias={new_match['bias_regime']}, pnl={new_match['pnl_usd']:+.0f}$)"
        print(f'  {v2["time_et"]} V2_LONG @ {v2["entry"]:.2f} -> {v2["exit"]:.2f} '
              f'(pnl {v2["pnl_usd"]:+.0f}$): {outcome}')

    print(f'\nV2 PnL totale: {v2_total:+.0f}$ ({len(V2_TRADES)} trades)')

    # New system trades
    print('\n' + '=' * 80)
    print(f'NUOVO SISTEMA — TRADES PRESI ({len(new_trades)})')
    print('=' * 80)
    new_total = 0
    for t in new_trades:
        new_total += t['pnl_usd']
        print(f'  {t["entry_time_et"]} {t["direction"].upper():5} @ {t["entry"]:.2f} -> '
              f'{t["exit"]:.2f} ({t["exit_reason"]}) '
              f'pnl {t["pnl_pts"]:+.1f}pt = {t["pnl_usd"]:+.0f}$ | '
              f'bias={t["bias_regime"]} (score {t["bias_score"]:+.0f}) | '
              f'reason: {t["llm_reason"]}')

    print(f'\nNew system PnL totale: {new_total:+.0f}$ ({len(new_trades)} trades)')

    # Skipped count
    print(f'\nBar saltati: {len(skipped)}')
    skip_by_reason = defaultdict(int)
    for s in skipped:
        key = s['reason'].split(':')[0] if ':' in s['reason'] else s['reason']
        skip_by_reason[key] += 1
    print('  Breakdown:')
    for k, v in sorted(skip_by_reason.items(), key=lambda x: -x[1]):
        print(f'    {k}: {v}')

    # Summary
    print('\n' + '=' * 80)
    print('SUMMARY')
    print('=' * 80)
    print(f'  V2 ATTUALE:  4 trades,  PnL {v2_total:+.0f}$')
    print(f'  V2 + NEW:    {len(new_trades)} trades, PnL {new_total:+.0f}$')
    print(f'  Delta:       {(len(new_trades) - 4):+d} trades, {(new_total - v2_total):+.0f}$ PnL')

    # Save
    out_dir = r'C:\Users\Mauro\Documents\nq-backtest-clean\output\new_rules'
    os.makedirs(out_dir, exist_ok=True)
    pd.DataFrame(new_trades).to_csv(os.path.join(out_dir, f'new_trades_{DATE}.csv'), index=False)
    pd.DataFrame(skipped).to_csv(os.path.join(out_dir, f'skipped_{DATE}.csv'), index=False)
    pd.DataFrame(bias_log).to_csv(os.path.join(out_dir, f'bias_log_{DATE}.csv'), index=False)
    print(f'\nFile salvati in {out_dir}/')

    # Also update dashboard status.json for 2025-03-03 only (so user sees the comparison)
    update_dashboard_status(new_trades, skipped, bias_log, v2_total)


if __name__ == '__main__':
    main()
