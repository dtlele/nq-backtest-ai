import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent

print(f"[START] Run 1 giorno avviata alle {datetime.now().strftime('%H:%M:%S')}")

result = subprocess.run(
    [sys.executable, '-m', 'src.backtest_runner',
     '--start_date', '20250409', '--max_days', '1'],
    cwd=str(BASE_DIR),
    capture_output=False
)

print(f"[DONE] Run completata con exit code: {result.returncode}")
