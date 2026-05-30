import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd
from pathlib import Path

# Load all latest trades
trades = []
with open('agent_memory/trades_log.jsonl', encoding='utf-8') as f:
    for line in f:
        t = json.loads(line)
        if t.get('logged_at', '') > '2026-05-30T11:54:00':
            trades.append(t)

print(f"Loaded {len(trades)} trades.")

# Let's see how many were exits by 'stop', 'target', 'early_exit', 'eod'
exit_counts = {}
for t in trades:
    exit_counts[t['exit_reason']] = exit_counts.get(t['exit_reason'], 0) + 1

print("\n--- Exit Reasons ---")
for k, v in exit_counts.items():
    print(f"{k}: {v}")

# How many 'stop' exits were actually TRAILING stops?
# A trailing stop is one where the exit price is DIFFERENT from the original stop.
# But we don't have the original stop. We can infer it:
# If the exit price is very close to the entry price (e.g., RR is > 0 but it's a stop, or loss is small compared to typical)
# Let's count how many trades had a positive PNL but exited via 'stop' (trailed into profit)
# Or negative PNL but very small (trailed to breakeven or small loss).
trailed_into_profit = 0
for t in trades:
    if t['exit_reason'] == 'stop' and t['pnl_ticks'] > 0:
        trailed_into_profit += 1

print(f"Trades exited by 'stop' but with POSITIVE PNL (Trailed into profit): {trailed_into_profit}")

# Let's compute MFE and MAE for all 55 trades by loading the M1 bars!
# This will be very accurate.
from src.data_loader import load_day
from src.bar_aggregator import aggregate_to_bars

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'

# Group trades by date
from collections import defaultdict
trades_by_date = defaultdict(list)
for t in trades:
    trades_by_date[t['date']].append(t)

results = []
for date_str, daily_trades in trades_by_date.items():
    csv_name = f"glbx-mdp3-{date_str.replace('-', '')}.trades.csv"
    csv_path = Path(DATA_DIR) / csv_name
    if not csv_path.exists():
        print(f"Missing {csv_path}")
        continue
    
    trades_raw = load_day(str(csv_path))
    bars = aggregate_to_bars(trades_raw, freq='1min')
    
    for t in daily_trades:
        # Find entry index
        entry_time_utc = pd.to_datetime(t['entry_time'])
        
        # M1 bars list
        trade_bars = [b for b in bars if b.timestamp > entry_time_utc]
        
        mfe_ticks = 0
        mae_ticks = 0
        hit_target_eventually = False
        
        entry = t['entry']
        target = t['target']
        direction = t['direction']
        
        highest_price = entry
        lowest_price = entry
        
        for b in trade_bars:
            if direction == 'long':
                mfe_points = b.high - entry
                mae_points = entry - b.low
                
                if b.high > highest_price: highest_price = b.high
                if b.low < lowest_price: lowest_price = b.low
                
                if b.high >= target:
                    hit_target_eventually = True
                    break
            else:
                mfe_points = entry - b.low
                mae_points = b.high - entry
                
                if b.low < lowest_price: lowest_price = b.low
                if b.high > highest_price: highest_price = b.high
                
                if b.low <= target:
                    hit_target_eventually = True
                    break
                    
        mfe_ticks = abs(highest_price - entry) / 0.25 if direction == 'long' else abs(entry - lowest_price) / 0.25
        mae_ticks = abs(entry - lowest_price) / 0.25 if direction == 'long' else abs(highest_price - entry) / 0.25
        
        t['mfe_ticks'] = mfe_ticks
        t['mae_ticks'] = mae_ticks
        t['hit_target_eventually'] = hit_target_eventually
        results.append(t)

print("\n--- Deep Analysis of Stops ---")
would_have_hit_target = 0
for t in results:
    if t['exit_reason'] == 'stop':
        # If it eventually hit target, it means the stop (or trailed stop) kicked us out prematurely!
        # But wait, did it hit the ORIGINAL stop before hitting the target?
        # We need the original stop to know for sure.
        import re
        orig_stop = None
        
        # Try to extract from fabio_reasoning
        m = re.search(r'stop.*?(?:at|behind).*?([\d\.]+)', t.get('fabio_reasoning', ''), re.IGNORECASE)
        if m:
            try:
                orig_stop = float(m.group(1))
            except: pass
            
        if not orig_stop:
            m = re.search(r'stop.*?([\d\.]+)', t.get('andrea_reasoning', ''), re.IGNORECASE)
            if m:
                try:
                    orig_stop = float(m.group(1))
                except: pass
        
        # If we couldn't find it, we just assume the MAE is what it is.
        t['orig_stop'] = orig_stop
        
        # Check if MAE hit original stop
        hit_orig_stop = False
        if orig_stop:
            if t['direction'] == 'long' and t['entry'] - (t['mae_ticks']*0.25) <= orig_stop:
                hit_orig_stop = True
            if t['direction'] == 'short' and t['entry'] + (t['mae_ticks']*0.25) >= orig_stop:
                hit_orig_stop = True
                
        t['hit_orig_stop'] = hit_orig_stop
        
        if t['hit_target_eventually'] and not hit_orig_stop:
            would_have_hit_target += 1
            print(f"[{t['date']} {t['entry_time'][-14:-9]}] {t['direction'].upper()} Exited by STOP ({t['pnl_ticks']} ticks). "
                  f"BUT it eventually reached TARGET! MAE was {t['mae_ticks']} ticks. Original stop: {orig_stop}")

print(f"\nTotal trades stopped out that WOULD HAVE HIT TARGET (if not trailed or if original stop was safe): {would_have_hit_target}")
