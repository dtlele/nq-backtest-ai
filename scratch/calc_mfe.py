import json
import pandas as pd
from pathlib import Path
import sys

# No imports needed

with open('dashboard/public/data/status.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

trades = d.get('ALL_TRADES', [])

print(f"Analyzing {len(trades)} trades for MFE...")

results = []

for t in trades:
    date = t['date']
    direction = t['direction']
    entry_price = t['entry']
    stop_price = t['stop']
    
    # Calculate risk points
    risk = abs(entry_price - stop_price)
    
    # Load 1m data for the date
    try:
        # Format date as YYYYMMDD for filename
        date_str = date.replace('-', '')
        df = pd.read_csv(f"C:/Users/Mauro/Documents/nq-backtest-clean/cache_ohlc/{date_str}.csv")
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        entry_time = pd.to_datetime(t['entry_time'])
        
        # Filter data from entry_time to end of day (or until stopped)
        future_data = df[df['timestamp'] >= entry_time]
        
        mfe_pts = 0
        mae_pts = 0
        hit_stop = False
        
        for idx, row in future_data.iterrows():
            if direction == 'long':
                mfe_pts = max(mfe_pts, row['high'] - entry_price)
                if row['low'] <= stop_price:
                    hit_stop = True
                    break
            else:
                mfe_pts = max(mfe_pts, entry_price - row['low'])
                if row['high'] >= stop_price:
                    hit_stop = True
                    break
                    
        mfe_r = mfe_pts / risk if risk > 0 else 0
        results.append(mfe_r)
        print(f"{date} {direction.upper()} @ {entry_time.strftime('%H:%M')} | Risk: {risk:.2f} | MFE Max: {mfe_r:.2f}R | Hit Stop: {hit_stop}")
        
    except Exception as e:
        print(f"Error on {date}: {e}")

if results:
    avg_mfe = sum(results) / len(results)
    print(f"\nAverage MFE (Max Favorable Excursion) across {len(results)} trades: {avg_mfe:.2f}R")
    
    # Let's see how many would have hit 1.5R and 2.0R
    hit_1_5 = sum(1 for r in results if r >= 1.5)
    hit_2_0 = sum(1 for r in results if r >= 2.0)
    hit_3_0 = sum(1 for r in results if r >= 3.0)
    
    print(f"Trades hitting 1.5R: {hit_1_5} ({hit_1_5/len(results)*100:.1f}%)")
    print(f"Trades hitting 2.0R: {hit_2_0} ({hit_2_0/len(results)*100:.1f}%)")
    print(f"Trades hitting 3.0R: {hit_3_0} ({hit_3_0/len(results)*100:.1f}%)")
