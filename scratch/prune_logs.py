import json
from pathlib import Path
import shutil
from datetime import datetime

MEMORY_DIR = Path(r'c:\Users\Mauro\Documents\nq-backtest\agent_memory')
REASONING_LOG = MEMORY_DIR / 'reasoning_log.jsonl'
TRADES_LOG = MEMORY_DIR / 'trades_log.jsonl'

def prune_reasoning_log():
    if not REASONING_LOG.exists():
        print(f"File not found: {REASONING_LOG}")
        return

    # Backup
    backup_path = REASONING_LOG.with_suffix('.jsonl.bak')
    shutil.copy(REASONING_LOG, backup_path)
    print(f"Backup created: {backup_path}")

    seen = {} # key: (date, bar_time_utc), value: full_line
    count_before = 0
    
    with open(REASONING_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            count_before += 1
            try:
                data = json.loads(line)
                key = (data.get('date'), data.get('bar_time_utc'))
                # We keep the LAST one (most recent attempt)
                seen[key] = line
            except Exception as e:
                print(f"Error parsing line: {e}")

    with open(REASONING_LOG, 'w', encoding='utf-8') as f:
        for line in seen.values():
            f.write(line + '\n')
            
    print(f"Pruned reasoning_log: {count_before} -> {len(seen)} lines.")

def prune_trades_log():
    if not TRADES_LOG.exists():
        print(f"File not found: {TRADES_LOG}")
        return

    # Backup
    backup_path = TRADES_LOG.with_suffix('.jsonl.bak')
    shutil.copy(TRADES_LOG, backup_path)
    print(f"Backup created: {backup_path}")

    seen = {} # key: (date, entry_time), value: full_line
    count_before = 0
    
    with open(TRADES_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            count_before += 1
            try:
                data = json.loads(line)
                key = (data.get('date'), data.get('entry_time'))
                seen[key] = line
            except Exception as e:
                print(f"Error parsing line: {e}")

    with open(TRADES_LOG, 'w', encoding='utf-8') as f:
        for line in seen.values():
            f.write(line + '\n')
            
    print(f"Pruned trades_log: {count_before} -> {len(seen)} lines.")

if __name__ == "__main__":
    prune_reasoning_log()
    prune_trades_log()
