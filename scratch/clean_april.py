import sys
from pathlib import Path
import json

base = Path('c:/Users/Mauro/Documents/nq-backtest/agent_memory')
for filename in ['trades_log.jsonl', 'reasoning_log.jsonl']:
    file_path = base / filename
    if not file_path.exists():
        continue
    
    keep_lines = []
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                # Keep lines that do NOT start with "2025-04-"
                if not data.get('date', '').startswith('2025-04-'):
                    keep_lines.append(line)
            except:
                keep_lines.append(line)

    with open(file_path, 'w', encoding='utf-8-sig') as f:
        f.writelines(keep_lines)
    print(f"Cleaned {filename}, kept {len(keep_lines)} lines.")
