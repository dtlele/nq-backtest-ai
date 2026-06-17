import json
from collections import defaultdict

sizes = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0.0, 'total': 0})

with open('agent_memory/trades_log.jsonl', 'r') as f:
    for line in f:
        if not line.strip(): continue
        t = json.loads(line)
        size = t.get('contracts', 1)
        pnl = t.get('pnl_usd', 0.0)
        
        sizes[size]['total'] += 1
        sizes[size]['pnl'] += pnl
        if pnl > 0:
            sizes[size]['wins'] += 1
        elif pnl < 0:
            sizes[size]['losses'] += 1

print("=== POSITION SIZING PERFORMANCE ===")
for size, stats in sorted(sizes.items()):
    tot = stats['total']
    wr = (stats['wins'] / tot) * 100 if tot > 0 else 0.0
    avg_pnl = stats['pnl'] / tot if tot > 0 else 0.0
    print(f"Size {size}x -> {stats['wins']} Wins, {stats['losses']} Losses (WR: {wr:.1f}%) | Total PnL: ${stats['pnl']:.2f} | Avg PnL: ${avg_pnl:.2f}")
