import json
from pathlib import Path
import shutil

MEMORY_DIR = Path(r'c:\Users\Mauro\Documents\nq-backtest\agent_memory')
REASONING_LOG = MEMORY_DIR / 'reasoning_log.jsonl'
TRADES_LOG = MEMORY_DIR / 'trades_log.jsonl'

def reset_month(file_path, month_str):
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    # Backup
    backup_path = file_path.with_suffix(f'.jsonl.bak_{month_str.replace("-", "")}')
    shutil.copy(file_path, backup_path)
    print(f"Backup created: {backup_path}")

    kept_lines = []
    removed_count = 0
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                data = json.loads(line)
                # Check if date starts with the month string (e.g. 2025-07)
                if data.get('date', '').startswith(month_str):
                    removed_count += 1
                else:
                    kept_lines.append(line)
            except Exception as e:
                print(f"Error parsing line: {e}")
                kept_lines.append(line)

    with open(file_path, 'w', encoding='utf-8') as f:
        for line in kept_lines:
            f.write(line + '\n')
            
    print(f"Reset {file_path.name}: Removed {removed_count} lines for {month_str}.")

if __name__ == "__main__":
    # Reset July 2025
    reset_month(REASONING_LOG, "2025-07")
    reset_month(TRADES_LOG, "2025-07")
