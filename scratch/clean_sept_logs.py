import sys
from pathlib import Path

def clean_log(file_path):
    path = Path(file_path)
    if not path.exists():
        return
    lines = path.read_text(encoding='utf-8').splitlines()
    # Keep lines that do NOT contain "2025-09"
    new_lines = [l for l in lines if '"2025-09' not in l]
    path.write_text('\n'.join(new_lines) + ('\n' if new_lines else ''), encoding='utf-8')
    print(f"Cleaned {file_path}: {len(lines)} -> {len(new_lines)} lines")

clean_log('agent_memory/trades_log.jsonl')
clean_log('agent_memory/reasoning_log.jsonl')
