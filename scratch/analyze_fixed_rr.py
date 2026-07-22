import json
import pandas as pd
from pathlib import Path

with open('dashboard/public/data/status.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

trades = d.get('ALL_TRADES', [])

print(f"Running offline target optimization on {len(trades)} trades...\n")

targets_to_test = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 3.5]
results = {t: {'wins': 0, 'losses': 0, 'pnl_r': 0.0} for t in targets_to_test}

for t in trades:
    date = t['date']
    direction = t['direction']
    entry_price = t['entry']
    stop_price = t['stop']
    
    risk = abs(entry_price - stop_price)
    
    if risk == 0:
        continue
        
    try:
        date_str = date.replace('-', '')
        df = pd.read_csv(f"C:/Users/Mauro/Documents/nq-backtest-clean/cache_ohlc/{date_str}.csv")
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        entry_time = pd.to_datetime(t['entry_time'])
        future_data = df[df['timestamp'] >= entry_time]
        
        # Test each target
        for target_r in targets_to_test:
            if direction == 'long':
                target_price = entry_price + (risk * target_r)
            else:
                target_price = entry_price - (risk * target_r)
                
            hit_target = False
            hit_stop = False
            
            for idx, row in future_data.iterrows():
                if direction == 'long':
                    if row['low'] <= stop_price:
                        hit_stop = True
                        break
                    if row['high'] >= target_price:
                        hit_target = True
                        break
                else:
                    if row['high'] >= stop_price:
                        hit_stop = True
                        break
                    if row['low'] <= target_price:
                        hit_target = True
                        break
                        
            if hit_target:
                results[target_r]['wins'] += 1
                results[target_r]['pnl_r'] += target_r
            else:
                results[target_r]['losses'] += 1
                results[target_r]['pnl_r'] -= 1.0
                
    except Exception as e:
        pass

print("=== OPTIMIZATION RESULTS (Fixed TP, Fixed SL, No Trailing) ===")
print(f"{'Target (R)':<12} | {'Win Rate':<10} | {'Wins':<5} | {'Losses':<7} | {'Total P&L (R)':<12}")
print("-" * 65)

for target_r in targets_to_test:
    res = results[target_r]
    total_trades = res['wins'] + res['losses']
    if total_trades > 0:
        win_rate = (res['wins'] / total_trades) * 100
        print(f"{target_r:<12.1f} | {win_rate:>5.1f}%     | {res['wins']:<5} | {res['losses']:<7} | {res['pnl_r']:>+8.2f} R")


print("\n\n=== OPTIMIZATION RESULTS (Trailing Stop Logic) ===")
# Let's test a simple trailing stop: if price hits 0.8R, move SL to BE. If 1.5R, lock in 1R.
trail_pnl = 0.0
trail_wins = 0
trail_losses = 0
trail_be = 0

for t in trades:
    date = t['date']
    direction = t['direction']
    entry_price = t['entry']
    stop_price = t['stop']
    risk = abs(entry_price - stop_price)
    
    if risk == 0: continue
    
    try:
        date_str = date.replace('-', '')
        df = pd.read_csv(f"C:/Users/Mauro/Documents/nq-backtest-clean/cache_ohlc/{date_str}.csv")
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        entry_time = pd.to_datetime(t['entry_time'])
        future_data = df[df['timestamp'] >= entry_time]
        
        current_sl = stop_price
        locked_r = -1.0
        
        for idx, row in future_data.iterrows():
            if direction == 'long':
                current_r = (row['high'] - entry_price) / risk
                
                if current_r >= 1.5 and locked_r < 1.0:
                    current_sl = entry_price + risk * 1.0
                    locked_r = 1.0
                elif current_r >= 0.8 and locked_r < 0.0:
                    current_sl = entry_price + 2.0  # Just above BE to cover fees
                    locked_r = 0.0
                    
                if row['low'] <= current_sl:
                    actual_pnl_r = (current_sl - entry_price) / risk
                    trail_pnl += actual_pnl_r
                    if actual_pnl_r > 0.1: trail_wins += 1
                    elif actual_pnl_r < -0.1: trail_losses += 1
                    else: trail_be += 1
                    break
            else:
                current_r = (entry_price - row['low']) / risk
                
                if current_r >= 1.5 and locked_r < 1.0:
                    current_sl = entry_price - risk * 1.0
                    locked_r = 1.0
                elif current_r >= 0.8 and locked_r < 0.0:
                    current_sl = entry_price - 2.0
                    locked_r = 0.0
                    
                if row['high'] >= current_sl:
                    actual_pnl_r = (entry_price - current_sl) / risk
                    trail_pnl += actual_pnl_r
                    if actual_pnl_r > 0.1: trail_wins += 1
                    elif actual_pnl_r < -0.1: trail_losses += 1
                    else: trail_be += 1
                    break
    except Exception as e:
        pass

print(f"Trailing Logic (BE at +0.8R, lock +1.0R at +1.5R):")
print(f"Wins: {trail_wins} | Losses: {trail_losses} | Break-Evens: {trail_be} | Total P&L: {trail_pnl:+.2f} R")
