import sys, os
from pathlib import Path
import pandas as pd
import pytz

# Add project root to path to allow imports
sys.path.append(str(Path(__file__).parent.parent))

from src.data_loader import load_day, list_data_files
from src.bar_aggregator import aggregate_to_bars

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'
VOLUME_THRESHOLD = 20000

def verify_volumes():
    files = list_data_files(DATA_DIR)
    if not files:
        print(f"No files found in {DATA_DIR}")
        return

    print(f"Analyzing {len(files)} files...")
    print(f"{'Date':<12} | {'Time (ET)':<10} | {'Volume':<10}")
    print("-" * 40)

    total_bars_found = 0
    day_counts = {}

    ET = pytz.timezone('America/New_York')

    for i, f in enumerate(files):
        try:
            # Extract date from filename for summary
            fname = Path(f).name
            date_part = fname.split('-')[2].split('.')[0] # e.g. 20250926
            month = date_part[:6]
            
            if (i + 1) % 10 == 0 or i == 0:
                print(f"[{i+1}/{len(files)}] Processing {date_part}...")

            trades = load_day(f)
            bars_m5 = aggregate_to_bars(trades, freq='5min')
            
            # Filter NY session only (09:30 - 16:00 ET)
            ny_bars = []
            for b in bars_m5:
                # Localize/convert to ET to check window
                ts_et = b.timestamp.replace(tzinfo=pytz.UTC).astimezone(ET)
                if 9 <= ts_et.hour <= 16:
                    if ts_et.hour == 9 and ts_et.minute < 30: continue
                    if ts_et.hour == 16 and ts_et.minute > 0: continue
                    ny_bars.append(b)

            found_today = 0
            for b in ny_bars:
                if b.volume >= VOLUME_THRESHOLD:
                    ts_et = b.timestamp.replace(tzinfo=pytz.UTC).astimezone(ET)
                    print(f"  --> FOUND: {date_part} | {ts_et.strftime('%H:%M')} | {b.volume:,}")
                    total_bars_found += 1
                    found_today += 1
            
            day_counts[month] = day_counts.get(month, 0) + found_today
            
        except Exception as e:
            print(f"Error processing {f}: {e}")

    print("\n" + "="*40)
    print(f"FINAL AUDIT SUMMARY (Threshold: {VOLUME_THRESHOLD:,})")
    print("="*40)
    for month, count in sorted(day_counts.items()):
        print(f"Month {month}: {count} candidates found.")
    print(f"Total Institutional Bars across all data: {total_bars_found}")
    print("="*40)

if __name__ == "__main__":
    verify_volumes()
