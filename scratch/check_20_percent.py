import json
from pathlib import Path

log_path = Path("agent_memory/reasoning_log.jsonl")
if log_path.exists():
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get("date") == "20250430":
                    print(f"Time: {data.get('bar_time_et')}")
                    print(f"Day Type: {data.get('day_type')}")
                    reasoning = data.get("fabio_reasoning", "")
                    print(f"Reasoning: {reasoning[:200]}...")
                    # Let's search if STATISTICAL MEMORY ALERT is mentioned in the full raw prompt or response
                    raw_prompt = data.get("fabio_raw", {}).get("prompt", "")
                    if "STATISTICAL" in raw_prompt:
                        print("-> Found STATISTICAL MEMORY ALERT in prompt!")
                    else:
                        print("-> NOT found in prompt.")
                    print("-" * 50)
            except Exception as e:
                print("Error parsing line:", e)
else:
    print("Log path does not exist")
