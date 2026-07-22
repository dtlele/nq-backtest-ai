import pandas as pd, sys, warnings
warnings.filterwarnings('ignore')
csv_path = r'C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250203.trades.csv'
print(f'Loading {csv_path}...')
df = pd.read_csv(csv_path, low_memory=False, dtype={'price': float})
df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
entry_time = pd.Timestamp('2025-02-03 15:23:00', tz='UTC')
entry_price = 21229.75
stop = 21198.0
target = 21277.5
print(f'Active trade at {entry_time} UTC: entry={entry_price}, stop={stop}, target={target}, R:R=1.5')
df_after = df[df['ts_event'] >= entry_time].copy()
if df_after.empty:
    print('No data after entry')
    sys.exit(1)
# find first crossing
for i, row in df_after.iterrows():
    p = row['price']
    if p <= stop:
        print(f'STOP HIT at {row["ts_event"]} price {p:.2f} (stop {stop})')
        break
    if p >= target:
        print(f'TARGET HIT at {row["ts_event"]} price {p:.2f} (target {target})')
        break
else:
    print('Neither stop nor target hit in trade data (price never crossed).')
    last_price = df_after.iloc[-1]['price']
    print(f'Last price in dataset: {last_price:.2f}')
    # compute max high/low after entry
    high = df_after['price'].max()
    low = df_after['price'].min()
    print(f'High after entry: {high:.2f}, Low after entry: {low:.2f}')
    dist_to_target = high - entry_price
    dist_to_stop = entry_price - low
    print(f'Maximum unrealized profit: {dist_to_target:.2f} pts')
    print(f'Maximum unrealized loss: -{dist_to_stop:.2f} pts')
    # check if price closed above/below entry at end of day (last trade)
    if last_price >= entry_price:
        print(f'Would close at market close with profit of {last_price - entry_price:.2f} pts.')
    else:
        print(f'Would close at market close with loss of {entry_price - last_price:.2f} pts.')