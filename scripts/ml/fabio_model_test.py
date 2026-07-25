"""
Test Fabio's 3-step model on V8b period (4-11 Feb 2025).

Uses pre-computed M5 features from data/ml/features_230d.csv.
This is an OFFLINE test — no LLM, no API calls.
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.fabio_model import (
    build_fabio_setup, SetupType, is_fabio_active_window,
    is_ny_session, classify_market_state,
)

# Load dataset
df = pd.read_csv('data/ml/features_230d.csv')
df['date'] = df['date'].astype(str)
df['datetime_et'] = pd.to_datetime(df['date'] + ' ' + df['time_et'])

# Filter to V8b (4-11 Feb 2025) NY session
v8b = df[(df['date'] >= '20250204') & (df['date'] <= '20250211')].copy()
v8b_ny = v8b[(v8b['tod'] >= 9.5) & (v8b['tod'] <= 16.0)].copy()
print(f'V8b total rows: {len(v8b)}, NY session: {len(v8b_ny)}')
print(f'Dates: {v8b_ny["date"].unique()}')

# Build setups
# We need to convert DF rows to "Bar-like" objects
# But our fabio_model uses Bar dataclass. Let's use a thin adapter.
from src import Bar
from datetime import datetime, timezone

def row_to_bar(row):
    # Parse timestamp
    try:
        ts = pd.Timestamp(row['datetime_et'])
        if ts.tz is None:
            ts = ts.tz_localize('America/New_York')
        else:
            ts = ts.tz_convert('America/New_York')
        ts_utc = ts.tz_convert('UTC').to_pydatetime()
    except Exception as e:
        ts_utc = datetime.now(timezone.utc)
    # Estimate big_trades from count + total
    big_count = int(row.get('big_trades_count', 0))
    big_total = int(row.get('big_trades_total', 0))
    big_trades = []
    if big_count > 0 and big_total > 0:
        avg_size = max(1, big_total // big_count)
        # If avg is >= NQ_BIG_TRADE_THRESHOLD (80), create fake big trades
        if avg_size >= 30:  # min big trade size
            from src import Trade, NQ_BIG_TRADE_THRESHOLD
            # Distribute as buy or sell based on delta sign
            is_buy = row.get('delta', 0) > 0
            side = 'A' if is_buy else 'B'
            n = min(big_count, 3)  # cap
            for _ in range(n):
                big_trades.append(Trade(
                    ts_event=ts_utc,
                    side=side,
                    price=float(row['close']),
                    size=max(NQ_BIG_TRADE_THRESHOLD, avg_size),
                ))
    return Bar(
        timestamp=ts_utc,
        open=float(row['open']),
        high=float(row['high']),
        low=float(row['low']),
        close=float(row['close']),
        volume=int(row.get('volume', 0)),
        buy_volume=int(row.get('volume', 0) * 0.5),  # estimate
        sell_volume=int(row.get('volume', 0) * 0.5),
        delta=int(row.get('delta', 0)),
        delta_pct=0.0,
        cvd=int(row.get('cv_delta_30m', 0)),
        vwap=0.0,
        big_trades=big_trades,
        footprint={},
    )

# Group by day
setups_found = []
for date, day_df in v8b_ny.groupby('date'):
    day_df = day_df.sort_values('datetime_et').reset_index(drop=True)
    bars_today = [row_to_bar(row) for _, row in day_df.iterrows()]
    # Sliding window: at each bar, build setup
    for i in range(20, len(bars_today)):  # need 20 bars for ATR
        m5_bars = bars_today[max(0, i-20):i+1]
        m1_bar = bars_today[i]
        # Estimate prev-day POC/VAH/VAL from prior day bars (use yesterday's data)
        prev_date = (pd.Timestamp(date) - pd.Timedelta(days=1)).strftime('%Y%m%d')
        prev_df = v8b_ny[v8b_ny['date'] == prev_date]
        prev_poc = prev_vah = prev_val = None
        if len(prev_df) > 0:
            # Approximate POC as median of close prices
            prev_poc = float(prev_df['close'].median())
            prev_vah = float(prev_df['high'].quantile(0.7))
            prev_val = float(prev_df['low'].quantile(0.3))
        setup = build_fabio_setup(
            m5_bars=m5_bars,
            m1_bar=m1_bar,
            prev_day_poc=prev_poc,
            prev_day_vah=prev_vah,
            prev_day_val=prev_val,
        )
        if setup.is_valid():
            setups_found.append({
                'date': date,
                'time_et': day_df.iloc[i]['time_et'],
                'setup_type': setup.setup_type.value,
                'direction': setup.direction,
                'entry': setup.entry,
                'stop': setup.stop,
                'target_1': setup.target_1,
                'confidence': setup.confidence,
                'trigger_size': setup.trigger_m1_size,
                'lvn_price': setup.lvn_zone[0] + 2.0 * 0.25,  # mid
                'notes': setup.notes,
            })

print(f'\n=== Total setups found in V8b: {len(setups_found)} ===')
if setups_found:
    result_df = pd.DataFrame(setups_found)
    print(result_df.head(30).to_string())
    print(f'\nBy direction: {result_df["direction"].value_counts().to_dict()}')
    print(f'By setup_type: {result_df["setup_type"].value_counts().to_dict()}')
    print(f'Avg confidence: {result_df["confidence"].mean():.1f}')
    print(f'Avg trigger size: {result_df["trigger_size"].mean():.0f}')
    # Save
    result_df.to_csv('output/fabio_v8b_test.csv', index=False)
    print('\nSaved to output/fabio_v8b_test.csv')
else:
    print('NO SETUPS FOUND — check filter thresholds')
