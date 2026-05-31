"""
Script wrapper che:
1. Scrive il marker di avvio run
2. Pulisce la cache solo per le date selezionate
3. Lancia il backtest 3-15 Aprile 2025
4. Avvia il cron Telegram ogni 5 minuti in background
"""
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent

# ── 1. Scrivi marker di avvio ────────────────────────────────────────────
marker = BASE_DIR / 'agent_memory' / 'run_start_marker.json'
marker.parent.mkdir(parents=True, exist_ok=True)
marker.write_text(json.dumps({
    'start_time': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    'range': '2025-04-03 → 2025-04-15'
}), encoding='utf-8')
print(f"[START] Run avviata alle {datetime.now().strftime('%H:%M:%S')} — range: 3-15 Aprile 2025")

# ── 2. Lancia il backtest ────────────────────────────────────────────────
print("[BACKTEST] Avvio backtest 3-15 Aprile 2025...")
result = subprocess.run(
    [sys.executable, '-m', 'src.backtest_runner',
     '--start_date', '20250403', '--end_date', '20250415'],
    cwd=str(BASE_DIR),
    capture_output=False
)

print(f"[BACKTEST] Completato con exit code: {result.returncode}")

# ── 3. Notifica Telegram finale ─────────────────────────────────────────
print("[TELEGRAM] Invio notifica finale su Telegram...")
subprocess.run(
    [sys.executable, str(BASE_DIR / 'scratch' / 'telegram_notifier.py')],
    cwd=str(BASE_DIR)
)

print("[DONE] Run completata!")
