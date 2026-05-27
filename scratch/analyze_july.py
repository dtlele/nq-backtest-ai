import json
from collections import defaultdict

trades_file = r'c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl'

stats = defaultdict(lambda: {'count': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0, 'r_sum': 0.0})
day_stats = defaultdict(lambda: {'pnl': 0.0, 'count': 0})

with open(trades_file, 'r') as f:
    for line in f:
        if not line.strip(): continue
        trade = json.loads(line)
        if '2025-07' not in trade['date']: continue
        
        setup = trade.get('setup_type', 'unknown')
        pnl = trade.get('pnl_usd', 0.0)
        
        stats[setup]['count'] += 1
        stats[setup]['pnl'] += pnl
        if pnl > 0:
            stats[setup]['wins'] += 1
        elif pnl < 0:
            stats[setup]['losses'] += 1
            
        stats[setup]['r_sum'] += trade.get('r_ratio', 0.0)

print("| Setup | Count | Wins | Losses | P&L ($) | Avg R |")
print("|-------|-------|------|--------|---------|-------|")
for setup, data in stats.items():
    avg_r = data['r_sum'] / data['count'] if data['count'] > 0 else 0
    print(f"| {setup} | {data['count']} | {data['wins']} | {data['losses']} | {data['pnl']:.2f} | {avg_r:.2f} |")

print("\n### Loss Analysis (Stop Runs?)")
# Special check for trades stopped out on the same day as a later winner in the same direction
# This would require a more complex check matching dates.
