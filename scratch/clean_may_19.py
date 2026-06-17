import json
from pathlib import Path
import shutil

MEM_DIR = Path(r"c:\Users\Mauro\Documents\nq-backtest\agent_memory")

# 1. Backups
print("Creating backups...")
for f in ["trades_log.jsonl", "reasoning_log.jsonl", "nlm_pending.jsonl", "session_state.json"]:
    src = MEM_DIR / f
    if src.exists():
        dst = MEM_DIR / f"{f}.pre_may19_clean"
        shutil.copy(src, dst)
        print(f"Backed up {f} to {dst.name}")

# 2. Clean trades_log.jsonl
trades_file = MEM_DIR / "trades_log.jsonl"
if trades_file.exists():
    lines = []
    removed_count = 0
    with open(trades_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                if data.get("date") == "2025-05-19":
                    removed_count += 1
                else:
                    lines.append(line)
    with open(trades_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Removed {removed_count} lines from trades_log.jsonl")

# 3. Clean reasoning_log.jsonl
reasoning_file = MEM_DIR / "reasoning_log.jsonl"
if reasoning_file.exists():
    lines = []
    removed_count = 0
    with open(reasoning_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                if data.get("date") == "2025-05-19":
                    removed_count += 1
                else:
                    lines.append(line)
    with open(reasoning_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Removed {removed_count} lines from reasoning_log.jsonl")

# 4. Clean nlm_pending.jsonl
nlm_file = MEM_DIR / "nlm_pending.jsonl"
if nlm_file.exists():
    lines = []
    removed_count = 0
    with open(nlm_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                if data.get("date") == "2025-05-19":
                    removed_count += 1
                else:
                    lines.append(line)
    with open(nlm_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"Removed {removed_count} lines from nlm_pending.jsonl")

# 5. Modify session_state.json
session_file = MEM_DIR / "session_state.json"
if session_file.exists():
    with open(session_file, "r", encoding="utf-8") as f:
        state = json.load(f)
    
    state["equity"] = 50488.40
    state["date"] = "2025-05-19"
    state["ib_high"] = None
    state["ib_low"] = None
    state["poc"] = None
    state["day_type"] = "unknown"
    state["open_trade"] = None
    state["daily_pnl_usd"] = 0.0
    state["trade_count_today"] = 0
    state["session_stopped"] = False

    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    print("Reset session_state.json to equity=50488.40, date=2025-05-19")
