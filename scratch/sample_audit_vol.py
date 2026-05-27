import sys, os
from pathlib import Path
import pandas as pd
import pytz

# Add project root to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from src.data_loader import load_day
from src.bar_aggregator import aggregate_to_bars

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'

# Sampled files from start, middle and recent data
SAMPLED_FILES = [
    'glbx-mdp3-20250102.trades.csv', # Jan peak
    'glbx-mdp3-20250106.trades.csv',
    'glbx-mdp3-20250430.trades.csv', # April peak
    'glbx-mdp3-20250502.trades.csv',
    'glbx-mdp3-20250828.trades.csv', # August peak (Low volatility?)
    'glbx-mdp3-20250917.trades.csv'  # September peak (FOMC?)
]

def sample_audit():
    print(f"{'File Date':<12} | {'Max M5 Vol':<12} | {'Avg NY Vol':<12}")
    print("-" * 45)
    
    ET = pytz.timezone('America/New_York')

    for fname in SAMPLED_FILES:
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath): continue
        
        try:
            trades = load_day(fpath)
            bars_m5 = aggregate_to_bars(trades, freq='5min')
            
            # Filter NY window
            ny_bars = []
            for b in bars_m5:
                ts_et = b.timestamp.replace(tzinfo=pytz.UTC).astimezone(ET)
                if 9 <= ts_et.hour <= 16:
                    if ts_et.hour == 9 and ts_et.minute < 30: continue
                    if ts_et.hour == 16 and ts_et.minute > 0: continue
                    ny_bars.append(b)
            
            if not ny_bars: continue
            
            volumes = [b.volume for b in ny_bars]
            max_v = max(volumes)
            avg_v = sum(volumes) / len(volumes)
            
            date_part = fname.split('-')[2].split('.')[0]
            print(f"{date_part:<12} | {max_v:<12,} | {avg_v:<12,.0f}")
            
        except Exception as e:
            print(f"Error {fname}: {e}")

if __name__ == "__main__":
    sample_audit()
