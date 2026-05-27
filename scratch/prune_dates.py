import json
from pathlib import Path

MEMORY_DIR = Path(r'c:\Users\Mauro\Documents\nq-backtest\agent_memory')
REASONING_LOG = MEMORY_DIR / 'reasoning_log.jsonl'
TRADES_LOG = MEMORY_DIR / 'trades_log.jsonl'

DATES_TO_REMOVE = {'2025-06-04', '2025-06-09', '2025-06-26'}

def prune_dates(file_path):
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    output_lines = []
    removed_count = 0
    total_count = 0

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            total_count += 1
            try:
                data = json.loads(line)
                if data.get('date') in DATES_TO_REMOVE:
                    removed_count += 1
                    continue
                output_lines.append(line)
            except Exception as e:
                print(f"Error parsing line: {e}")
                output_lines.append(line)

    with open(file_path, 'w', encoding='utf-8') as f:
        for line in output_lines:
            f.write(line + '\n')
            
    print(f"Processed {file_path.name}: {total_count} total, {removed_count} removed, {len(output_lines)} remaining.")

if __name__ == "__main__":
    prune_dates(REASONING_LOG)
    prune_dates(TRADES_LOG)
