import sys, os
from pathlib import Path
import pandas as pd
import pytz

# Add project root to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from src.data_loader import load_day
from src.bar_aggregator import aggregate_to_bars
from src.session_context import build_session_context, filter_ny_window
from src.candidate_detector import detect_candidates
from src.volume_profile import compute_volume_profile

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'
F_PATH = os.path.join(DATA_DIR, 'glbx-mdp3-20250828.trades.csv')

def debug_aug_28():
    ET = pytz.timezone('America/New_York')
    print("DEBUGGING AUGUST 28, 2025")
    print("-" * 30)
    
    trades = load_day(F_PATH)
    bars_m5 = aggregate_to_bars(trades, freq='5min')
    
    # 1. Look for the 24k bar
    found_24k = None
    for b in bars_m5:
        if b.volume >= 20000:
            ts_et = b.timestamp.replace(tzinfo=pytz.UTC).astimezone(ET)
            print(f"FOUND 24K BAR: {ts_et.strftime('%H:%M ET')} | Volume: {b.volume:,}")
            found_24k = b
            
    # 2. Check Candidate Detection
    # To detect candidates we need the session context
    from src.session_context import filter_overnight_window
    bars_m1 = aggregate_to_bars(trades, freq='1min')
    bars_m1_overnight = filter_overnight_window(bars_m1)
    vp = compute_volume_profile(bars_m1_overnight)
    
    bars_m1_ny = filter_ny_window(bars_m1)
    ctx = build_session_context("2025-08-28", bars_m1_ny, vp)
    
    ny_bars_m5 = filter_ny_window(bars_m5)
    candidates = detect_candidates(ny_bars_m5, ctx)
    
    print(f"\nCandidates detected in NY Window: {len(candidates)}")
    for c in candidates:
        ts_et = c.bar.timestamp.replace(tzinfo=pytz.UTC).astimezone(ET)
        print(f"  Candidate at {ts_et.strftime('%H:%M ET')} | Vol: {c.bar.volume:,} | Setup: {c.setup_type if hasattr(c, 'setup_type') else '?'}")

if __name__ == "__main__":
    debug_aug_28()
