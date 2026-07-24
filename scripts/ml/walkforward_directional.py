"""Honest walk-forward: measure if ML filter predicts ACTUAL price moves.

Strategy:
- Filter: take only bars with score > threshold
- For each filtered bar, measure the ACTUAL next 30-min range from M5 OHLC
- Compare hit rate vs base rate
- This is the cleanest test of "does the model predict tradeable moves?"

Plus a second test:
- Direction-AGNOSTIC: did the next 30 min have 16+ pt move in EITHER direction?
- This is the realistic PnL test: if we'd entered at close with 8pt stop / 16pt target
  using the FAVORABLE direction, did we hit target?
"""
import os
import sys
import csv
import datetime as _dt
from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

sys.path.insert(0, r'C:\Users\Mauro\Documents\nq-backtest-clean')
from src.bar_aggregator import aggregate_to_bars
from src import Trade
import pytz
import datetime as dt

ET = pytz.timezone('America/New_York')
UTC = pytz.UTC
DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'
CSV_FEATURES = r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml\features_230d.csv'
OUT_DIR = r'C:\Users\Mauro\Documents\nq-backtest-clean\output\walkforward'
os.makedirs(OUT_DIR, exist_ok=True)

MIN_TRAIN_DAYS = 30
RETRAIN_EVERY_DAYS = 5
THRESHOLDS = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]
MAX_HOLD_BARS = 6
STOP_PT = 8.0
TARGET_PT = 16.0
COST_PT = 0.5


def load_day_bars(date_str):
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


