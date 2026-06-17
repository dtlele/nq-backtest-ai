import json
from pathlib import Path

log_path = Path("agent_memory/reasoning_log.jsonl")
if log_path.exists():
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                andrea_reasoning = data.get("andrea_reasoning")
                if andrea_reasoning and andrea_reasoning != "fabio_only_skip_andrea":
                    # Check if it was rejected or accepted
                    decision = data.get("decision")
                    print(f"Date: {data.get('date')} | Time: {data.get('bar_time_et')} | Decision: {decision}")
                    print(f"Fabio Setup: {data.get('fabio_setup')} | Direction: {data.get('fabio_direction')} | Conf: {data.get('fabio_confidence')}")
                    print(f"Fabio Reasoning: {data.get('fabio_reasoning')[:120]}...")
                    print(f"Andrea Reasoning: {andrea_reasoning}")
                    print("-" * 80)
            except Exception as e:
                pass
else:
    print("Log file not found")
