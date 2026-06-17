import subprocess
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
MEM_DIR = BASE_DIR / 'agent_memory'

print("[CLEANUP] Salvataggio e pulizia vecchi log per evitare residui Telegram...")
for log_file in ['trades_log.jsonl', 'reasoning_log.jsonl', 'quantitative_memory.json', 'run_start_marker.json']:
    src = MEM_DIR / log_file
    if src.exists():
        dst = MEM_DIR / f"{log_file}.bak_before_may_full"
        shutil.copy(src, dst)
        src.unlink() # Elimina per partire da zero

marker = MEM_DIR / 'run_start_marker.json'
marker.write_text(json.dumps({
    'start_time': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    'range': '2025-05-01 → 2025-05-31'
}), encoding='utf-8')
print(f"[START] Run intero Maggio avviata alle {datetime.now().strftime('%H:%M:%S')}")

print("[BACKTEST] Avvio backtest...")
result = subprocess.run(
    [sys.executable, '-m', 'src.backtest_runner',
     '--start_date', '20250501', '--end_date', '20250531'],
    cwd=str(BASE_DIR),
    capture_output=False
)

print(f"[BACKTEST] Completato con exit code: {result.returncode}")

print("[TELEGRAM] Invio notifica finale su Telegram...")
subprocess.run(
    [sys.executable, str(BASE_DIR / 'scratch' / 'telegram_notifier.py')],
    cwd=str(BASE_DIR)
)

print("[DONE] Run completata!")
