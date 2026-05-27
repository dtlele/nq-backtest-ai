import pandas as pd

f = r'c:\Users\Mauro\Documents\nq-backtest\archive_data\glbx-mdp3-20250430.trades.csv'
df = pd.read_csv(f, usecols=['ts_event', 'action', 'side', 'price', 'size'])
df = df[df['action'] == 'T'].copy()
df['ts_event'] = pd.to_datetime(df['ts_event']) # keeps nanoseconds in Pandas!

df.sort_values('ts_event', inplace=True)

time_diff = df['ts_event'].diff()
group_change = (df['side'] != df['side'].shift(1)) | \
               (df['price'] != df['price'].shift(1)) | \
               (time_diff.dt.total_seconds() > 0.01)

df['group_id'] = group_change.cumsum()

agg_trades = df.groupby('group_id').agg(
    ts_event=('ts_event', 'first'),
    side=('side', 'first'),
    price=('price', 'first'),
    size=('size', 'sum'),
    trade_count=('size', 'count')
).reset_index()

big_trades = agg_trades[agg_trades['size'] >= 30]

print(f'Original raw trades: {len(df)}')
print(f'Original raw trades >= 30: {(df["size"] >= 30).sum()}')
print(f'Aggregated trades total: {len(agg_trades)}')
print(f'Aggregated trades >= 30: {len(big_trades)}')
print(big_trades.head(10))
