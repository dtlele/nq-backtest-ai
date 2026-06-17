import json
from collections import defaultdict

stops_by_contracts = defaultdict(list)

with open('agent_memory/trades_log.jsonl', 'r') as f:
    for line in f:
        if not line.strip(): continue
        t = json.loads(line)
        contracts = t.get('contracts', 1)
        entry = t.get('entry')
        stop = t.get('stop')
        if entry and stop:
            dist = abs(entry - stop)
            stops_by_contracts[contracts].append(dist)

print("=== CONTRACTS VS STOP LOSS DISTANCE ===")
for contracts, dists in sorted(stops_by_contracts.items()):
    avg_dist = sum(dists) / len(dists) if dists else 0.0
    print(f"Contracts {contracts}x -> Avg Stop Distance: {avg_dist:.2f} points (Min: {min(dists):.2f}, Max: {max(dists):.2f})")
