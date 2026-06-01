import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load trades
trades = []
with open('agent_memory/trades_log.jsonl', encoding='utf-8') as f:
    for line in f:
        t = json.loads(line)
        if t.get('logged_at', '') > '2026-05-30T11:54:00':
            trades.append(t)

# Note: The 'confidence' logged in trades_log is currently not explicitly saved as a top-level key in some older versions.
# Let's check where confidence is. It's in fabio_confidence or final_confidence in reasoning_log!
# Let's read reasoning_log to map trade_entry to confidence.

conf_map = {}
with open('agent_memory/reasoning_log.jsonl', encoding='utf-8') as f:
    for line in f:
        r = json.loads(line)
        if r.get('trade_entry') is not None and r.get('decision') == 'trade':
            # Map by date + entry time approx or exact entry price
            k1 = f"{r['date']}_{r.get('bar_time_utc')}"
            k2 = f"{r['date']}_{r['trade_entry']}"
            conf = r.get('fabio_confidence', 0)
            conf_map[k1] = conf
            conf_map[k2] = conf

# Process trades
buckets = {
    '65-69': {'W': 0, 'L': 0, 'pnl': 0.0},
    '70-74': {'W': 0, 'L': 0, 'pnl': 0.0},
    '75-79': {'W': 0, 'L': 0, 'pnl': 0.0},
    '80-84': {'W': 0, 'L': 0, 'pnl': 0.0},
    '85-89': {'W': 0, 'L': 0, 'pnl': 0.0},
    '90+':   {'W': 0, 'L': 0, 'pnl': 0.0}
}

found_conf = 0
for t in trades:
    k1 = f"{t['date']}_{t.get('entry_time')}"
    k2 = f"{t['date']}_{t['entry']}"
    conf = conf_map.get(k1, conf_map.get(k2))
    
    # If not found, try to extract from fabio_reasoning string
    if not conf:
        import re
        m = re.search(r'confidence.*?(\d+)', t.get('fabio_reasoning', ''), re.IGNORECASE)
        if m:
            conf = int(m.group(1))
            
    if not conf:
        # Defaults to 65 if completely missing
        conf = 65
    else:
        found_conf += 1
        
    if conf < 70: b = '65-69'
    elif conf < 75: b = '70-74'
    elif conf < 80: b = '75-79'
    elif conf < 85: b = '80-84'
    elif conf < 90: b = '85-89'
    else: b = '90+'
    
    if t['pnl_usd'] > 0:
        buckets[b]['W'] += 1
    elif t['pnl_usd'] < 0:
        buckets[b]['L'] += 1
    else:
        # BE doesn't count towards win/loss but counts for PnL (0)
        pass
        
    buckets[b]['pnl'] += t['pnl_usd']

print(f"Processed {len(trades)} trades. Found exact confidence for {found_conf} trades.")
print("\n--- CONFIDENCE ANALYSIS ---")
for b, stats in buckets.items():
    total = stats['W'] + stats['L']
    if total == 0: continue
    wr = stats['W'] / total
    avg_pnl = stats['pnl'] / total
    print(f"[{b}%] Trades: {total:2d} | WR: {wr:5.1%} ({stats['W']}W {stats['L']}L) | Total PnL: ${stats['pnl']:7.2f} | Avg PnL: ${avg_pnl:6.2f}")

# Plotting
labels = [b for b in buckets.keys() if (buckets[b]['W'] + buckets[b]['L']) > 0]
win_rates = [buckets[b]['W'] / (buckets[b]['W'] + buckets[b]['L']) * 100 for b in labels]
total_pnls = [buckets[b]['pnl'] for b in labels]
trades_counts = [(buckets[b]['W'] + buckets[b]['L']) for b in labels]

fig, ax1 = plt.subplots(figsize=(10, 6))

color = 'tab:blue'
ax1.set_xlabel('Confidence Bucket')
ax1.set_ylabel('Win Rate (%)', color=color)
bars = ax1.bar(labels, win_rates, color=color, alpha=0.6, label='Win Rate %')
ax1.tick_params(axis='y', labelcolor=color)
ax1.set_ylim(0, 100)

# Add text labels on bars
for bar, count in zip(bars, trades_counts):
    yval = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2, yval + 1, f"n={count}", ha='center', va='bottom')

ax2 = ax1.twinx()  
color = 'tab:green'
ax2.set_ylabel('Total PnL ($)', color=color)  
ax2.plot(labels, total_pnls, color=color, marker='o', linewidth=2, label='Total PnL ($)')
ax2.tick_params(axis='y', labelcolor=color)

plt.title('Trade Performance vs Agent Confidence Level', fontsize=14)
fig.tight_layout()  
plt.savefig('C:/Users/Mauro/.gemini/antigravity/brain/e86b7458-2bf7-4121-9908-1844e8f5d6dd/confidence_report.png')
plt.close()

print("Plot saved to artifacts.")
