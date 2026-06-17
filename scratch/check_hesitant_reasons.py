import json
from pathlib import Path

log_path = Path("agent_memory/reasoning_log.jsonl")
if log_path.exists():
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                conf = data.get("fabio_confidence")
                if conf in [70, 65]:
                    print(f"Date: {data.get('date')} | Time: {data.get('bar_time_et')} | Conf: {conf} | Setup: {data.get('fabio_setup')}")
                    print(f"Reason: {data.get('fabio_reasoning')}")
                    print("-" * 80)
            except:
                pass
else:
    print("Log file not found")
