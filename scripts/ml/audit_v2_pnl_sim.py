"""V2 audit PnL validation — measures ACTUAL PnL of V2-confirmed vs V2-rejected bars.

For each M5 bar with score>0.5:
  1. Get the bar + 6 future bars
  2. Determine direction (long if net>0, short if net<0)
  3. Run V2 audit (with wick exception)
  4. Simulate entering at close with 8pt stop / 16pt target / 0.5pt cost
  5. Compare PnL: V2-confirmed trades vs V2-rejected trades

This is the REAL test of V2: does it actually improve PnL, not just label WR?
"""
import os
import sys
import csv
import datetime as dt
import pytz
import pandas as pd
import joblib

sys.path.insert(0, r'C:\Users\Mauro\Documents\nq-backtest-clean')
from scripts.ml.audit_v2_simulator import (
    load_day_bars, apply_v2_audit
)
from src.bar_aggregator import aggregate_to_bars
from src import Trade

ET = pytz.timezone('America/New_York')
UTC = pytz.UTC
DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'
CSV_FEATURES = r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml\features_230d.csv'

STOP_PT = 8.0
TARGET_PT = 16.0
COST_PT = 0.5
MAX_HOLD_BARS = 6
TRADES_PER_DAY_CAP = 3


def simulate_entry(bar, future_bars, direction):
    """Simulate 8pt stop / 16pt target entry, with cost."""
    entry = bar.close
    if direction == 'long':
        stop, target = entry - STOP_PT, entry + TARGET_PT
    elif direction == 'short':
        stop, target = entry + STOP_PT, entry - TARGET_PT
    else:
        return 0, 'no direction'
    for fb in future_bars[:MAX_HOLD_BARS]:
        if direction == 'long':
            if fb.low <= stop: return -STOP_PT - COST_PT, 'stop'
            if fb.high >= target: return TARGET_PT - COST_PT, 'target'
        else:
            if fb.high >= stop: return -STOP_PT - COST_PT, 'stop'
            if fb.low <= target: return TARGET_PT - COST_PT, 'target'
    # Time stop
    if future_bars:
        last = future_bars[min(MAX_HOLD_BARS - 1, len(future_bars) - 1)]
        if direction == 'long':
            return last.close - entry - COST_PT, 'time'
        else:
            return entry - last.close - COST_PT, 'time'
    return 0, 'no future'


