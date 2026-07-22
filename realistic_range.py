import pandas as pd
df = pd.read_csv(r'C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250203.trades.csv', low_memory=False)
df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
df['price'] = df['price'].astype(float)
# remove extreme outliers (price < 5000 or > 30000)
df = df[(df['price'] > 5000) & (df['price'] < 30000)].copy()
entry_time = pd.Timestamp('2025-02-03 15:23:00', tz='UTC')
after = df[df['ts_event'] >= entry_time].copy()
print(f'Trades after entry (cleaned): {len(after)}')
if len(after) == 0:
    exit()
print('First few trades:')
print(after[['ts_event','price','size']].head())
print('\nStats:')
print(after['price'].describe())
low = after['price'].min()
high = after['price'].max()
print(f'Low after entry (realistic): {low:.2f}')
print(f'High after entry (realistic): {high:.2f}')
entry_price = 21229.75
stop = 21198.0
target = 21277.5
if low <= stop:
    print(f'\nSTOP would have been hit at price {low:.2f} (time {after[after["price"] <= stop].iloc0["ts_event"]})')
else:
    print(f'\nStop NOT hit (low after entry {low:.2f} > stop {stop})')
if high >= target:
    first_target = after[after['price'] >= target].iloc[0]
    print(f'TARGET hit at {first_target["ts_event"]} price {first_target["price"]:.2f}')
else:
    print(f'Target NOT hit (max {high:.2f} < target {target})')
# compute if price ever went below stop after entry
stop_hit = after['price'].le(stop).any()
target_hit = after['price'].ge(target).any()
print(f'\nStop hit after entry: {stop_hit}')
print(f'Target hit after entry: {target_hit}')
# compute time to target if hit
if target_hit:
    first = after[after['price'] >= target].iloc[0]
    delta = (first['ts_event'] - entry_time).total_seconds()
    print(f'Target hit {delta:.2f} seconds after entry')
if stop_hit:
    first = after[after['price'] <= stop].iloc[0]
    delta = (first['ts_event'] - entry_time).total_seconds()
    print(f'Stop hit {delta:.2f} seconds after entry')
# plot price movement
import matplotlib.pyplot as plt
plt.figure(figsize=(10,5))
plt.plot(after['ts_event'], after['price'], '.', markersize=1, alpha=0.5)
plt.axhline(y=entry_price, color='black', linestyle='--', label='entry')
plt.axhline(y=stop, color='red', linestyle='--', label='stop')
plt.axhline(y=target, color='green', linestyle='--', label='target')
plt.legend(); plt.title('Price after entry (cleaned)')
plt.savefig('price_after_entry.png', dpi=150)
print('Plot saved to price_after_entry.png')