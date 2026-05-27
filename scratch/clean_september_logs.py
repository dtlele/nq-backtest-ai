import json
from pathlib import Path

def clean_logs(month_prefix="2025-09"):
    log_files = [
        "agent_memory/trades_log.jsonl",
        "agent_memory/reasoning_log.jsonl"
    ]
    
    import shutil
    backup_dir = Path("agent_memory/archive_sept_audit")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    for log_path in log_files:
        p = Path(log_path)
        if p.exists():
            backup_p = backup_dir / p.name
            print(f"Backing up {log_path} to {backup_p}")
            shutil.copy2(p, backup_p)

    for log_path in log_files:
        p = Path(log_path)
        with open(p, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        original_count = len(lines)
        # Keep lines that DON'T contain the month_prefix
        # Note: We check if it's in the line string at all, which works for JSONL timestamps
        new_lines = [line for line in lines if month_prefix not in line]
        
        with open(p, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        print(f"  Removed {original_count - len(new_lines)} lines.")

if __name__ == "__main__":
    clean_logs()
