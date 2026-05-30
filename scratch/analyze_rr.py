import json
import pandas as pd
from pathlib import Path
import sys

trades = []
with open('agent_memory/trades_log.jsonl', encoding='utf-8') as f:
    for line in f:
        t = json.loads(line)
        if t.get('logged_at', '') > '2026-05-30T11:54:00':
            trades.append(t)

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'

from collections import defaultdict
trades_by_date = defaultdict(list)
for t in trades:
    trades_by_date[t['date']].append(t)

# Mock aggregate function since we are not importing src
def aggregate(trades_df):
    trades_df['ts'] = pd.to_datetime(trades_df['ts_recv'], unit='ns', utc=True)
    trades_df.set_index('ts', inplace=True)
    bars = trades_df['price'].resample('1min').agg({'first', 'max', 'min', 'last'}).rename(
        columns={'first': 'open', 'max': 'high', 'min': 'low', 'last': 'close'}
    ).dropna()
    class Bar: pass
    bar_objs = []
    for ts, row in bars.iterrows():
        b = Bar()
        b.timestamp = ts
        b.high = row['high']
        b.low = row['low']
        bar_objs.append(b)
    return bar_objs

results = []
for date_str, daily_trades in trades_by_date.items():
    csv_name = f"glbx-mdp3-{date_str.replace('-', '')}.trades.csv"
    csv_path = Path(DATA_DIR) / csv_name
    if not csv_path.exists(): continue
    
    df = pd.read_csv(csv_path)
    bars = aggregate(df)
    
    for t in daily_trades:
        entry_time_utc = pd.to_datetime(t['entry_time'])
        trade_bars = [b for b in bars if b.timestamp > entry_time_utc]
        
        entry = t['entry']
        direction = t['direction']
        
        highest_price = entry
        lowest_price = entry
        
        for b in trade_bars:
            if b.high > highest_price: highest_price = b.high
            if b.low < lowest_price: lowest_price = b.low
                
        mfe_ticks = abs(highest_price - entry) / 0.25 if direction == 'long' else abs(entry - lowest_price) / 0.25
        t['mfe_ticks'] = mfe_ticks
        results.append(t)

# Analyze R:R
print("--- Stop Loss Analysis ---")
for t in results:
    if t['exit_reason'] == 'stop':
        # What was the initial risk?
        risk_ticks = abs(t['pnl_ticks']) # Assuming original stop was hit
        if risk_ticks == 0: continue
        
        max_rr = t['mfe_ticks'] / risk_ticks
        
        if max_rr > 0.5:
            print(f"[{t['date']} {t['entry_time'][-14:-9]}] {t['direction'].upper()} STOPPED. Max R:R reached: {max_rr:.2f} (MFE: {t['mfe_ticks']} ticks)")

