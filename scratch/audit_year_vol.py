import sys, os
from pathlib import Path
import pandas as pd
import pytz

# Add project root to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from src.data_loader import load_day, list_data_files
from src.bar_aggregator import aggregate_to_bars

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'

def audit_year_vol():
    files = list_data_files(DATA_DIR)
    if not files:
        print(f"No files found in {DATA_DIR}")
        return

    print(f"Auditing {len(files)} files for MAX volume and 20k candidates...")
    
    monthly_stats = {}
    ET = pytz.timezone('America/New_York')

    for i, f in enumerate(files):
        try:
            fname = Path(f).name
            date_part = fname.split('-')[2].split('.')[0]
            month = date_part[:6]
            
            if month not in monthly_stats:
                monthly_stats[month] = {"max_vol": 0, "count_20k": 0, "days": 0}
            
            monthly_stats[month]["days"] += 1

            trades = load_day(f)
            bars_m5 = aggregate_to_bars(trades, freq='5min')
            
            # Filter NY window only
            ny_bars = []
            for b in bars_m5:
                ts_et = b.timestamp.replace(tzinfo=pytz.UTC).astimezone(ET)
                if 9 <= ts_et.hour <= 16:
                    if ts_et.hour == 9 and ts_et.minute < 30: continue
                    if ts_et.hour == 16 and ts_et.minute > 0: continue
                    ny_bars.append(b)

            day_max = 0
            count_20k = 0
            for b in ny_bars:
                if b.volume > day_max: day_max = b.volume
                if b.volume >= 20000: count_20k += 1
            
            if day_max > monthly_stats[month]["max_vol"]:
                monthly_stats[month]["max_vol"] = day_max
            
            monthly_stats[month]["count_20k"] += count_20k

            if (i + 1) % 20 == 0:
                print(f"Processed {i+1}/{len(files)} files...")

        except Exception as e:
            pass # Skip errors for speed in this rough audit

    print("\n" + "="*60)
    print(f"{'Month':<10} | {'Days':<6} | {'Max M5 Volume':<15} | {'20k Bars Found'}")
    print("-" * 60)
    for month, stats in sorted(monthly_stats.items()):
        print(f"{month:<10} | {stats['days']:<6} | {stats['max_vol']:<15,} | {stats['count_20k']}")
    print("="*60)

if __name__ == "__main__":
    audit_year_vol()
