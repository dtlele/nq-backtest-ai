import pandas as pd, numpy as np
df = pd.read_csv(r'C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250203.trades.csv', low_memory=False)
df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
df['price'] = df['price'].astype(float)
# filter after 15:22:00 up to maybe 15:30 (enough to see if target or stop hit)
mask = (df['ts_event'] >= '2025-02-03 15:22:00') & (df['ts_event'] <= '2025-02-03 15:30:00')
df_sub = df.loc[mask].copy()
print(f'Trades in window: {len(df_sub)}')
print(df_sub[['ts_event','price','size']].head())
# resample 1-minute OHLC
df_sub.set_index('ts_event', inplace=True)
resampled = df_sub['price'].resample('1min').agg(['first','max','min','last'])
resampled.columns = ['open','high','low','close']
print('\n1-minute bars:')
print(resampled)
entry_price = 21229.75
stop = 21198.0
target = 21277.5
print(f'\nEntry: {entry_price}, Stop: {stop}, Target: {target}')
# check each bar
for idx, row in resampled.iterrows():
    if row['low'] <= stop:
        print(f'STOP hit at bar {idx} low {row["low"]:.2f}')
        break
    if row['high'] >= target:
        print(f'TARGET hit at bar {idx} high {row["high"]:.2f}')
        break
else:
    print('Neither stop nor target hit within 8 minutes.')
    # compute max/min
    max_high = resampled['high'].max()
    min_low = resampled['low'].min()
    print(f'Max high: {max_high:.2f}, Min low: {min_low:.2f}')
    if max_high >= target:
        print('Target would have been hit later (outside window).')
    if min_low <= stop:
        print('Stop would have been hit later (outside window).')
# also check raw trades for immediate spike
spike = df_sub[df_sub['price'] >= target]
if not spike.empty:
    first_spike = spike.iloc[0]
    print(f'\nFirst trade >= target at {first_spike.name} price {first_spike["price"]:.2f}')
    # compute time from entry
    entry_ts = pd.Timestamp('2025-02-03 15:23:00', tz='UTC')
    delta = (first_spike.name - entry_ts).total_seconds()
    print(f'Seconds after entry: {delta:.2f}')
else:
    print('\nNo trade >= target in window.')
# compute profit/loss if exit at end of window
last_price = resampled.iloc[-1]['close']
print(f'\nPrice at end of window (15:30): {last_price:.2f}')
if last_price >= target:
    print('Target already hit before end of window.')
elif last_price <= stop:
    print('Stop already hit before end of window.')
else:
    print('Trade still open within window.')
    unrealized = (last_price - entry_price) * 5.0  # $ per point NQ? 5$ per point? Actually NQ = $20 per point? Wait NQ tick value $5 per point (0.25 tick = $1.25). I think NQ = $5 per point.
    print(f'Unrealized P&L at 15:30: {unrealized:.2f} $ per contract')