def main():
    print('=== HONEST WALK-FORWARD: PREDICTING ACTUAL MOVES ===\n')
    df = pd.read_csv(CSV_FEATURES, dtype={'date': str})
    df = df.sort_values(['date', 'time_et']).reset_index(drop=True)
    feature_cols = [c for c in df.columns if c not in ('date', 'time_et', 'label')]
    dates = sorted(df.date.unique())
    print(f'Dates: {len(dates)}, training requires first {MIN_TRAIN_DAYS}+ days\n')

    print('Pre-loading M5 bars for OOS period...')
    day_bars = {}
    test_dates = dates[MIN_TRAIN_DAYS:]
    for i, d in enumerate(test_dates):
        day_bars[d] = load_day_bars(d)
    print(f'  Loaded {sum(1 for v in day_bars.values() if v)}/{len(test_dates)} days\n')

    # Walk-forward
    oos_records = []
    model = None
    last_train_idx = -999

    for day_idx, day in enumerate(dates):
        if day_idx < MIN_TRAIN_DAYS:
            continue
        if not day_bars.get(day):
            continue

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

        day_df = df[df.date == day].copy()
        Xte = day_df[feature_cols].fillna(0).values
        proba = model.predict_proba(Xte)[:, 1]
        day_df = day_df.assign(score=proba)

        bars = day_bars[day]
        # Map by 5-min rounded timestamp
        bar_by_ts = {}
        for b in bars:
            ts = b.timestamp.astimezone(UTC)
            ts = ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)
            bar_by_ts[ts] = b

        for _, row in day_df.iterrows():
            et_time = dt.datetime.strptime(row['time_et'], '%H:%M').time()
            et_dt = ET.localize(dt.datetime.combine(
                dt.datetime.strptime(day, '%Y%m%d').date(), et_time))
            minute = (et_dt.minute // 5) * 5
            et_dt = et_dt.replace(minute=minute, second=0, microsecond=0)
            bar_ts = et_dt.astimezone(UTC).replace(second=0, microsecond=0)
            cur_bar = bar_by_ts.get(bar_ts)
            if not cur_bar:
                continue
            try:
                cur_idx = bars.index(cur_bar)
            except ValueError:
                continue
            future = bars[cur_idx + 1:cur_idx + 1 + MAX_HOLD_BARS]
            if len(future) < 3:
                continue
            # Compute actual forward 30-min range
            fut_high = max(f.high for f in future)
            fut_low = min(f.low for f in future)
            entry = cur_bar.close
            # Max favorable excursion (MFE) and MAE in points
            if len(future) > 0:
                mfe_long = fut_high - entry
                mae_long = entry - fut_low
                mfe_short = entry - fut_low
                mae_short = fut_high - entry
            else:
                mfe_long = mfe_short = mae_long = mae_short = 0

            # Best direction-agnostic PnL: 8pt stop / 16pt target, choose best direction
            pnl_long = TARGET_PT - COST_PT if mfe_long >= TARGET_PT and mae_long < STOP_PT else (max(mae_long, -STOP_PT) - COST_PT)
            pnl_short = TARGET_PT - COST_PT if mfe_short >= TARGET_PT and mae_short < STOP_PT else (max(mae_short, -STOP_PT) - COST_PT)
            best_pnl = max(pnl_long, pnl_short)

            oos_records.append({
                'date': day, 'time_et': row['time_et'],
                'close': row['close'], 'label': row['label'],
                'score': row['score'],
                'fut_high': fut_high, 'fut_low': fut_low,
                'mfe_long': mfe_long, 'mae_long': mae_long,
                'mfe_short': mfe_short, 'mae_short': mae_short,
                'pnl_long': pnl_long, 'pnl_short': pnl_short,
                'best_pnl': best_pnl,
            })

    oos = pd.DataFrame(oos_records)
    print(f'OOS bars: {len(oos)} across {oos.date.nunique()} days\n')

    # === TEST 1: Does the model predict actual price moves? ===
    print('=== TEST 1: ACTUAL FORWARD RANGE vs LABEL ===')
    print('Cross-check: how often does forward 30-min have a 16+pt move (the "target")?')
    oos['mfe_actual'] = oos[['mfe_long', 'mfe_short']].max(axis=1)
    oos['mae_actual'] = oos[['mae_long', 'mae_short']].max(axis=1)
    base_actual = (oos.mfe_actual >= TARGET_PT).mean()
    print(f'  Base rate of 16+pt MFE: {base_actual:.1%}\n')

    print('=== TEST 2: HIT RATE BY THRESHOLD (label vs actual move) ===')
    print(f'{"thresh":>7}  {"n":>5}  {"labelWR":>8}  {"actual16pt":>10}  {"actual20pt":>10}  {"actual25pt":>10}')
    for th in THRESHOLDS:
        m = oos.score > th
        if m.sum() < 30:
            continue
        n = m.sum()
        lbl = oos.loc[m, 'label'].mean()
        a16 = (oos.loc[m, 'mfe_actual'] >= 16).mean()
        a20 = (oos.loc[m, 'mfe_actual'] >= 20).mean()
        a25 = (oos.loc[m, 'mfe_actual'] >= 25).mean()
        print(f'{th:>7.2f}  {n:>5}  {lbl:>8.1%}  {a16:>10.1%}  {a20:>10.1%}  {a25:>10.1%}')

    # === TEST 3: REALISTIC TRADING PnL ===
    print('\n=== TEST 3: BEST-DIRECTION PnL (oracle picks long/short) ===')
    print('Assumes oracle picks the right direction. Upper bound on edge.')
    print(f'{"thresh":>7}  {"n":>5}  {"WR":>6}  {"totPnL":>8}  {"avg":>7}  {"Sharpe":>7}  {"maxDD":>7}')
    for th in THRESHOLDS:
        m = oos.score > th
        sub = oos.loc[m].copy()
        if len(sub) < 30:
            continue
        # WR with cost: win = pnl > 0
        wins = (sub.best_pnl > 0).sum()
        wr = wins / len(sub)
        total = sub.best_pnl.sum()
        avg = sub.best_pnl.mean()
        std = sub.best_pnl.std()
        sharpe = (avg / std) * np.sqrt(252) if std > 0 else 0
        cum = sub.best_pnl.cumsum()
        dd = (cum - cum.cummax()).min()
        print(f'{th:>7.2f}  {len(sub):>5}  {wr:>6.1%}  {total:>+8.0f}  {avg:>+7.2f}  {sharpe:>7.2f}  {dd:>7.1f}')

    # === TEST 4: BASELINE (no filter) ===
    print('\n=== TEST 4: BASELINE no filter ===')
    sub = oos.copy()
    wins = (sub.best_pnl > 0).sum()
    wr = wins / len(sub)
    total = sub.best_pnl.sum()
    avg = sub.best_pnl.mean()
    std = sub.best_pnl.std()
    sharpe = (avg / std) * np.sqrt(252) if std > 0 else 0
    cum = sub.best_pnl.cumsum()
    dd = (cum - cum.cummax()).min()
    print(f'  n={len(sub)} WR={wr:.1%} totPnL={total:+.0f}pt avg={avg:+.2f} Sharpe={sharpe:.2f} maxDD={dd:.1f}pt')

    # === TEST 5: LLM direction proxy (long if score>0.5 means bullish bias) ===
    print('\n=== TEST 5: naive long bias (assume long every time) ===')
    sub = oos.copy()
    sub['naive_pnl'] = sub.pnl_long
    wins = (sub.naive_pnl > 0).sum()
    wr = wins / len(sub)
    total = sub.naive_pnl.sum()
    avg = sub.naive_pnl.mean()
    sharpe = (avg / sub.naive_pnl.std()) * np.sqrt(252)
    cum = sub.naive_pnl.cumsum()
    dd = (cum - cum.cummax()).min()
    print(f'  n={len(sub)} WR={wr:.1%} totPnL={total:+.0f}pt avg={avg:+.2f} Sharpe={sharpe:.2f} maxDD={dd:.1f}pt')

    # Save OOS for further analysis
    oos.to_csv(os.path.join(OUT_DIR, 'oos_realistic.csv'), index=False)
    print(f'\nOOS saved: {OUT_DIR}/oos_realistic.csv')


if __name__ == '__main__':
    main()
