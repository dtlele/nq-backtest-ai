"""V2 audit simulator — deterministic, runs the V2 audit rules on real M5 bars.

For each M5 bar in features_230d:
  1. Load the bar (incl. big_trades with side)
  2. Compute a SIMPLIFIED institutional bias (since we don't have the full ctx)
  3. Apply V2 audit rules R1-R6 to decide confirm/reject
  4. Compare to actual V8b trades (3 specific bars)

This is a SHADOW test of the V2 audit — no LLM calls, fully reproducible.
"""
import os
import sys
import csv
import datetime as dt
from collections import defaultdict
import numpy as np
import pandas as pd

sys.path.insert(0, r'C:\Users\Mauro\Documents\nq-backtest-clean')
from src.bar_aggregator import aggregate_to_bars
from src import Trade
import pytz

ET = pytz.timezone('America/New_York')
UTC = pytz.UTC
DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'
CSV_FEATURES = r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml\features_230d.csv'
NQ_BIG_TRADE_THRESHOLD = 50  # Same as bar_aggregator default

# V2 audit thresholds (from docs/AUDIT_PROMPT_V2.md, RELAXED after V8b shadow test)
# Relaxed from initial: ±300/±800 -> ±500/±1500. Rationale: failed-push absorption
# patterns (e.g. 11 Feb 10:50 LONG) can have large opposite delta by design.
R1_DELTA_INSTANT = 500      # bar.delta > +500 and direction=short -> REJECT (and reverse)
R1_CV_DELTA = 1500          # cv_delta_30m > +1500 and direction=short -> REJECT
R1_WICK_EXCEPTION_RATIO = 1.5  # upper_wick/body > 1.5 (failed push for longs)
R3_BIG_TRADES_WRONG_SIDE = 2  # >= 2 Big Trades on wrong side -> REJECT
R3_BIG_TRADE_TOTAL_SIZE = 150  # 1 single huge Big Trade (size>=150) on wrong side -> REJECT
R4_BIAS_THRESHOLD = 30      # |bias_score| >= 30 = drive, can't counter-trend without reversal
R5_OPEN_NO_TRADE_MINUTES = (9 * 60 + 30, 9 * 60 + 45)  # 9:30-9:45 ET opening rotation
R5_LATE_ET_MINUTES = 15 * 60 + 15  # 15:15 ET

# V8b trade IDs (date, time, expected ML direction, expected outcome)
V8B_TRADES = [
    ('20250204', '12:25', 'short', 'stop'),     # SHORT 21555 → -$50
    ('20250211', '09:35', 'long',  'be'),       # LONG 21781.75 → BE
    ('20250211', '10:50', 'long',  'win'),      # LONG 21867.50 → +$766
]


def load_day_bars(date_str):
    """Load M5 bars with full big_trades list."""
    path = os.path.join(DATA_DIR, f'glbx-mdp3-{date_str}.trades.csv')
    if not os.path.exists(path):
        return []
    trades = []
    try:
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
    except Exception:
        return []
    if len(trades) < 100:
        return []
    bars = aggregate_to_bars(trades, freq='5min')
    rth = [b for b in bars if 9 <= b.timestamp.astimezone(ET).hour < 16]
    return rth


def compute_big_trades_by_side(bar, threshold=NQ_BIG_TRADE_THRESHOLD):
    """Count big trades on each side for a single M5 bar."""
    buys = 0  # 'A' = lift/buy
    sells = 0  # 'B' = hit/sell
    buy_size = 0
    sell_size = 0
    for t in (bar.big_trades or []):
        if t.size >= threshold:
            if t.side == 'A':
                buys += 1
                buy_size += t.size
            elif t.side == 'B':
                sells += 1
                sell_size += t.size
    return {'buy_n': buys, 'sell_n': sells, 'buy_size': buy_size, 'sell_size': sell_size}


