import json
import pandas as pd
import matplotlib.pyplot as plt
import os
from pathlib import Path
from collections import defaultdict

# 1. Load latest trades
trades = []
with open('agent_memory/trades_log.jsonl', encoding='utf-8') as f:
    for line in f:
        t = json.loads(line)
        if t.get('logged_at', '') > '2026-05-30T11:54:00':
            trades.append(t)

# 2. Extract reasonings, setups, and rules
# reasoning_log maps by date and bar_time_utc
trade_details = {}
with open('agent_memory/reasoning_log.jsonl', encoding='utf-8') as f:
    for line in f:
        r = json.loads(line)
        if r.get('trade_entry') is not None:
            # Try to match the exact entry time. For pending limit orders, entry_time in trades_log is fill time.
            # But we can match by date and price roughly.
            pass

# Since trades_log also contains fabio_reasoning and fabio_setup, we can just use that!
wins_rules = defaultdict(int)
loss_rules = defaultdict(int)

setup_stats = defaultdict(lambda: {'W': 0, 'L': 0, 'pnl': 0.0})
imbalance_stats = {'W': 0, 'L': 0}
balance_stats = {'W': 0, 'L': 0}

for t in trades:
    is_win = t['pnl_usd'] > 0
    setup = t.get('setup_type', 'unknown')
    if setup == 'unknown':
        # try to extract from reasoning
        if 'hunting' in t.get('fabio_reasoning', '').lower(): setup = 'imbalance_hunting'
        elif 'ibob' in t.get('fabio_reasoning', '').lower(): setup = 'ibob'
        elif 'reversal' in t.get('fabio_reasoning', '').lower(): setup = 'reversal'
        elif 'reload' in t.get('fabio_reasoning', '').lower(): setup = 'trend_continuation'
        
    setup_stats[setup]['pnl'] += t['pnl_usd']
    if is_win:
        setup_stats[setup]['W'] += 1
        if setup == 'imbalance_hunting': imbalance_stats['W'] += 1
        else: balance_stats['W'] += 1
    else:
        setup_stats[setup]['L'] += 1
        if setup == 'imbalance_hunting': imbalance_stats['L'] += 1
        else: balance_stats['L'] += 1
        
    # Extract AMT rules from reasoning
    import re
    rules = re.findall(r'AMT_RULE_\d+', t.get('fabio_reasoning', '') + t.get('andrea_reasoning', ''))
    for r in set(rules):
        if is_win: wins_rules[r] += 1
        else: loss_rules[r] += 1

print("--- RULES USED IN WINS ---")
for r, count in sorted(wins_rules.items(), key=lambda x: -x[1]):
    print(f"{r}: {count} wins")

print("\n--- RULES USED IN LOSSES ---")
for r, count in sorted(loss_rules.items(), key=lambda x: -x[1]):
    print(f"{r}: {count} losses")

# 3. Generate Overlay Plot
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
        b.close = row['close']
        bar_objs.append(b)
    return bar_objs

plt.figure(figsize=(14, 8))

for date_str, daily_trades in trades_by_date.items():
    csv_name = f"glbx-mdp3-{date_str.replace('-', '')}.trades.csv"
    csv_path = Path(DATA_DIR) / csv_name
    if not csv_path.exists(): continue
    
    df = pd.read_csv(csv_path)
    bars = aggregate(df)
    
    for t in daily_trades:
        entry_time_utc = pd.to_datetime(t['entry_time'])
        exit_time_utc = pd.to_datetime(t['exit_time'])
        
        # trade bars
        trade_bars = [b for b in bars if b.timestamp >= entry_time_utc and b.timestamp <= exit_time_utc]
        if not trade_bars: continue
        
        y_vals = []
        for b in trade_bars:
            if t['direction'] == 'long':
                y_vals.append((b.close - t['entry']) / 0.25) # in ticks
            else:
                y_vals.append((t['entry'] - b.close) / 0.25)
                
        x_vals = range(len(y_vals))
        color = 'green' if t['pnl_usd'] > 0 else 'red'
        alpha = 0.5
        linewidth = 1.5
        
        plt.plot(x_vals, y_vals, color=color, alpha=alpha, linewidth=linewidth)
        
        # Plot entry and exit dots
        plt.scatter(0, y_vals[0], color='blue', s=20, zorder=5) # Entry
        plt.scatter(x_vals[-1], y_vals[-1], color=color, s=40, zorder=5, marker='x') # Exit

plt.title('Trade Trajectories (Normalized to Entry Price) - Wins vs Losses', fontsize=16)
plt.xlabel('Minutes since Entry', fontsize=12)
plt.ylabel('Profit/Loss in Ticks', fontsize=12)
plt.axhline(0, color='black', linestyle='--', linewidth=1)
plt.grid(True, alpha=0.3)
os.makedirs('C:/Users/Mauro/.gemini/antigravity/brain/e86b7458-2bf7-4121-9908-1844e8f5d6dd', exist_ok=True)
plt.savefig('C:/Users/Mauro/.gemini/antigravity/brain/e86b7458-2bf7-4121-9908-1844e8f5d6dd/trajectories.png', bbox_inches='tight')
plt.close()

# 4. Generate Bar Chart for Setup Performance
setups = list(setup_stats.keys())
wins = [setup_stats[s]['W'] for s in setups]
losses = [setup_stats[s]['L'] for s in setups]

plt.figure(figsize=(10, 6))
x = range(len(setups))
plt.bar(x, wins, width=0.4, label='Wins', color='green')
plt.bar([i + 0.4 for i in x], losses, width=0.4, label='Losses', color='red')
plt.xticks([i + 0.2 for i in x], setups, rotation=45, ha='right')
plt.title('Performance by Setup Type', fontsize=14)
plt.ylabel('Number of Trades')
plt.legend()
plt.tight_layout()
plt.savefig('C:/Users/Mauro/.gemini/antigravity/brain/e86b7458-2bf7-4121-9908-1844e8f5d6dd/setup_performance.png')
plt.close()

# Save stats to a text file for reporting
with open('C:/Users/Mauro/.gemini/antigravity/brain/e86b7458-2bf7-4121-9908-1844e8f5d6dd/stats_summary.txt', 'w') as f:
    f.write("=== SETUP STATS ===\n")
    for s, stats in setup_stats.items():
        wr = stats['W'] / (stats['W'] + stats['L']) if (stats['W'] + stats['L']) > 0 else 0
        f.write(f"{s}: {stats['W']}W {stats['L']}L (WR: {wr:.1%}) PnL: ${stats['pnl']:.2f}\n")
    f.write(f"\nBalance vs Imbalance:\n")
    f.write(f"IMBALANCE: {imbalance_stats['W']}W {imbalance_stats['L']}L\n")
    f.write(f"BALANCE: {balance_stats['W']}W {balance_stats['L']}L\n")
