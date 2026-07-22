import pandas as pd, numpy as np
df = pd.read_csv(r'C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250203.trades.csv', low_memory=False)
df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
df['price'] = df['price'].astype(float)
mask = (df['ts_event'] >= '2025-02-03 15:23:00') & (df['ts_event'] < '2025-02-03 15:24:00')
bar = df.loc[mask].copy()
print(f'Trades in bar: {len(bar)}')
print('Price stats:')
print(bar['price'].describe())
# filter out obvious outliers (price > 21500 or < 1000)
bar_clean = bar[(bar['price'] > 1000) & (bar['price'] < 21500)].copy()
print(f'\nRemaining after removing outliers: {len(bar_clean)}')
if len(bar_clean) < len(bar):
    print('Removed outliers:')
    outliers = bar[(bar['price'] <= 1000) | (bar['price'] >= 21500)]
    print(outliers[['ts_event','price','size','side']])
print('\nCleaned price stats:')
print(bar_clean['price'].describe())
print(f'\nRealistic high: {bar_clean[\"price\"].max():.2f}')
print(f'Realistic low: {bar_clean[\"price\"].min():.2f}')
entry = 21229.75
stop = 21198.0
target = 21277.5
print(f'\nEntry: {entry}, target: {target}')
if bar_clean['price'].max() >= target:
    print('✅ Target WOULD be hit realistically')
else:
    print('❌ Target would NOT be hit (realistic high < target)')
if bar_clean['price'].min() <= stop:
    print('❌ Stop WOULD be hit realistically')
else:
    print('✅ Stop would NOT be hit (realistic low > stop)')

# also compute rolling median filter (5 seconds window) to smooth spikes
import warnings
warnings.filterwarnings('ignore')
bar_sorted = bar.sort_values('ts_event')
bar_sorted['roll_median'] = bar_sorted['price'].rolling(window=100, center=True, min_periods=1).median()
bar_sorted['roll_std'] = bar_sorted['price'].rolling(window=100, center=True, min_periods=1).std()
bar_sorted['outlier'] = abs(bar_sorted['price'] - bar_sorted['roll_median']) > 3 * bar_sorted['roll_std']
print('\n--- Rolling statistics ---')
print(f'Median price over bar: {bar_sorted[\"roll_median\"].iloc[-1]:.2f}')
print(f'Std over bar: {bar_sorted[\"roll_std\"].iloc[-1]:.2f}')
print(f'Outliers detected: {bar_sorted[\"outlier\"].sum()}')
if bar_sorted['outlier'].any():
    print('Outlier timestamps:')
    print(bar_sorted[bar_sorted['outlier']][['ts_event','price','roll_median','roll_std']])
realistic = bar_sorted[~bar_sorted['outlier']]
if len(realistic) > 0:
    print(f'\nRealistic range (no outliers): {realistic[\"price\"].min():.2f} - {realistic[\"price\"].max():.2f}')
    if realistic['price'].max() >= target:
        print('✅ Target hit within realistic range')
    else:
        print('❌ Target NOT hit within realistic range')
    if realistic['price'].min() <= stop:
        print('❌ Stop hit within realistic range')
    else:
        print('✅ Stop NOT hit within realistic range')