import json
from collections import defaultdict

counts = defaultdict(lambda: defaultdict(int))

with open('agent_memory/trades_log.jsonl.unfiltered_bak', 'r') as f:
    for line in f:
        if not line.strip(): continue
        t = json.loads(line)
        wall_side = t.get('wall_side', 'none')
        direction = t.get('direction', 'none')
        counts[wall_side][direction] += 1

print("=== WALL SIDE VS TRADE DIRECTION ===")
for side, dirs in counts.items():
    print(f"Wall Side '{side}' -> {dict(dirs)}")
