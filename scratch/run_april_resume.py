import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
MEM_DIR = BASE_DIR / 'agent_memory'

print("[RESUME] Ripresa backtest dal 3 Aprile. Nessun log cancellato!")
marker = MEM_DIR / 'run_start_marker.json'
if marker.exists():
    try:
        data = json.loads(marker.read_text(encoding='utf-8'))
        data['resume_time'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        marker.write_text(json.dumps(data), encoding='utf-8')
    except Exception:
        pass

result = subprocess.run(
    [sys.executable, '-m', 'src.backtest_runner',
     '--start_date', '20250403', '--end_date', '20250430'],
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
