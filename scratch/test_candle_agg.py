import pandas as pd
import pytz

f = r'c:\Users\Mauro\Documents\nq-backtest\archive_data\glbx-mdp3-20250430.trades.csv'
df = pd.read_csv(f, usecols=['ts_event', 'action', 'side', 'price', 'size'])
df = df[df['action'] == 'T'].copy()
df['ts_event'] = pd.to_datetime(df['ts_event']).dt.tz_convert('America/New_York')

ny_df = df[(df['ts_event'].dt.hour >= 9) & (df['ts_event'].dt.hour < 16)].copy()

ny_df['minute'] = ny_df['ts_event'].dt.floor('1min')
agg = ny_df.groupby(['minute', 'side', 'price'])['size'].sum().reset_index()

big_bubbles = agg[agg['size'] >= 30]

print(f'Total M1 Price-Side levels: {len(agg)}')
print(f'Bubbles >= 30: {len(big_bubbles)}')
print(f'Bubbles >= 50: {len(agg[agg["size"] >= 50])}')
print(f'Bubbles >= 100: {len(agg[agg["size"] >= 100])}')
print(f'Bubbles >= 300: {len(agg[agg["size"] >= 300])}')
