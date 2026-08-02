import glob
import os
import re
import time
from pathlib import Path
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
CACHE_DIR = Path(r"C:\Users\Mauro\Documents\nq-backtest-clean\cache_ohlc")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def process_file(fpath):
    fname = Path(fpath).name
    m = re.search(r'(\d{8})', fname)
    if not m:
        return None
    date_str = m.group(1)
    cache_file = CACHE_DIR / f"{date_str}.csv"
    if cache_file.exists():
        return date_str, True
    try:
        df = pd.read_csv(fpath, usecols=['ts_event', 'action', 'price', 'size', 'symbol'])
        df = df[df['action'] == 'T'].copy()
        if 'symbol' in df.columns:
            outright = df[~df['symbol'].str.contains('-', na=False)]
            if not outright.empty:
                front_month = outright['symbol'].value_counts().idxmax()
                df = outright[outright['symbol'] == front_month].copy()
        df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
        df = df.set_index('ts_event')
        bars_df = df['price'].resample('1Min').ohlc()
        bars_df = bars_df.dropna().reset_index()
        bars_df.columns = ['timestamp', 'open', 'high', 'low', 'close']
        bars_df.to_csv(cache_file, index=False)
        return date_str, True
    except Exception as e:
        print(f"Error on {date_str}: {e}")
        return date_str, False

def main():
    files = sorted(glob.glob(f"{DATA_DIR}/*.trades.csv"))
    print(f"Processing {len(files)} Databento files into 1-minute OHLC cache...")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(process_file, files))
    t1 = time.time()
    successes = sum(1 for r in results if r and r[1])
    print(f"Completed in {t1-t0:.2f}s. Total cached OHLC days: {successes}/{len(files)}")

if __name__ == '__main__':
    main()
