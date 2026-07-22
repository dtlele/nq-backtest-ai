import pandas as pd
from src.data_loader import load_day
from src.bar_aggregator import aggregate_to_bars

def check(date, entry_time_str, direction, entry, target, orig_stop):
    file_path = f'C:/Users/Mauro/Documents/databento-data/glbx-mdp3-{date.replace("-", "")}.trades.csv'
    print(f"Loading {file_path}...")
    try:
        df = load_day(file_path, as_df=True)
    except Exception as e:
        print(f"File not found or error: {e}")
        return
        
    bars = aggregate_to_bars(df, freq='1min')
    
    entry_time = pd.to_datetime(entry_time_str)
    future_bars = [b for b in bars if b.timestamp >= entry_time]
    
    print(f'\nChecking {direction} trade on {date} at {entry}')
    for bar in future_bars:
        h, l = bar.high, bar.low
        if direction == 'short':
            if h >= orig_stop:
                print('Hit original stop first!')
                return
            if l <= target:
                print('Would have hit FULL TARGET!')
                return
        else:
            if l <= orig_stop:
                print('Hit original stop first!')
                return
            if h >= target:
                print('Would have hit FULL TARGET!')
                return
    print('Did not hit target or stop by end of day')

check('2025-02-03', '2025-02-03T15:13:00+00:00', 'short', 21148.0, 21098.5, 21148.0+33)
check('2025-02-04', '2025-02-04T15:31:00+00:00', 'long', 21627.25, 21700.25, 21627.25-48.6)
