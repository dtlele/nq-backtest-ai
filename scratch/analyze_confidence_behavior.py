import json
from collections import defaultdict

conf_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0.0, 'total': 0, 'early_exits': 0})

with open('agent_memory/trades_log.jsonl', 'r') as f:
    for line in f:
        if not line.strip(): continue
        t = json.loads(line)
        conf = t.get('final_confidence', 0)
        pnl = t.get('pnl_usd', 0.0)
        exit_reason = t.get('exit_reason', '')
        
        # Bin confidence by 5% increments or groups
        conf_group = (conf // 5) * 5
        
        conf_stats[conf_group]['total'] += 1
        conf_stats[conf_group]['pnl'] += pnl
        if pnl > 0:
            conf_stats[conf_group]['wins'] += 1
        elif pnl < 0:
            conf_stats[conf_group]['losses'] += 1
            
        if exit_reason.startswith('early'):
            conf_stats[conf_group]['early_exits'] += 1

print("=== CONFIDENCE LEVEL PERFORMANCE ===")
for conf, stats in sorted(conf_stats.items()):
    tot = stats['total']
    wr = (stats['wins'] / tot) * 100 if tot > 0 else 0.0
    avg_pnl = stats['pnl'] / tot if tot > 0 else 0.0
    early_pct = (stats['early_exits'] / tot) * 100 if tot > 0 else 0.0
    print(f"Confidence {conf}% -> {stats['wins']} Wins, {stats['losses']} Losses (WR: {wr:.1f}%) | Total PnL: ${stats['pnl']:.2f} | Avg PnL: ${avg_pnl:.2f} | Early Exits: {stats['early_exits']} ({early_pct:.1f}%)")
