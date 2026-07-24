"""Walk-forward OOS analysis on the 230-day M5 NQ dataset.

Simulates a realistic day-by-day trading decision:
- For each day, train the model on PRIOR days only (no future data leak)
- Score the bars of the day
- For each score > threshold, "trade" — assume the next 30 min moves
  in the direction of the bar (long if net>0, short if net<0)
- Measure: hit rate, edge, Sharpe, max DD, total R

This is purely OFFLINE: no LLM calls, no API usage.
"""
import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score

CSV = r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml\features_230d.csv'
OUT_DIR = r'C:\Users\Mauro/Documents\nq-backtest-clean\output\walkforward'
os.makedirs(OUT_DIR, exist_ok=True)

# Config
MIN_TRAIN_DAYS = 30       # need at least 30 days of training
TEST_WINDOW_DAYS = 1      # test 1 day at a time (true walk-forward)
RETRAIN_EVERY_DAYS = 5    # retrain every 5 days
THRESHOLDS = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]
TRADES_PER_DAY_CAP = 5    # cap on trades per day (realistic: 1-3)
STOP_DISTANCE_PT = 8.0    # 8pt stop (close-based)
TARGET_DISTANCE_PT = 16.0 # 2R target
COST_PER_TRADE_PT = 0.5   # round-trip slippage + comm