def compute_simplified_bias(bar, prev_bars, day_open_bars, dist_ib_high, dist_ib_low, ib_range, dist_vwap_pct):
    """Compute a simplified institutional bias using features available in the bar.

    Mirrors src/agents/institutional_bias.py but uses only bar-level features.
    """
    score = 0.0
    drivers = []

    # 1. IB extension
    if ib_range > 0:
        if dist_ib_high > 0.5 * ib_range:
            score += 30
            drivers.append(f"DRIVE: close {dist_ib_high:.0f}pt above IB_high")
        elif dist_ib_high > 0:
            score += 12
            drivers.append(f"above IB_high by {dist_ib_high:.0f}pt")
        elif dist_ib_low > 0.5 * ib_range:
            score -= 30
            drivers.append(f"DRIVE: close {dist_ib_low:.0f}pt below IB_low")
        elif dist_ib_low > 0:
            score -= 12
            drivers.append(f"below IB_low by {dist_ib_low:.0f}pt")

    # 2. POC migration proxy: compare last 3 bars' midpoints
    if len(prev_bars) >= 3:
        prev_mid = (prev_bars[-3].high + prev_bars[-3].low) / 2
        cur_mid = (bar.high + bar.low) / 2
        if cur_mid > prev_mid + 5:
            score += 15
            drivers.append("POC migration UP")
        elif cur_mid < prev_mid - 5:
            score -= 15
            drivers.append("POC migration DOWN")

    # 3. VWAP position
    if dist_vwap_pct > 0.05:
        score += 8
        drivers.append(f"above VWAP by {dist_vwap_pct:.2f}%")
    elif dist_vwap_pct < -0.05:
        score -= 8
        drivers.append(f"below VWAP by {abs(dist_vwap_pct):.2f}%")

    # 4. Day open comparison (proxy for prev day VA)
    if day_open_bars:
        day_open = day_open_bars[0].open
        if bar.close > day_open * 1.002:  # +0.2% above open
            score += 10
            drivers.append("accepting above day open")
        elif bar.close < day_open * 0.998:
            score -= 10
            drivers.append("accepting below day open")

    # 5. Delta recent (6 bars)
    if len(prev_bars) >= 6:
        dsum = sum(b.delta for b in prev_bars[-6:])
        if abs(dsum) >= 300:
            contrib = max(-12, min(12, dsum / 100))
            score += contrib
            drivers.append(f"delta last 6 bars: {dsum:+d}")

    return max(-100.0, min(100.0, score)), drivers


def get_regime(bias_score):
    if bias_score >= 35: return 'drive_up'
    if bias_score >= 15: return 'lean_up'
    if bias_score <= -35: return 'drive_down'
    if bias_score <= -15: return 'lean_down'
    return 'rotational'


