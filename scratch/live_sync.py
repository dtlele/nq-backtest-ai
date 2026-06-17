import time
import os
import subprocess
from pathlib import Path

MEMORY_DIR = Path("c:/Users/Mauro/Documents/nq-backtest/agent_memory")
FILES_TO_WATCH = [
    MEMORY_DIR / "trades_log.jsonl",
    MEMORY_DIR / "session_state.json",
    MEMORY_DIR / "reasoning_log.jsonl"
]
SCRIPT_TO_RUN = "scratch/restore_mockdata.py"

print("Avvio sincronizzazione live per la dashboard...")
print(f"In ascolto per modifiche in {MEMORY_DIR}...")

def get_total_mtime():
    total = 0.0
    for f in FILES_TO_WATCH:
        if f.exists():
            total += f.stat().st_mtime
    return total

last_mtime = get_total_mtime()

while True:
    try:
        current_mtime = get_total_mtime()
        if current_mtime != last_mtime:
            print("Nuovi dati rilevati! Aggiorno la dashboard...")
            # Prima esportiamo i json del grafico (skips se gia esistono)
            subprocess.run(["python", "scratch/export_dashboard_data.py"])
            # Poi aggiorniamo i dati React
            subprocess.run(["python", SCRIPT_TO_RUN])
            last_mtime = current_mtime
    except Exception as e:
        print(f"Errore durante la sincronizzazione: {e}")
    
    time.sleep(2)
