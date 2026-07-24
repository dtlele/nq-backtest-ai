"""Realistic walk-forward backtest using ACTUAL forward price action.

This is the honest version:
- For each day in OOS period, train RF on prior days
- Score each M5 bar of the day
- For each bar with score > threshold, ENTER at close
- Look at the next 6 M5 bars (30 min) of ACTUAL price action
- Determine PnL based on whether stop or target hit first
- Account for slippage

This requires re-aggregating the raw tick data to M5 bars + 30-min forward window.
"""
import os
import sys
import csv
import datetime as dt
from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# Use existing bar aggregator
sys.path.insert(0, r'C:\Users\Mauro\Documents\nq-backtest-clean')
from src.bar_aggregator import aggregate_to_bars
from src import Trade

import pytz
ET = pytz.timezone('America/New_York')
UTC = pytz.UTC

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'
CSV_FEATURES = r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml\features_230d.csv'
OUT_DIR = r'C:\Users\Mauro\Documents\nq-backtest-clean\output\walkforward'
os.makedirs(OUT_DIR, exist_ok=True)

# Config
MIN_TRAIN_DAYS = 30
RETRAIN_EVERY_DAYS = 5
THRESHOLDS = [0.6, 0.65, 0.7, 0.75, 0.8]
TRADES_PER_DAY_CAP = 5
STOP_PT = 8.0
TARGET_PT = 16.0
COST_PT = 0.5  # round-trip slippage + comm
MAX_HOLD_BARS = 6  # 30 min


def load_day_trades(date_str):
    """Load trades for a given date and convert to M5 bars + M1 bars."""
    path = os.path.join(DATA_DIR, f'glbx-mdp3-{date_str}.trades.csv')
    if not os.path.exists(path):
        return [], []
    trades = []
    try:
        with open(path) as f:
            r = csv.DictReader(f)
            for row in r:
                # Only NQ front month
                if 'NQ' not in row.get('symbol', ''):
                    continue
                ts_str = row['ts_event'].replace('Z', '+00:00')
                ts = dt.datetime.fromisoformat(ts_str)
                # Make tz-aware UTC
                if ts.tzinfo is None:
                    ts = UTC.localize(ts)
                price = float(row['price'])
                if price < 5000 or price > 50000:
                    continue
                trades.append(Trade(
                    ts_event=ts, price=price, size=int(row['size']),
                    side=row.get('side', 'A'),
                ))
    except Exception as e:
        return [], []
    if len(trades) < 100:
        return [], []
    bars_m5 = aggregate_to_bars(trades, freq='5min')
    return bars_m5, trades


def simulate_bar_entry(bar, future_bars, direction):
    """Simulate entering at bar close, with stop and target.

    direction: 'long' or 'short'
    Returns: pnl in points (positive = win, negative = loss, 0 = time stop at BE)
    """
    entry = bar.close
    if direction == 'long':
        stop = entry - STOP_PT
        target = entry + TARGET_PT
    else:
        stop = entry + STOP_PT
        target = entry - TARGET_PT

    for fb in future_bars[:MAX_HOLD_BARS]:
        if direction == 'long':
            # Check stop first (conservative — wick would be hit)
            if fb.low <= stop:
                return -STOP_PT - COST_PT
            if fb.high >= target:
                return TARGET_PT - COST_PT
        else:
            if fb.high >= stop:
                return -STOP_PT - COST_PT
            if fb.low <= target:
                return TARGET_PT - COST_PT
    # Time stop — exit at last close
    if future_bars:
        last_close = future_bars[min(MAX_HOLD_BARS - 1, len(future_bars) - 1)].close
        if direction == 'long':
            pnl = last_close - entry
        else:
            pnl = entry - last_close
        return pnl - COST_PT
    return 0