def apply_v2_audit(bar, prev_bars, day_open_bars, features_row, direction):
    """Apply V2 audit rules. Returns (verdict, rule_violated, reason).

    direction: 'long' or 'short' (the LLM's proposed direction)
    """
    if direction not in ('long', 'short'):
        return 'confirm', 'none', 'no direction'

    delta = bar.delta
    cv_delta = features_row.get('cv_delta_30m', 0) or 0
    tod = features_row.get('tod', 0)
    dist_ib_high = features_row.get('dist_ib_high', 0) or 0
    dist_ib_low = features_row.get('dist_ib_low', 0) or 0
    ib_range = 0  # can't compute from features alone
    dist_vwap_pct = features_row.get('dist_vwap_pct', 0) or 0
    big = compute_big_trades_by_side(bar)
    score, drivers = compute_simplified_bias(
        bar, prev_bars, day_open_bars, dist_ib_high, dist_ib_low, ib_range, dist_vwap_pct)
    regime = get_regime(score)

    # Failed-push absorption exception (BEFORE R1 check):
    # Long with big upper wick = failed push, sellers exhausted, OK to fade sellers.
    # Short with big lower wick = failed breakdown, buyers exhausted, OK to fade buyers.
    upper_wick = bar.high - max(bar.open, bar.close)
    lower_wick = min(bar.open, bar.close) - bar.low
    body = abs(bar.close - bar.open)
    is_failed_push_long = upper_wick > R1_WICK_EXCEPTION_RATIO * max(body, 5.0)
    is_failed_push_short = lower_wick > R1_WICK_EXCEPTION_RATIO * max(body, 5.0)
    wick_exception = (direction == 'long' and is_failed_push_long) or \
                     (direction == 'short' and is_failed_push_short)

    # R1: delta opposes direction (with wick exception)
    if not wick_exception:
        if direction == 'short' and delta >= R1_DELTA_INSTANT:
            return 'reject', 'R1', f'delta={delta:+d} >= +{R1_DELTA_INSTANT} opposes short'
        if direction == 'short' and cv_delta >= R1_CV_DELTA:
            return 'reject', 'R1', f'cv_delta_30m={cv_delta:+d} >= +{R1_CV_DELTA} opposes short'
        if direction == 'long' and delta <= -R1_DELTA_INSTANT:
            return 'reject', 'R1', f'delta={delta:+d} <= -{R1_DELTA_INSTANT} opposes long'
        if direction == 'long' and cv_delta <= -R1_CV_DELTA:
            return 'reject', 'R1', f'cv_delta_30m={cv_delta:+d} <= -{R1_CV_DELTA} opposes long'

    # R3: big trades on wrong side (with wick exception)
    if not wick_exception:
        if direction == 'long' and big['sell_n'] >= R3_BIG_TRADES_WRONG_SIDE:
            return 'reject', 'R3', f'{big["sell_n"]} Big SELL trades (size>={NQ_BIG_TRADE_THRESHOLD}) oppose long'
        if direction == 'short' and big['buy_n'] >= R3_BIG_TRADES_WRONG_SIDE:
            return 'reject', 'R3', f'{big["buy_n"]} Big BUY trades oppose short'
        # R3b: single HUGE Big Trade (>=150) on wrong side is also a veto
        if direction == 'long' and big['sell_size'] >= R3_BIG_TRADE_TOTAL_SIZE:
            return 'reject', 'R3', f'Big SELL block ({big["sell_size"]} contracts) opposes long'
        if direction == 'short' and big['buy_size'] >= R3_BIG_TRADE_TOTAL_SIZE:
            return 'reject', 'R3', f'Big BUY block ({big["buy_size"]} contracts) opposes short'

    # R4: counter-trend against drive without reversal setup
    if abs(score) >= R4_BIAS_THRESHOLD and regime in ('drive_up', 'drive_down'):
        if regime == 'drive_up' and direction == 'short':
            return 'reject', 'R4', f'counter-trend against drive_up (score={score:+.0f}), no reversal setup'
        if regime == 'drive_down' and direction == 'long':
            return 'reject', 'R4', f'counter-trend against drive_down (score={score:+.0f}), no reversal setup'

    # R5: time-of-day risk (9:30-9:45 opening rotation)
    hour = int(tod)
    minute = int((tod - hour) * 60)
    et_minutes = hour * 60 + minute
    if R5_OPEN_NO_TRADE_MINUTES[0] <= et_minutes < R5_OPEN_NO_TRADE_MINUTES[1]:
        return 'reject', 'R5', f'opening rotation 9:30-9:45 ET (TOD={tod:.2f})'

    # Confirm if we got here
    wick_note = ' (wick-absorption exception applied)' if wick_exception else ''
    return 'confirm', 'none', f'score={score:+.0f} regime={regime}{wick_note} | ' + '; '.join(drivers[:2])


