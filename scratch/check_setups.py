import json
from pathlib import Path

log_path = Path("c:/Users/Mauro/Documents/nq-backtest/agent_memory/reasoning_log.jsonl")
if not log_path.exists():
    print("reasoning_log.jsonl not found")
    exit()

counts = {}
with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            try:
                r = json.loads(line)
                setup = r.get("fabio_setup", "none")
                direction = r.get("fabio_direction", "none")
                conf = r.get("fabio_confidence", 0)
                time_et = r.get("bar_time_et", "")
                
                key = (setup, direction)
                counts[key] = counts.get(key, 0) + 1
                
                if direction != "none":
                    print(f"[{time_et}] Setup: {setup} | Dir: {direction} | Conf: {conf} | Reason: {r.get('fabio_reasoning')[:120]}...")
            except Exception as e:
                print(f"Error: {e}")

print("\nSetup Counts:")
for (setup, direction), count in counts.items():
    print(f"Setup: {setup} | Dir: {direction} | Count: {count}")
