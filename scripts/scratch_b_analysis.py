import pandas as pd

tdf = pd.read_csv('output/whale_v8_config_B.csv')
tdf['entry_ts'] = pd.to_datetime(tdf['entry_ts'], utc=True).dt.tz_convert('US/Eastern')

import warnings
warnings.filterwarnings('ignore')
tdf['month'] = tdf['entry_ts'].dt.to_period('M')

monthly = tdf.groupby('month').agg(
    n=('net_pnl', 'count'),
    net=('net_pnl', 'sum'),
    wr=('net_pnl', lambda x: (x > 0).mean() * 100)
)

print("Distribuzione mensile Config B (50-200, wick>=0.5):")
print(monthly.to_string())
print()
print(f"Mesi in perdita: {(monthly['net'] < 0).sum()}")
print(f"WR minima mensile: {monthly['wr'].min():.1f}%")
print(f"WR media mensile: {monthly['wr'].mean():.1f}%")
print(f"Max trades in 1 mese: {monthly['n'].max()}")
print(f"Min trades in 1 mese: {monthly['n'].min()}")

# Sequenze perdenti
tdf_s = tdf.sort_values('entry_ts').reset_index(drop=True)
wins = tdf_s['net_pnl'] > 0
max_loss_streak = cur = 0
for w in wins:
    cur = 0 if w else cur + 1
    max_loss_streak = max(max_loss_streak, cur)
print(f"Max SL consecutivi: {max_loss_streak}")
print(f"  -> Perdita max sequenza: ${max_loss_streak * 87.80:.2f}")
