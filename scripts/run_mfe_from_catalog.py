"""
Backtest B — Fast MFE Analysis from Zone Catalog
Reads the generated zone catalog and simulates trade management by scanning ticks.
Extremely fast because it only processes ticks after the entry signal.
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
import pytz

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.data_loader import load_day

DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
NY_TZ = pytz.timezone("America/New_York")

def simulate_trades_from_catalog(catalog_path: str):
    if not os.path.exists(catalog_path):
        print(f"Error: Catalog not found at {catalog_path}")
        return

    with open(catalog_path, "r", encoding="utf-8") as f:
        all_zones = json.load(f)

    print(f"Loaded {len(all_zones)} zones from catalog.")

    # Group zones by date
    zones_by_date = {}
    for z in all_zones:
        d = z["date"]
        if d not in zones_by_date:
            zones_by_date[d] = []
        zones_by_date[d].append(z)

    processed_trades = []
    
    print("Simulating trades tick-by-tick from entry...")
    start_time = time.time()
    
    for date_str in sorted(zones_by_date.keys()):
        day_zones = sorted(zones_by_date[date_str], key=lambda x: x["time"])
        
        # Apply max 2 trades per day rule
        day_trades_to_take = day_zones[:2]
        
        # Need to load the day's data
        # Find the correct file for this date
        pattern = os.path.join(DATA_DIR, f"*2025{date_str[4:]}*.trades.csv") if len(date_str) == 8 else os.path.join(DATA_DIR, f"*{date_str}*.trades.csv")
        matching_files = glob.glob(pattern) if 'glob' in globals() else []
        import glob
        matching_files = glob.glob(os.path.join(DATA_DIR, f"*{date_str}*.trades.csv"))
        if not matching_files:
            continue
            
        filepath = matching_files[0]
        raw_trades = load_day(filepath)
        if raw_trades is None or len(raw_trades) == 0:
            continue
            
        trades_df = pd.DataFrame(raw_trades)
            
        # Optimize tick access
        timestamps_ns = trades_df['ts_event'].values
        prices = trades_df['price'].values
        
        for i, trade in enumerate(day_trades_to_take):
            # Parse entry time to UTC nanoseconds to find the starting index
            # Trade time is NY time "HH:MM"
            dt_ny = datetime.strptime(f"{date_str} {trade['time']}", "%Y%m%d %H:%M")
            dt_ny = NY_TZ.localize(dt_ny)
            
            # EOD time is 16:00 NY
            dt_eod_ny = dt_ny.replace(hour=16, minute=0, second=0, microsecond=0)
            eod_ns = np.datetime64(int(dt_eod_ny.astimezone(pytz.utc).timestamp() * 1e9), 'ns')
            
            # We want to find the first tick >= the entry time
            # Since the entry triggered at the close of the 40-range bar, we approximate
            # by starting exactly at the HH:MM minute boundary.
            start_ns = np.datetime64(int(dt_ny.astimezone(pytz.utc).timestamp() * 1e9), 'ns')
            
            # Find start index
            idx = np.searchsorted(timestamps_ns, start_ns)
            
            if idx >= len(prices):
                continue
                
            entry_p = trade['entry']
            sl_p = trade['stop']
            risk = trade['risk_pts']
            direction = trade['direction']
            
            mfe_pts = 0.0
            mae_pts = 0.0
            outcome = "eod"
            
            # Tick loop
            for j in range(idx, len(prices)):
                ts = timestamps_ns[j]
                p = prices[j]
                
                if ts >= eod_ns:
                    outcome = "eod"
                    break
                    
                if direction == "LONG":
                    prof = p - entry_p
                    loss = entry_p - p
                    
                    if prof > mfe_pts: mfe_pts = prof
                    if loss > mae_pts: mae_pts = loss
                        
                    if p <= sl_p:
                        outcome = "loss"
                        break
                        
                else: # SHORT
                    prof = entry_p - p
                    loss = p - entry_p
                    
                    if prof > mfe_pts: mfe_pts = prof
                    if loss > mae_pts: mae_pts = loss
                        
                    if p >= sl_p:
                        outcome = "loss"
                        break
            
            trade_record = trade.copy()
            trade_record['half_size'] = (i == 1)
            trade_record['mfe_pts'] = round(mfe_pts, 2)
            trade_record['mfe_r'] = round(mfe_pts / risk, 2) if risk > 0 else 0
            trade_record['mae_pts'] = round(mae_pts, 2)
            trade_record['mae_r'] = round(mae_pts / risk, 2) if risk > 0 else 0
            trade_record['outcome'] = outcome
            
            processed_trades.append(trade_record)

    df = pd.DataFrame(processed_trades)
    if len(df) == 0:
        print("No trades processed.")
        return
        
    print(f"\nCompleted fast simulation in {time.time() - start_time:.2f}s")
    
    n_total = len(df)
    n_loss = (df['outcome'] == 'loss').sum()
    n_eod = (df['outcome'] == 'eod').sum()
    
    print(f"\n{'='*60}")
    print(f"MFE ANALYSIS RESULTS — Max 2 trades/day")
    print(f"{'='*60}")
    print(f"  Trade Totali:        {n_total}")
    print(f"  Loss (stop pieno):   {n_loss} ({(n_loss/n_total)*100:.1f}%)")
    print(f"  Chiusi EOD:          {n_eod}")
    
    print("\n  MFE Distribution:")
    for r in [2, 3, 4, 5, 6, 7, 8, 10]:
        n_above = (df['mfe_r'] >= r).sum()
        pct = n_above / n_total * 100
        bar = '#' * int(pct / 2)
        print(f"    >= {r}R: {n_above:>5} ({pct:>5.1f}%)  {bar}")
        
    print("\n  Dettaglio Trade:")
    for row in df.itertuples():
        size_tag = "HALF" if row.half_size else "FULL"
        icon = "[WIN]" if "win" in row.outcome else "[LOSS]"
        print(f"    {row.date} {row.time} | {row.direction:<5} | {size_tag} | Entry:{row.entry:>9.2f} Risk:{row.risk_pts:>5.1f} | MFE:{row.mfe_r:>4.1f}R  MAE:{row.mae_r:>4.1f}R | {icon} {row.outcome}")

    # Save output
    out_path = Path("C:/Users/Mauro/Documents/nq-backtest-clean/output/mfe_analysis_results_2025.csv")
    df.to_csv(out_path, index=False)
    print(f"\n  Saved detailed results to {out_path}")

if __name__ == "__main__":
    catalog_path = r"C:\Users\Mauro\Documents\nq-backtest-clean\output\zone_catalog_2025.json"
    simulate_trades_from_catalog(catalog_path)

