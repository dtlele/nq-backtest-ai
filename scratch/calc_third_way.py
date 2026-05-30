import json

trades = []
with open('agent_memory/trades_log.jsonl', encoding='utf-8') as f:
    for line in f:
        t = json.loads(line)
        if t.get('logged_at', '') > '2026-05-30T11:54:00':
            trades.append(t)

# Load reasoning to get original stops
orig_stops = {}
with open('agent_memory/reasoning_log.jsonl', encoding='utf-8') as f:
    for line in f:
        r = json.loads(line)
        if r.get('trade_stop') is not None:
            k1 = f"{r['date']}_{r['bar_time_utc']}"
            orig_stops[k1] = r['trade_stop']
            k2 = f"{r['date']}_{r['trade_entry']}"
            orig_stops[k2] = r['trade_stop']

import pandas as pd
from pathlib import Path
from collections import defaultdict
DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'

trades_by_date = defaultdict(list)
for t in trades:
    trades_by_date[t['date']].append(t)

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

new_wins = 0
new_losses = 0
new_pnl_usd = 0.0

old_wins = 0
old_losses = 0
old_pnl_usd = 0.0

for date_str, daily_trades in trades_by_date.items():
    csv_name = f"glbx-mdp3-{date_str.replace('-', '')}.trades.csv"
    csv_path = Path(DATA_DIR) / csv_name
    if not csv_path.exists(): continue
    
    df = pd.read_csv(csv_path)
    bars = aggregate(df)
    
    for t in daily_trades:
        old_pnl_usd += t['pnl_usd']
        if t['pnl_usd'] > 0: old_wins += 1
        elif t['pnl_usd'] < 0: old_losses += 1
        
        entry_time_utc = pd.to_datetime(t['entry_time'])
        trade_bars = [b for b in bars if b.timestamp > entry_time_utc]
        
        entry = t['entry']
        direction = t['direction']
        target = t['target']
        
        k1 = f"{t['date']}_{t['entry_time']}"
        k2 = f"{t['date']}_{t['entry']}"
        orig_stop = orig_stops.get(k1, orig_stops.get(k2))
        
        if not orig_stop:
            orig_stop = t['stop']
            
        # THIRD WAY: Add 2 points (8 ticks) buffer to the original stop
        buffer_ticks = 8.0
        new_stop = orig_stop - (buffer_ticks * 0.25) if direction == 'long' else orig_stop + (buffer_ticks * 0.25)
        
        # Calculate new risk ticks to adjust contracts
        new_risk_ticks = abs(entry - new_stop) / 0.25
        # Floor of 60 ticks (15 points)
        effective_risk_ticks = max(60.0, new_risk_ticks)
        
        # Original contracts (approximated from risk $100)
        # Risk = contracts * effective_risk_ticks * 0.5
        # contracts = 100 / (effective_risk_ticks * 0.5)
        new_contracts = max(1, int(100 / (effective_risk_ticks * 0.5)))
        # Apply x2 multiplier if it had one (we can estimate if original contracts > expected)
        orig_risk_ticks = max(40.0, abs(entry - orig_stop) / 0.25)
        expected_orig_contracts = max(1, int(100 / (orig_risk_ticks * 0.5)))
        if t['contracts'] >= expected_orig_contracts * 2:
            new_contracts *= 2
            
        status = 'open'
        exit_price = entry
        
        for b in trade_bars:
            if direction == 'long':
                if b.low <= new_stop:
                    status = 'loss'
                    exit_price = new_stop
                    break
                elif b.high >= target:
                    status = 'win'
                    exit_price = target
                    break
            else:
                if b.high >= new_stop:
                    status = 'loss'
                    exit_price = new_stop
                    break
                elif b.low <= target:
                    status = 'win'
                    exit_price = target
                    break
                    
        if status == 'win':
            new_wins += 1
            new_pnl_usd += (abs(exit_price - entry) / 0.25) * new_contracts * 0.5
        elif status == 'loss':
            new_losses += 1
            new_pnl_usd -= (abs(exit_price - entry) / 0.25) * new_contracts * 0.5

print(f"BASELINE: Win Rate: {old_wins/(old_wins+old_losses):.1%} ({old_wins}W {old_losses}L) | PnL: ${old_pnl_usd:.2f}")
if new_wins + new_losses > 0:
    print(f"THIRD WAY (+2pt Buffer, Floor=15pt): Win Rate: {new_wins/(new_wins+new_losses):.1%} ({new_wins}W {new_losses}L) | PnL: ${new_pnl_usd:.2f}")
else:
    print("No trades simulated.")
