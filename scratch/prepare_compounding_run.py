import json
import shutil
from pathlib import Path

BASE_DIR = Path(r"c:\Users\Mauro\Documents\nq-backtest")
MEMORY_DIR = BASE_DIR / "agent_memory"

print("=== BACKUP AND RESET FOR NEW COMPILING RUN ===")

# Backup old logs if they are not already backup up or just overwrite backup
for name in ["trades_log.jsonl", "reasoning_log.jsonl"]:
    src = MEMORY_DIR / name
    if src.exists():
        dst = MEMORY_DIR / f"{name}.unfiltered_bak"
        shutil.copy(str(src), str(dst))
        print(f"Backed up {name} to {dst.name}")

# Clear active logs
for name in ["trades_log.jsonl", "reasoning_log.jsonl"]:
    path = MEMORY_DIR / name
    with open(path, 'w', encoding='utf-8') as f:
        pass
    print(f"Cleared active log: {name}")

# Reset session_state.json
session_state = {
    "date": "2025-05-01",
    "ib_high": None,
    "ib_low": None,
    "poc": None,
    "day_type": "unknown",
    "open_trade": None,
    "equity": 50000.0,
    "daily_pnl_usd": 0.0,
    "trade_count_today": 0,
    "session_stopped": False
}

with open(MEMORY_DIR / "session_state.json", 'w', encoding='utf-8') as f:
    json.dump(session_state, f, indent=2)
print("Reset session_state.json to starting equity $50,000.00 on 2025-05-01")
