import json
import pandas as pd
from pathlib import Path

# Load all latest trades
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
        b.close = row['close']
        bar_objs.append(b)
    return bar_objs

# Baseline metrics
base_wins = 0
base_losses = 0
base_pnl_usd = 0.0

# Scen 1: Wider Stop (+12 ticks = 3 points)
s1_wins = 0
s1_losses = 0
s1_pnl_usd = 0.0

# Scen 2: Early BE (BE at 0.5 R)
s2_wins = 0
s2_losses = 0
s2_be = 0
s2_pnl_usd = 0.0

for date_str, daily_trades in trades_by_date.items():
    csv_name = f"glbx-mdp3-{date_str.replace('-', '')}.trades.csv"
    csv_path = Path(DATA_DIR) / csv_name
    if not csv_path.exists(): continue
    
    df = pd.read_csv(csv_path)
    bars = aggregate(df)
    
    for t in daily_trades:
        base_pnl_usd += t['pnl_usd']
        if t['pnl_usd'] > 0: base_wins += 1
        elif t['pnl_usd'] < 0: base_losses += 1
        
        entry_time_utc = pd.to_datetime(t['entry_time'])
        trade_bars = [b for b in bars if b.timestamp > entry_time_utc]
        
        entry = t['entry']
        direction = t['direction']
        target = t['target']
        contracts = t.get('contracts', 1)
        tick_val = 0.5 # MNQ
        
        # Estimate original stop from current PnL if it was a loss
        orig_stop = t['stop'] # approximation
        if t['exit_reason'] == 'stop':
            if direction == 'long': orig_stop = entry - (abs(t['pnl_ticks']) * 0.25)
            else: orig_stop = entry + (abs(t['pnl_ticks']) * 0.25)
            
        risk_ticks = abs(entry - orig_stop) / 0.25 if entry != orig_stop else 40.0
        
        # S1: Wider Stop (add 16 ticks = 4 points buffer)
        s1_stop = orig_stop - (16 * 0.25) if direction == 'long' else orig_stop + (16 * 0.25)
        
        s1_status = 'open'
        s1_exit_price = entry
        
        s2_stop = orig_stop
        s2_status = 'open'
        s2_exit_price = entry
        s2_be_activated = False
        
        for b in trade_bars:
            # S1 SIM
            if s1_status == 'open':
                if direction == 'long':
                    if b.low <= s1_stop:
                        s1_status = 'loss'
                        s1_exit_price = s1_stop
                    elif b.high >= target:
                        s1_status = 'win'
                        s1_exit_price = target
                else:
                    if b.high >= s1_stop:
                        s1_status = 'loss'
                        s1_exit_price = s1_stop
                    elif b.low <= target:
                        s1_status = 'win'
                        s1_exit_price = target
                        
            # S2 SIM
            if s2_status == 'open':
                if direction == 'long':
                    # check if it hits BE trigger first
                    if not s2_be_activated and b.high >= entry + (risk_ticks * 0.5 * 0.25):
                        s2_be_activated = True
                        s2_stop = entry # Move to BE
                        
                    if b.low <= s2_stop:
                        s2_status = 'be' if s2_be_activated else 'loss'
                        s2_exit_price = s2_stop
                    elif b.high >= target:
                        s2_status = 'win'
                        s2_exit_price = target
                else:
                    if not s2_be_activated and b.low <= entry - (risk_ticks * 0.5 * 0.25):
                        s2_be_activated = True
                        s2_stop = entry # Move to BE
                        
                    if b.high >= s2_stop:
                        s2_status = 'be' if s2_be_activated else 'loss'
                        s2_exit_price = s2_stop
                    elif b.low <= target:
                        s2_status = 'win'
                        s2_exit_price = target
        
        # Calculate PnLs
        if s1_status == 'open': s1_status = 'eod'
        if s2_status == 'open': s2_status = 'eod'
        
        if s1_status == 'win':
            s1_wins += 1
            s1_pnl_usd += (abs(s1_exit_price - entry) / 0.25) * contracts * tick_val
        elif s1_status == 'loss':
            s1_losses += 1
            s1_pnl_usd -= (abs(s1_exit_price - entry) / 0.25) * contracts * tick_val
            
        if s2_status == 'win':
            s2_wins += 1
            s2_pnl_usd += (abs(s2_exit_price - entry) / 0.25) * contracts * tick_val
        elif s2_status == 'loss':
            s2_losses += 1
            s2_pnl_usd -= (abs(s2_exit_price - entry) / 0.25) * contracts * tick_val
        elif s2_status == 'be':
            s2_be += 1
            # 0 PnL (excluding commissions)

print(f"=== BASELINE ===")
print(f"Wins: {base_wins}, Losses: {base_losses}")
print(f"Win Rate: {base_wins / (base_wins + base_losses):.1%}")
print(f"PnL USD: ${base_pnl_usd:.2f}")

print(f"\n=== SCENARIO 1: WIDER STOPS (+4 points buffer) ===")
print(f"Wins: {s1_wins}, Losses: {s1_losses}")
print(f"Win Rate: {s1_wins / (s1_wins + s1_losses) if (s1_wins + s1_losses) > 0 else 0:.1%}")
print(f"PnL USD: ${s1_pnl_usd:.2f} (Delta: ${s1_pnl_usd - base_pnl_usd:.2f})")

print(f"\n=== SCENARIO 2: EARLY BREAKEVEN (Trail to BE at 0.5R) ===")
print(f"Wins: {s2_wins}, Losses: {s2_losses}, BEs: {s2_be}")
total_s2 = s2_wins + s2_losses + s2_be
print(f"Win Rate: {s2_wins / total_s2 if total_s2 > 0 else 0:.1%}")
print(f"Loss Rate: {s2_losses / total_s2 if total_s2 > 0 else 0:.1%}")
print(f"PnL USD: ${s2_pnl_usd:.2f} (Delta: ${s2_pnl_usd - base_pnl_usd:.2f})")
