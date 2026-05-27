import json
import sys
from pathlib import Path

decision_file = Path("agent_memory/human_decisions.jsonl")
decision_file.parent.mkdir(parents=True, exist_ok=True)

new_decision = {
    "key": "95fcaa3531b6632c74b7620538f9e96aeab009ae4b8a34e55af00c85907e3ae2",
    "decision": {
        "direction": "none",
        "confidence": 0,
        "entry": None,
        "stop": None,
        "target": None,
        "setup_type": "none",
        "reasoning": "While the market shows a 'Second Drive' signature with seller absorption at the 22330 highs (10:40 showed -505 delta on a rising candle), the current volume (3512) still fails to meet the 4,000 participation floor. Per Rule 2, we avoid entering during low-participation drifts."
    }
}

with open(decision_file, "a", encoding="utf-8") as f:
    f.write(json.dumps(new_decision) + "\n")

print(f"Appended decision for key: {new_decision['key'][:8]}...")