def main():
    print('=== V2 PnL SIMULATION (real forward OHLC) ===\n')
    df = pd.read_csv(CSV_FEATURES, dtype={'date': str})
    df = df.sort_values(['date', 'time_et']).reset_index(drop=True)
    bundle = joblib.load(r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml\rf_v1.pkl')
    model = bundle['model']
    feats = bundle['feature_cols']
    df['score'] = model.predict_proba(df[feats].fillna(0).values)[:, 1]

    # Load all days bars (with cache)
    cache = r'C:\Users\Mauro\Documents\nq-backtest-clean\output\walkforward\day_bars_cache.pkl'
    if os.path.exists(cache):
        import pickle
        with open(cache, 'rb') as f:
            day_bars = pickle.load(f)
        print(f'Loaded {len(day_bars)} days from cache')
    else:
        day_bars = {}
        for d in sorted(df.date.unique()):
            day_bars[d] = load_day_bars(d)
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, 'wb') as f:
            pickle.dump(day_bars, f)

    bar_lookup = {}
    for d, bars in day_bars.items():
        for b in bars:
            ts = b.timestamp.astimezone(UTC).replace(minute=(b.timestamp.minute // 5) * 5, second=0, microsecond=0)
            bar_lookup[(d, ts)] = b

    # Run audit + simulate for each bar
    print('Running V2 audit + PnL sim on all score>0.5 bars...')
    results = []
    for _, row in df.iterrows():
        if row.score <= 0.5:
            continue
        d = row['date']
        t = row['time_et']
        et_time = dt.datetime.strptime(t, '%H:%M').time()
        et_dt = ET.localize(dt.datetime.combine(dt.datetime.strptime(d, '%Y%m%d').date(), et_time))
        minute = (et_dt.minute // 5) * 5
        et_dt = et_dt.replace(minute=minute, second=0, microsecond=0)
        bar_ts = et_dt.astimezone(UTC).replace(second=0, microsecond=0)
        bar = bar_lookup.get((d, bar_ts))
        if not bar:
            continue
        direction = 'long' if row['net'] > 0 else ('short' if row['net'] < 0 else None)
        if not direction:
            continue
        bars_today = day_bars.get(d, [])
        try:
            cur_idx = bars_today.index(bar)
        except ValueError:
            continue
        future = bars_today[cur_idx + 1:cur_idx + 1 + MAX_HOLD_BARS]
        if not future:
            continue
        prev_bars = bars_today[:cur_idx]
        day_open = bars_today[:cur_idx + 1]
        verdict, rule, reason = apply_v2_audit(bar, prev_bars, day_open, row, direction)
        pnl, exit_reason = simulate_entry(bar, future, direction)
        results.append({
            'date': d, 'time_et': t, 'close': bar.close,
            'score': row.score, 'direction': direction,
            'verdict': verdict, 'rule': rule, 'pnl': pnl, 'exit_reason': exit_reason,
            'label': row['label'],
        })

    rdf = pd.DataFrame(results)
    print(f'Total bars simulated: {len(rdf)}')
    print()

    # Stats
    conf = rdf[rdf.verdict == 'confirm']
    rej = rdf[rdf.verdict == 'reject']

    # Cap trades per day for both groups (realistic)
    def cap_per_day(group):
        return group.sort_values('score', ascending=False).head(TRADES_PER_DAY_CAP)

    conf_capped = conf.groupby('date', group_keys=False).apply(cap_per_day)
    rej_capped = rej.groupby('date', group_keys=False).apply(cap_per_day)

    print('=== PnL COMPARISON (capped at 3 trades/day) ===\n')
    print(f'V2-CONFIRMED trades: {len(conf_capped)}')
    print(f'  WR: {(conf_capped.pnl > 0).mean():.1%}')
    print(f'  Total PnL: {conf_capped.pnl.sum():+.0f}pt')
    print(f'  Avg/trade: {conf_capped.pnl.mean():+.2f}pt')
    print(f'  Per-day PnL: {conf_capped.groupby("date").pnl.sum().mean():+.2f}pt')
    print(f'  % days positive: {(conf_capped.groupby("date").pnl.sum() > 0).mean():.1%}')
    print()
    print(f'V2-REJECTED trades: {len(rej_capped)}')
    print(f'  WR: {(rej_capped.pnl > 0).mean():.1%}')
    print(f'  Total PnL: {rej_capped.pnl.sum():+.0f}pt')
    print(f'  Avg/trade: {rej_capped.pnl.mean():+.2f}pt')
    print(f'  Per-day PnL: {rej_capped.groupby("date").pnl.sum().mean():+.2f}pt')
    print(f'  % days positive: {(rej_capped.groupby("date").pnl.sum() > 0).mean():.1%}')
    print()

    # "What if we only traded V2-confirmed bars"
    conf_per_day = conf_capped.groupby('date').pnl.sum()
    print(f'V2-CONFIRMED: {len(conf_per_day)} days, total PnL: {conf_per_day.sum():+.0f}pt')
    print(f'  days>0: {(conf_per_day > 0).sum()}/{len(conf_per_day)} ({(conf_per_day > 0).mean():.1%})')
    print(f'  avg winning day: {conf_per_day[conf_per_day > 0].mean():+.1f}pt')
    print(f'  avg losing day: {conf_per_day[conf_per_day < 0].mean():+.1f}pt')
    print(f'  max day: {conf_per_day.max():+.0f}pt, min day: {conf_per_day.min():+.0f}pt')
    print()

    # Compare to baseline (all score>0.5 trades, no V2 filter)
    print('=== BASELINE: all score>0.5 bars (no V2 filter) ===')
    base_capped = rdf.groupby('date', group_keys=False).apply(cap_per_day)
    base_per_day = base_capped.groupby('date').pnl.sum()
    print(f'  {len(base_per_day)} days, total PnL: {base_per_day.sum():+.0f}pt')
    print(f'  days>0: {(base_per_day > 0).sum()}/{len(base_per_day)} ({(base_per_day > 0).mean():.1%})')
    print(f'  avg winning day: {base_per_day[base_per_day > 0].mean():+.1f}pt')
    print(f'  avg losing day: {base_per_day[base_per_day < 0].mean():+.1f}pt')
    print()

    # By rule breakdown
    print('=== V2 PnL BY RULE (rejected bars — would V2 have helped?) ===')
    for rule in rej.rule.unique():
        sub = rej[rej.rule == rule]
        if len(sub) == 0: continue
        print(f'  {rule}: n={len(sub)}, WR={(sub.pnl > 0).mean():.1%}, total PnL={sub.pnl.sum():+.0f}pt, avg={sub.pnl.mean():+.2f}pt')

    # Save
    out = r'C:\Users\Mauro\Documents\nq-backtest-clean\output\walkforward\v2_pnl_sim.csv'
    rdf.to_csv(out, index=False)
    print(f'\nFull results saved: {out}')


if __name__ == '__main__':
    main()
