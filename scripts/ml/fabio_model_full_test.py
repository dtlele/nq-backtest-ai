"""
Run Fabio model on full dataset (not just V8b) to measure baseline performance.
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Import the tuner
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fabio_model_tune import row_to_bar, run_fabio_tuned, simulate_pnl, is_ny_session


def stress_test(df_t, nq_round_trip_cost=22.0):
    """Apply realistic costs to a list of trades."""
    df = df_t.copy()
    df['pnl_usd_gross'] = df['pnl_usd']
    df['pnl_usd_net'] = df['pnl_usd'] - nq_round_trip_cost
    print(f'\n=== STRESS TEST: ${nq_round_trip_cost:.0f}/roundtrip ===')
    print(f'  (4 ticks slippage + $1.50 fees per side, total per RT)')
    print(f'  Trades: {len(df)}')
    print(f'  Gross PnL: ${df["pnl_usd_gross"].sum():.0f}')
    print(f'  Net PnL:   ${df["pnl_usd_net"].sum():.0f}')
    print(f'  Net PnL/week: ${df["pnl_usd_net"].sum() / (df["date"].nunique() / 5):.0f}')
    # Worst case
    return df


if __name__ == '__main__':
    df = pd.read_csv('data/ml/features_230d.csv')
    df['date'] = df['date'].astype(str)
    df['datetime_et'] = pd.to_datetime(df['date'] + ' ' + df['time_et'])

    # Use full NY session
    df_ny = df[(df['tod'] >= 9.5) & (df['tod'] <= 16.0)].copy()
    print(f'Full NY session rows: {len(df_ny)}')
    print(f'Date range: {df_ny["date"].min()} -> {df_ny["date"].max()}')

    # Variant 1 (best so far): min_big=50, R:R=1:1, hold=12
    print('\n[Full period: min_big_size=50, R:R=1:1, hold=12]')
    setups = run_fabio_tuned(df_ny, min_big_size=50, lvn_lookback=10, swing_lookback=3)
    print(f'  Total setups: {len(setups)}')
    if setups:
        trades = simulate_pnl(setups, df_ny, hold_bars=6, target_r=1.0, max_hold=12)
        if trades:
            df_t = pd.DataFrame(trades)
            wins = (df_t['outcome'] == 'target').sum()
            losses = (df_t['outcome'] == 'stop').sum()
            timeouts = (df_t['outcome'] == 'timeout').sum()
            total_pnl = df_t['pnl_usd'].sum()
            total_pnl_per_week = total_pnl / (df_ny['date'].nunique() / 5)
            print(f'  Trades: {len(trades)} | Wins: {wins} | Losses: {losses} | Timeouts: {timeouts}')
            print(f'  Win rate: {wins/len(trades)*100:.1f}%')
            print(f'  Total PnL: ${total_pnl:.0f}')
            print(f'  PnL/week: ${total_pnl_per_week:.0f}')
            print(f'  Trades/day: {len(trades)/df_ny["date"].nunique():.1f}')

            # Per-day stats
            by_date = df_t.groupby('date')['pnl_usd'].agg(['sum', 'count', 'mean'])
            print(f'\n  Days with profit: {(by_date["sum"] > 0).sum()} / {len(by_date)} ({(by_date["sum"] > 0).mean()*100:.0f}%)')
            print(f'  Best day: ${by_date["sum"].max():.0f} on {by_date["sum"].idxmax()}')
            print(f'  Worst day: ${by_date["sum"].min():.0f} on {by_date["sum"].idxmin()}')

            # Show by-month
            df_t['month'] = df_t['date'].astype(str).str[:6]
            by_month = df_t.groupby('month')['pnl_usd'].agg(['sum', 'count'])
            print('\n  By month:')
            print(by_month.to_string())

            # Stress test
            print()
            stress_test(df_t, nq_round_trip_cost=22.0)  # 4 ticks + 1.50 fees
            stress_test(df_t, nq_round_trip_cost=10.0)  # 2 ticks no fees
            stress_test(df_t, nq_round_trip_cost=5.0)   # 1 tick only