def main():
    print('=== V2 AUDIT SIMULATOR (DETERMINISTIC, OFFLINE) ===\n')
    df = pd.read_csv(CSV_FEATURES, dtype={'date': str})
    df = df.sort_values(['date', 'time_et']).reset_index(drop=True)
    print(f'Loaded {len(df)} M5 bars across {df.date.nunique()} days\n')

    # Run audit on every bar that has ML score > 0.5
    import joblib
    bundle = joblib.load(r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml\rf_v1.pkl')
    model = bundle['model']
    feats = bundle['feature_cols']
    df['score'] = model.predict_proba(df[feats].fillna(0).values)[:, 1]

    # Cache M5 bars by date
    print('Loading M5 bars with big_trades...')
    cache_path = r'C:\Users\Mauro\Documents\nq-backtest-clean\output\walkforward\day_bars_cache.pkl'
    if os.path.exists(cache_path):
        import pickle
        with open(cache_path, 'rb') as f:
            day_bars = pickle.load(f)
        print(f'  Loaded from cache: {len(day_bars)} days')
    else:
        day_bars = {}
        test_dates = sorted(df.date.unique())
        for i, d in enumerate(test_dates):
            day_bars[d] = load_day_bars(d)
            if (i + 1) % 30 == 0:
                print(f'  {i+1}/{len(test_dates)} days loaded')
        print(f'  Done: {sum(1 for v in day_bars.values() if v)}/{len(test_dates)} days with bars')
        import pickle
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'wb') as f:
            pickle.dump(day_bars, f)
        print(f'  Cached to {cache_path}')
    print()

    # Build index: date+time -> bar
    bar_lookup = {}
    for d, bars in day_bars.items():
        for b in bars:
            ts = b.timestamp.astimezone(UTC).replace(minute=(b.timestamp.minute // 5) * 5, second=0, microsecond=0)
            bar_lookup[(d, ts)] = b

    # Run V2 audit on all score>0.5 bars
    print('=== V2 AUDIT RESULTS — ALL score>0.5 BARS ===\n')
    print(f'{"date":>10}  {"time":>6}  {"close":>8}  {"delta":>6}  {"cv_d30":>7}  {"bias":>5}  {"dir":>5}  {"verdict":>8}  {"rule":>5}')
    print('-' * 90)

    audit_results = []
    for _, row in df.iterrows():
        if row.score <= 0.5:
            continue
        d = row['date']
        t = row['time_et']
        # Find bar
        try:
            et_time = dt.datetime.strptime(t, '%H:%M').time()
            et_dt = ET.localize(dt.datetime.combine(
                dt.datetime.strptime(d, '%Y%m%d').date(), et_time))
            minute = (et_dt.minute // 5) * 5
            et_dt = et_dt.replace(minute=minute, second=0, microsecond=0)
            bar_ts = et_dt.astimezone(UTC).replace(second=0, microsecond=0)
            bar = bar_lookup.get((d, bar_ts))
        except Exception:
            continue
        if not bar:
            continue
        # Direction from net (LLM proxy)
        direction = 'long' if row['net'] > 0 else ('short' if row['net'] < 0 else None)
        if not direction:
            continue
        # Prev bars
        bars_today = day_bars.get(d, [])
        try:
            cur_idx = bars_today.index(bar)
        except ValueError:
            continue
        prev_bars = bars_today[:cur_idx]
        day_open = bars_today[:cur_idx + 1]

        verdict, rule, reason = apply_v2_audit(bar, prev_bars, day_open, row, direction)
        audit_results.append({
            'date': d, 'time_et': t, 'close': bar.close, 'delta': bar.delta,
            'cv_delta_30m': row.get('cv_delta_30m', 0), 'score': row.score,
            'direction': direction, 'verdict': verdict, 'rule': rule, 'reason': reason,
            'label': row['label'],
        })

    adf = pd.DataFrame(audit_results)
    print(f'Total audited bars (score>0.5): {len(adf)}')
    print(f'  CONFIRMED: {(adf.verdict == "confirm").sum()} ({(adf.verdict == "confirm").mean():.1%})')
    print(f'  REJECTED:  {(adf.verdict == "reject").sum()} ({(adf.verdict == "reject").mean():.1%})')
    print()

    # Reject breakdown
    print('=== REJECT RULES BREAKDOWN ===')
    rej = adf[adf.verdict == 'reject']
    print(rej.groupby('rule').size().to_string())
    print()

    # V8b-specific: what would V2 do for the 3 V8b trades?
    print('=== V8b TRADES — V2 AUDIT VERDICT ===')
    for v8b_date, v8b_time, expected_dir, outcome in V8B_TRADES:
        match = adf[(adf.date == v8b_date) & (adf.time_et == v8b_time)]
        if len(match) == 0:
            print(f'  {v8b_date} {v8b_time} ({expected_dir} → {outcome}): NOT FOUND in audit (score<=0.5?)')
        else:
            m = match.iloc[0]
            ok = '✓' if (m.verdict == 'reject' and outcome == 'stop') or (m.verdict == 'confirm' and outcome in ('win', 'be')) else '?'
            print(f'  {v8b_date} {v8b_time} ({expected_dir} → {outcome}): {m.verdict.upper()} ({m.rule}) {ok}')
            print(f'      reason: {m.reason}')

    print()

    # Save
    out = r'C:\Users\Mauro\Documents\nq-backtest-clean\output\walkforward\audit_v2_results.csv'
    adf.to_csv(out, index=False)
    print(f'Full results saved: {out}')


if __name__ == '__main__':
    main()