def main():
    print('=== WALK-FORWARD OOS ANALYSIS (230 days NQ M5) ===\n')
    df = pd.read_csv(CSV, dtype={'date': str})
    df = df.sort_values(['date', 'time_et']).reset_index(drop=True)

    # Feature columns
    feature_cols = [c for c in df.columns if c not in ('date', 'time_et', 'label')]
    print(f'Features: {len(feature_cols)}')
    print(f'Total rows: {len(df)}, dates: {df.date.nunique()}')
    print(f'Date range: {df.date.min()} to {df.date.max()}\n')

    dates = sorted(df.date.unique())
    print(f'Window: train on first {MIN_TRAIN_DAYS}+ days, walk forward 1 day at a time')
    print(f'Retrain every {RETRAIN_EVERY_DAYS} test days\n')
    sys.stdout.reconfigure(encoding='utf-8')

    # Store OOS predictions and trades
    oos_records = []
    model = None
    last_train_idx = -999

    for day_idx, day in enumerate(dates):
        test_mask = df.date == day
        test_df = df[test_mask].copy()
        if len(test_df) == 0:
            continue

        # Need at least MIN_TRAIN_DAYS prior days for training
        if day_idx < MIN_TRAIN_DAYS:
            continue

        # Retrain periodically
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

        # Score test day
        Xte = test_df[feature_cols].fillna(0).values
        proba = model.predict_proba(Xte)[:, 1]
        test_df = test_df.assign(score=proba)

        for _, row in test_df.iterrows():
            oos_records.append({
                'date': row['date'],
                'time_et': row['time_et'],
                'close': row['close'],
                'net': row['net'],
                'label': row['label'],
                'score': row['score'],
            })

    oos = pd.DataFrame(oos_records)
    print(f'Total OOS predictions: {len(oos)} bars across {oos.date.nunique()} days')
    print(f'Base WIN rate: {oos.label.mean():.3f}\n')

    # === EDGE BY THRESHOLD ===
    print('=== OOS EDGE BY SCORE THRESHOLD ===')
    print(f'{"thresh":>7}  {"n_bars":>7}  {"WR":>6}  {"base":>5}  {"edge":>6}  {"days>3":>7}')
    summary = []
    for th in THRESHOLDS:
        m = oos.score > th
        if m.sum() < 50:
            continue
        wr = oos.loc[m, 'label'].mean()
        n_days_with_3plus = (oos[m].groupby('date').size() > 3).sum()
        edge = wr - oos.label.mean()
        print(f'{th:>7.2f}  {m.sum():>7}  {wr:>6.3f}  {oos.label.mean():>5.3f}  {edge:>+6.3f}  {n_days_with_3plus:>7}')
        summary.append({'threshold': th, 'n': m.sum(), 'wr': wr, 'edge': edge,
                        'n_day_3plus': n_days_with_3plus})

    # === SIMULATED TRADING ===
    print('\n=== SIMULATED TRADING (with stop/target/cost) ===')
    print(f'Assumptions: stop={STOP_DISTANCE_PT}pt, target={TARGET_DISTANCE_PT}pt (R:R=2.0), cost={COST_PER_TRADE_PT}pt')
    print('Entry direction: LONG if net>0, SHORT if net<0')
    print('Win: +16pt - cost = +15.5pt; Loss: -8pt - cost = -8.5pt\n')

    for th in [0.6, 0.65, 0.7, 0.75]:
        trades = []
        for day, day_df in oos.groupby('date'):
            cand = day_df[day_df.score > th].sort_values('score', ascending=False).head(TRADES_PER_DAY_CAP)
            for _, r in cand.iterrows():
                # Long if net>0, short if net<0
                if r['net'] > 0:
                    # Long: win if label=1, loss otherwise
                    pnl = TARGET_DISTANCE_PT - COST_PER_TRADE_PT if r['label'] == 1 else -STOP_DISTANCE_PT - COST_PER_TRADE_PT
                elif r['net'] < 0:
                    pnl = TARGET_DISTANCE_PT - COST_PER_TRADE_PT if r['label'] == 1 else -STOP_DISTANCE_PT - COST_PER_TRADE_PT
                else:
                    continue  # no direction
                trades.append({'date': day, 'time_et': r['time_et'], 'pnl': pnl,
                              'label': r['label'], 'score': r['score']})
        if not trades:
            print(f'Threshold {th}: 0 trades\n')
            continue
        tdf = pd.DataFrame(trades)
        wins = (tdf.pnl > 0).sum()
        losses = (tdf.pnl < 0).sum()
        wr = wins / len(tdf)
        total = tdf.pnl.sum()
        avg = tdf.pnl.mean()
        std = tdf.pnl.std()
        sharpe = (avg / std) * np.sqrt(252) if std > 0 else 0
        # Max DD on cumulative PnL
        cum = tdf.pnl.cumsum()
        dd = (cum - cum.cummax()).min()
        # Annualized return
        n_days = tdf.date.nunique()
        ann = total * 252 / n_days if n_days > 0 else 0
        print(f'Threshold {th}:')
        print(f'  n_trades: {len(tdf)} ({n_days} days, {len(tdf)/n_days:.1f}/day)')
        print(f'  Win/Loss: {wins}/{losses} (WR={wr:.1%})')
        print(f'  Total PnL: {total:+.1f}pt (per-trade avg: {avg:+.2f}pt)')
        print(f'  Sharpe (annualized): {sharpe:.2f}')
        print(f'  Max DD: {dd:.1f}pt')
        print(f'  Annualized: {ann:+.0f}pt\n')

    # === BASELINE: no filter (every bar) ===
    print('=== BASELINE: NO FILTER (all bars) ===')
    base_trades = []
    for day, day_df in oos.groupby('date'):
        for _, r in day_df.iterrows():
            if r['net'] > 0:
                pnl = TARGET_DISTANCE_PT - COST_PER_TRADE_PT if r['label'] == 1 else -STOP_DISTANCE_PT - COST_PER_TRADE_PT
            elif r['net'] < 0:
                pnl = TARGET_DISTANCE_PT - COST_PER_TRADE_PT if r['label'] == 1 else -STOP_DISTANCE_PT - COST_PER_TRADE_PT
            else:
                continue
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
        print(f'  n_trades: {len(bdf)} ({len(bdf)/n_days:.1f}/day)')
        print(f'  Win/Loss: {wins}/{len(bdf)-wins} (WR={wr:.1%})')
        print(f'  Total PnL: {total:+.1f}pt (per-trade avg: {avg:+.3f}pt)')
        print(f'  Sharpe (annualized): {sharpe:.2f}')
        print(f'  Max DD: {dd:.1f}pt')

    # === SAVE OOS ===
    oos.to_csv(os.path.join(OUT_DIR, 'oos_predictions.csv'), index=False)
    print(f'\nOOS predictions saved: {OUT_DIR}/oos_predictions.csv')


if __name__ == '__main__':
    main()
