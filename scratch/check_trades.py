import json
from pathlib import Path

trades_file = Path('agent_memory/trades_log.jsonl')
if trades_file.exists():
    with open(trades_file) as f:
        for line in f:
            if line.strip():
                t = json.loads(line)
                print(t.get('date'), t.get('direction'), t.get('entry'), t.get('exit_price'), t.get('pnl_usd'))
                print('  entry_time:', t.get('entry_time'))
                print('  exit_time:', t.get('exit_time'))