def main():
    print('=== WALK-FORWARD OOS: REALISTIC SIMULATION (230 days NQ M5) ===\n')
    df = pd.read_csv(CSV_FEATURES, dtype={'date': str})
    df = df.sort_values(['date', 'time_et']).reset_index(drop=True)
    feature_cols = [c for c in df.columns if c not in ('date', 'time_et', 'label')]
    dates = sorted(df.date.unique())
    print(f'Dates: {len(dates)}, training requires first {MIN_TRAIN_DAYS}+ days\n')

    # Pre-load M5 bars for all test days (so we can look forward)
    print('Pre-loading M5 bars for test days...')
    day_bars = {}
    test_dates = dates[MIN_TRAIN_DAYS:]
    for i, d in enumerate(test_dates):
        bars, _ = load_day_trades(d)
        # Filter RTH
        rth = [b for b in bars if 9 <= b.timestamp.astimezone(ET).hour < 16]
        # Index by timestamp for fast lookup
        day_bars[d] = rth
        if (i + 1) % 30 == 0:
            print(f'  Loaded {i+1}/{len(test_dates)} days')
    print(f'  Total: {len(day_bars)} days with bars\n')

    # Walk-forward
    oos_records = []
    model = None
    last_train_idx = -999

    for day_idx, day in enumerate(dates):
        if day_idx < MIN_TRAIN_DAYS:
            continue
        if day not in day_bars or not day_bars[day]:
            continue

        # Retrain
        if model is None or (day_idx - last_train_idx) >= RETRAIN_EVERY_DAYS:
            train_days = dates[max(0, day_idx - MIN_TRAIN_DAYS - 60):day_idx]
            train_mask = df.date.isin(train_days)
            Xtr = df.loc[train_mask, feature_cols].fillna(0).values
            ytr = df.loc[train_mask, 'label'].values
            if len(Xtr) < 1000:
                continue
            model = RandomForestClassifier(
                n_estimators=200, max_depth=8, min_samples_split=50,
                min_samples_leaf=20, max_features='sqrt', n_jobs=-1, random_state=42,
            )
            model.fit(Xtr, ytr)
            last_train_idx = day_idx

        # Score this day
        day_df = df[df.date == day].copy()
        if len(day_df) == 0:
            continue
        Xte = day_df[feature_cols].fillna(0).values
        proba = model.predict_proba(Xte)[:, 1]
        day_df = day_df.assign(score=proba)

        # Map features → bars
        bars = day_bars[day]
        bar_by_ts = {b.timestamp.replace(second=0, microsecond=0): b for b in bars}

        # For each bar, get future 6 bars
        for i, (_, row) in enumerate(day_df.iterrows()):
            # Reconstruct bar timestamp from time_et
            et_time = dt.datetime.strptime(row['time_et'], '%H:%M').time()
            et_dt = ET.localize(dt.datetime.combine(dt.datetime.strptime(day, '%Y%m%d').date(), et_time))
            # Round to 5min
            minute = (et_dt.minute // 5) * 5
            et_dt = et_dt.replace(minute=minute, second=0, microsecond=0)
            bar_ts = et_dt.astimezone(UTC).replace(second=0, microsecond=0)
            cur_bar = bar_by_ts.get(bar_ts)
            if not cur_bar:
                continue
            # Find this bar's index in bars list
            try:
                cur_idx = bars.index(cur_bar)
            except ValueError:
                continue
            future = bars[cur_idx + 1:cur_idx + 1 + MAX_HOLD_BARS]
            oos_records.append({
                'date': day, 'time_et': row['time_et'],
                'close': row['close'], 'net': row['net'],
                'label': row['label'], 'score': row['score'],
                'bar_idx': cur_idx,
            })

    oos = pd.DataFrame(oos_records)
    print(f'OOS bars: {len(oos)} across {oos.date.nunique()} days')
    print(f'Base label WIN rate: {oos.label.mean():.3f}\n')

    # === SIMULATED TRADING ===
    print(f'Assumptions: stop={STOP_PT}pt, target={TARGET_PT}pt, cost={COST_PT}pt, max hold={MAX_HOLD_BARS*5}min')
    print(f'{"thresh":>7}  {"n":>5}  {"WR":>6}  {"totPnL":>8}  {"avg":>7}  {"Sharpe":>7}  {"maxDD":>7}  {"days>0":>7}')
    print('-' * 80)

    for th in THRESHOLDS:
        trades = []
        for day, day_df in oos.groupby('date'):
            cand = day_df[day_df.score > th].sort_values('score', ascending=False).head(TRADES_PER_DAY_CAP)
            for _, r in cand.iterrows():
                # Direction from net
                if r['net'] > 0:
                    direction = 'long'
                elif r['net'] < 0:
                    direction = 'short'
                else:
                    continue
                # Get bar
                bars = day_bars.get(day, [])
                if r['bar_idx'] >= len(bars):
                    continue
                cur_bar = bars[r['bar_idx']]
                future = bars[r['bar_idx'] + 1:r['bar_idx'] + 1 + MAX_HOLD_BARS]
                pnl = simulate_bar_entry(cur_bar, future, direction)
                trades.append({'date': day, 'time_et': r['time_et'], 'pnl': pnl,
                              'label': r['label'], 'score': r['score']})
        if not trades:
            print(f'{th:>7.2f}  no trades')
            continue
        tdf = pd.DataFrame(trades)
        wins = (tdf.pnl > 0).sum()
        wr = wins / len(tdf)
        total = tdf.pnl.sum()
        avg = tdf.pnl.mean()
        std = tdf.pnl.std()
        sharpe = (avg / std) * np.sqrt(252) if std > 0 else 0
        cum = tdf.pnl.cumsum()
        dd = (cum - cum.cummax()).min()
        n_days_pos = (tdf.groupby('date').pnl.sum() > 0).sum()
        n_days = tdf.date.nunique()
        print(f'{th:>7.2f}  {len(tdf):>5}  {wr:>6.1%}  {total:>+8.0f}  {avg:>+7.2f}  {sharpe:>7.2f}  {dd:>7.1f}  {n_days_pos}/{n_days}')

    # === BASELINE: NO FILTER, but only bars with non-zero net ===
    print('\n=== BASELINE: NO FILTER (all bars with direction) ===')
    base_trades = []
    for day, day_df in oos.groupby('date'):
        for _, r in day_df.iterrows():
            if r['net'] > 0:
                direction = 'long'
            elif r['net'] < 0:
                direction = 'short'
            else:
                continue
            bars = day_bars.get(day, [])
            if r['bar_idx'] >= len(bars):
                continue
            cur_bar = bars[r['bar_idx']]
            future = bars[r['bar_idx'] + 1:r['bar_idx'] + 1 + MAX_HOLD_BARS]
            pnl = simulate_bar_entry(cur_bar, future, direction)
            base_trades.append({'date': day, 'pnl': pnl})
    bdf = pd.DataFrame(base_trades)
    if len(bdf) > 0:
        wins = (bdf.pnl > 0).sum()
        wr = wins / len(bdf)
        total = bdf.pnl.sum()
        avg = bdf.pnl.mean()
        std = bdf.pnl.std()
        sharpe = (avg / std) * np.sqrt(252) if std > 0 else 0
        cum = bdf.pnl.cumsum()
        dd = (cum - cum.cummax()).min()
        n_days = bdf.date.nunique()
        n_days_pos = (bdf.groupby('date').pnl.sum() > 0).sum()
        print(f'  n: {len(bdf)} ({len(bdf)/n_days:.1f}/day), WR: {wr:.1%}, total: {total:+.0f}pt, avg: {avg:+.2f}pt')
        print(f'  Sharpe: {sharpe:.2f}, MaxDD: {dd:.1f}pt, days>0: {n_days_pos}/{n_days}')


if __name__ == '__main__':
    main()
