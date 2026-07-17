import json
import glob

print("--- AUDIT: CONFIDENCE >= 65 ---")
for file in glob.glob("agent_memory/variants20_logs/*/*.jsonl"):
    var_name = file.split("\\")[-2]
    with open(file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                conf = data.get("fabio_confidence", 0)
                # If trade is opened, it might have trade_entry not null
                if conf >= 65 or data.get("trade_entry") is not None:
                    t = data.get("bar_time_utc", "")
                    d = data.get("fabio_direction", "")
                    r = data.get("fabio_reasoning", "")[:300]
                    print(f"[{var_name}] {t} | Dir: {d} | Conf: {conf}%\nReasoning: {r}...\n")
            except Exception as e:
                pass
print("--- END AUDIT ---")
