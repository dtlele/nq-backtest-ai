import json
from pathlib import Path

for name in ['agent_memory/reasoning_log.jsonl', 'agent_memory/trades_log.jsonl']:
    path = Path(name)
    if not path.exists():
        continue
    with open(path, encoding='utf-8') as f:
        for idx, line in enumerate(f):
            if 'vah' in line.lower() or 'value area' in line.lower():
                try:
                    data = json.loads(line)
                    date = data.get("date")
                    time_val = data.get("bar_time_et") or data.get("entry_time")
                    reason = data.get('reasoning') or data.get('fabio') or data.get('no_trade_reason')
                    print(f"{name} L{idx}: date={date}, time={time_val}")
                    print(f"  REASON: {reason}\n")
                except Exception as e:
                    pass
