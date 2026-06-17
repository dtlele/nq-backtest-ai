import json
from pathlib import Path
from collections import Counter

log_path = Path("agent_memory/reasoning_log.jsonl")
if log_path.exists():
    confidences = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                conf = data.get("fabio_confidence")
                if conf is not None:
                    confidences.append(conf)
            except:
                pass
                
    print(f"Total confidences analyzed: {len(confidences)}")
    c = Counter(confidences)
    print("Confidences distribution (Sorted by confidence level):")
    for k in sorted(c.keys(), reverse=True):
        print(f"  Conf {k}: {c[k]} times")
else:
    print("Log file not found")
