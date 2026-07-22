import pandas as pd, numpy as np, sys, os, json, math, datetime as dt, re, sys, warnings
warnings.filterwarnings('ignore')
csv_path = r'C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250203.trades.csv'
print(f'Loading {csv_path}...')
df = pd.read_csv(csv_path, low_memory=False)
# parse ts_event (nanoseconds UTC) to datetime
df['ts_event'] = pd.to_datetime(df['ts_event'], unit='ns', utc=True)
df['price'] = df['price'] / 100_000_000.0  # databento price scaling? maybe not needed? check sample
df['price'].head()
# filter after 15:23:00 UTC (entry time) up to maybe 18:00 (end of day)
entry_time = pd.Timestamp('2025-02-03 15:23:00', tz='UTC')
stop = 21198.0
target = 21277.5
# find first price crossing stop or target after entry_time
df_after = df[df['ts_event'] > entry_time].copy()
if df_after.empty:
    print('No data after entry_time')
    sys.exit(1)
# compute cumulative min and max for high/low
# we'll just check each trade price
for i, row in df_after.iterrows():
    p = row['price']
    if p <= stop:
        print(f'STOP HIT at {row["ts_event"]} price {p} (stop {stop})')
        break
    if p >= target:
        print(f'TARGET HIT at {row["ts_event"]} price {p} (target {target})')
        break
else:
    # reached end of day without hitting stop or target
    last_price = df_after.iloc[-1]['price']
    print(f'NEITHER stop nor target hit by end of data (last price {last_price})')
    # compute max drawdown and max profit
    low = df_after['price'].min()
    high = df_after['price'].max()
    print(f'Low after entry: {low}, High after entry: {high}')
    print(f'Distance to stop: {entry_price - low:.2f} pts')
    print(f'Distance to target: {high - entry_price:.2f} pts')
    # check if price closed above/below entry at end of day
    if last_price >= entry_price:
        print('Trade would close at end of day with profit? Not necessarily; need to compute at close')
    else:
        print('Trade would close at end of day with loss? Not necessarily')
# also compute 1-minute bars for visualization
df_after.set_index('ts_event', inplace=True)
resampled = df_after['price'].resample('1min').ohlc()
print('\nFirst few 1-minute bars after entry:')
print(resampled.head(10))
# find where price crosses stop/target in resampled bars (using high/low)
for idx, bar in resampled.iterrows():
    if bar['low'] <= stop:
        print(f'STOP hit in bar {idx} low {bar["low"]}')
        break
    if bar['high'] >= target:
        print(f'TARGET hit in bar {idx} high {bar["high"]}')
        break
else:
    print('No crossing in 1-minute bars up to end of data')
    # compute final bar close
    last_bar = resampled.iloc[-1]
    print(f'Last bar close: {last_bar["close"]}')
    # compute P&L if closed at last bar close
    if last_bar['close'] >= entry_price:
        print(f'Would be profitable of {last_bar["close"] - entry_price:.2f} pts')
    else:
        print(f'Would be losing {entry_price - last_bar["close"]:.2f} pts')