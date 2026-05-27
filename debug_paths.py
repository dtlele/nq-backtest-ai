from src.agent_memory import LOG_FILE, TRADES_FILE, MEMORY_DIR
from pathlib import Path
print(f"DEBUG - MEMORY_DIR (abs): {MEMORY_DIR.absolute()}")
print(f"DEBUG - LOG_FILE (abs): {LOG_FILE.absolute()}")
print(f"DEBUG - LOG_FILE exists: {LOG_FILE.exists()}")
if LOG_FILE.exists():
    print(f"DEBUG - LOG_FILE size: {LOG_FILE.stat().st_size} bytes")
    with open(LOG_FILE, 'r') as f:
        lines = f.readlines()
        print(f"DEBUG - LOG_FILE lines with '2025-09': {len([l for l in lines if '2025-09' in l])}")
