import os
import glob
import pandas as pd

def check_trade():
    print("Checking OHLC files for Jan 7, 15:40 UTC...")
    files = glob.glob(r"C:\Users\Mauro\Documents\nq-backtest-clean\cache_ohlc\*.csv")
    target_file = None
    for f in files:
        if "0107" in f:
            target_file = f
            break
            
    if not target_file:
        print("No CSV found for Jan 7")
        return
        
    print(f"Found file: {target_file}")
    df = pd.read_csv(target_file)
    
    # Check if 'timestamp' exists
    if 'timestamp' not in df.columns and 'ts_event' in df.columns:
        df['timestamp'] = df['ts_event']
        
    # Filter after 15:40 UTC
    try:
        # Some CSVs have string timestamps, some have unix
        if isinstance(df['timestamp'].iloc[0], str):
            df['datetime'] = pd.to_datetime(df['timestamp'])
            mask = df['datetime'] >= pd.to_datetime('2026-01-07 15:40:00+00:00', utc=True)
            if not mask.any():
                mask = df['datetime'] >= pd.to_datetime('2025-01-07 15:40:00+00:00', utc=True)
        else:
            print("Timestamp format unknown")
            return
            
        df_sub = df[mask]
        print(f"Rows after 15:40 UTC: {len(df_sub)}")
        
        entry = 25851.0
        sl = 25905.5
        tp = 25771.0
        
        for idx, row in df_sub.iterrows():
            high = row['high']
            low = row['low']
            
            if low <= tp:
                print(f"PROFIT HIT FIRST at {row['timestamp']}! Reached target {tp}")
                return
            if high >= sl:
                print(f"STOP LOSS HIT FIRST at {row['timestamp']}! Reached SL {sl}")
                return
                
        print("Neither hit by end of day.")
    except Exception as e:
        print(f"Error: {e}")

check_trade()
