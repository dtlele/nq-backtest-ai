import sys, io, os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

import src
# Force full analysis using NotebookLM
src.LIGHT_CONFIDENCE_THRESHOLD = 0 
from src.backtest_runner import run_day
from src.data_loader import list_data_files

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'

def test_day(date_str, prev_date_str):
    files = list_data_files(DATA_DIR)
    target_file = [f for f in files if date_str in f][0]
    prev_file = [f for f in files if prev_date_str in f][0]

    print(f"\n{'='*70}")
    print(f"VERIFICATION: {date_str} (Prev: {prev_date_str})")
    print(f"{'='*70}")

    print("\n--- Building Prev Day VP ---")
    _, prev_vp = run_day(prev_file, dry_run=True, quiet=True)
    
    print(f"\n--- Running {date_str} Analysis ---")
    # We want to see the detailed reasoning for the 10:45 bar specifically
    trades, _ = run_day(target_file, dry_run=False, quiet=False, prev_day_vp=prev_vp)

    print(f"\nRESULT for {date_str}: {len(trades)} trades")
    for t in trades:
        print(f"  {t.direction} | entry={t.entry} stop={t.stop} target={t.target}")
        print(f"  exit={t.exit_price} reason={t.exit_reason} PnL={t.pnl_usd:.0f} USD")
        print(f"  Fabio: {t.fabio_reasoning}")
        print(f"  Andrea: {t.andrea_reasoning}")

if __name__ == "__main__":
    # Test June 26 (previously rejected at 10:45 due to volume 3902 < 4000)
    test_day('20250626', '20250625')
