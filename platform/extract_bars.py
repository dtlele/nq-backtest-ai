import os
import glob
import json
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import sys

# Ensure src is accessible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_loader import load_day
from src.bar_aggregator import aggregate_to_bars

ARCHIVE_DIR = r"C:\Users\Mauro\Documents\databento-data"
OUTPUT_JSON = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'all_bars.json'))

def main():
    print(f"Scanning {ARCHIVE_DIR} for trades.csv...")
    files = sorted(glob.glob(os.path.join(ARCHIVE_DIR, '*.trades.csv')))
    # No filter: process all available days
    
    if not files:
        print("No CSVs found for Sept/Oct.")
        return

    all_bars_data = []

    for fpath in files:
        filename = os.path.basename(fpath)
        print(f"Processing {filename}...")
        try:
            trades = load_day(fpath)
            if not trades:
                continue
            
            bars = aggregate_to_bars(trades, freq='5min')
            
            for b in bars:
                dt_utc = b.timestamp.astimezone(timezone.utc)
                big_trades_list = []
                for t in b.big_trades:
                    big_trades_list.append({
                        "ts": t.ts_event.isoformat(),
                        "price": t.price,
                        "size": t.size,
                        "side": t.side
                    })
                bar_dict = {
                    "time": int(dt_utc.timestamp()), # For lightweight charts
                    "bar_time_utc": dt_utc.isoformat(),
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                    "delta": b.delta,
                    "big_trades": big_trades_list
                }
                all_bars_data.append(bar_dict)
                
        except Exception as e:
            print(f"Error processing {filename}: {e}")

    # Sort just in case
    all_bars_data.sort(key=lambda x: x["time"])

    with open(OUTPUT_JSON, "w") as f:
        json.dump(all_bars_data, f)
        
    print(f"Successfully saved {len(all_bars_data)} M5 bars to {OUTPUT_JSON}")

if __name__ == '__main__':
    main()
