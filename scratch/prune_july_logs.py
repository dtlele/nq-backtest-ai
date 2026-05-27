import json
from pathlib import Path

log_path = Path('agent_memory/reasoning_log.jsonl')
if log_path.exists():
    lines = log_path.read_text(encoding='utf-8').splitlines()
    # Filter out July entries (2025-07)
    new_lines = [l for l in lines if '"date": "2025-07-' not in l]
    log_path.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
    print(f"Pruned {len(lines) - len(new_lines)} entries from reasoning_log.jsonl")
else:
    print("Log not found.")
