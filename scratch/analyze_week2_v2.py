import json
from pathlib import Path

filepath = "agent_memory/trades_log.jsonl"
if Path(filepath).exists():
    with open(filepath, 'r') as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                dt = data.get('entry_time', '')[:16]
                direction = data.get('direction', '')
                pnl = data.get('pnl_usd', 0)
                reason = data.get('fabio_reasoning', '')
                print(f"[{dt}] {direction.upper()} | PnL: ${pnl}")
                print(f"  Fabio: {reason}")
            except Exception:
                pass
