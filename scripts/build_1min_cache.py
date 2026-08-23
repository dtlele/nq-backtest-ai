"""
Build 1-minute OHLC bar cache from Databento tick/trade CSV files.
"""

import os
import glob
import time
import pandas as pd
import numpy as np
from datetime import time as dtime
from concurrent.futures import ProcessPoolExecutor, as_completed

def process_single_databento_file(f):
    try:
        df = pd.read_csv(f, usecols=['ts_event', 'price', 'size', 'side'])
        if df.empty:
            return None
            
        df['ts_event'] = pd.to_datetime(df['ts_event'])
        if df['ts_event'].dt.tz is None:
            df['ts_event'] = df['ts_event'].dt.tz_localize('UTC')
        df['ts_eastern'] = df['ts_event'].dt.tz_convert('US/Eastern')
        
        # Filter RTH (09:30 to 16:00 EST)
        df_rth = df[(df['ts_eastern'].dt.time >= dtime(9, 30)) & (df['ts_eastern'].dt.time < dtime(16, 0))].copy()
        if df_rth.empty:
            return None
            
        df_rth['minute'] = df_rth['ts_eastern'].dt.floor('1min')
        
        bars = df_rth.groupby('minute').agg(
            open=('price', 'first'),
            high=('price', 'max'),
            low=('price', 'min'),
            close=('price', 'last'),
            volume=('size', 'sum')
        )
        
        idx_max = df_rth.groupby('minute')['size'].idxmax()
        mp = df_rth.loc[idx_max, ['minute', 'price', 'size', 'side']].set_index('minute')
        mp.columns = ['max_print_price', 'max_print_size', 'max_print_side']
        
        combined = bars.join(mp)
        return combined
    except Exception as e:
        print(f"Error processing {f}: {e}")
        return None

def main():
    t0 = time.time()
    data_dir = r"C:\Users\Mauro\Documents\databento-data"
    output_dir = r"C:\Users\Mauro\Documents\nq-backtest\output"
    os.makedirs(output_dir, exist_ok=True)
    out_parquet = os.path.join(output_dir, "whale_1min_bars.parquet")

    files = sorted(glob.glob(os.path.join(data_dir, "glbx-mdp3-*.trades.csv")))
    print(f"Found {len(files)} Databento trade files.")

    all_dfs = []
    # Multiprocessing with 8 workers
    with ProcessPoolExecutor(max_workers=8) as executor:
        future_to_file = {executor.submit(process_single_databento_file, f): f for f in files}
        count = 0
        for future in as_completed(future_to_file):
            count += 1
            if count % 50 == 0 or count == len(files):
                print(f"Processed {count}/{len(files)} files...")
            res = future.result()
            if res is not None and not res.empty:
                all_dfs.append(res)

    if not all_dfs:
        print("No bar data processed.")
        return

    full_df = pd.concat(all_dfs)
    full_df.sort_index(inplace=True)
    
    # Calculate ATR 14 (1-minute ATR)
    tr1 = full_df['high'] - full_df['low']
    tr2 = (full_df['high'] - full_df['close'].shift(1)).abs()
    tr3 = (full_df['low'] - full_df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    full_df['atr_14'] = tr.rolling(window=14, min_periods=1).mean()

    # Save to parquet
    full_df.to_parquet(out_parquet)
    t1 = time.time()
    print(f"\nSuccessfully built 1-min bar cache with {len(full_df)} rows in {t1-t0:.2f} seconds!")
    print(f"Saved to: {out_parquet}")

if __name__ == "__main__":
    main()
