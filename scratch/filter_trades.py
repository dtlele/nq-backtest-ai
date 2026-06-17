import json
from pathlib import Path

# The current run started around 2026-06-01T13:03:00 UTC
# We will keep only trades logged after this timestamp.
CUTOFF_TIME = "2026-06-01T13:03:00"

file_path = Path("c:/Users/Mauro/Documents/nq-backtest/agent_memory/trades_log.jsonl")
if not file_path.exists():
    print("File does not exist.")
    exit()

backup_path = file_path.with_suffix('.jsonl.bak2')
file_path.rename(backup_path)

kept_trades = 0
with open(backup_path, 'r', encoding='utf-8') as fin, open(file_path, 'w', encoding='utf-8') as fout:
    for line in fin:
        if not line.strip():
            continue
        try:
            trade = json.loads(line)
            logged_at = trade.get('logged_at', '')
            if logged_at > CUTOFF_TIME:
                fout.write(line)
                kept_trades += 1
        except json.JSONDecodeError:
            pass

print(f"Filtered trades_log.jsonl. Kept {kept_trades} trades from the current run.")
