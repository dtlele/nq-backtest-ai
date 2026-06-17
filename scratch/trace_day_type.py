import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.data_loader import load_day
from src.session_context import filter_ny_window, build_session_context, update_day_type, classify_day_type
from src.bar_aggregator import aggregate_to_bars
import datetime
import pytz

csv_path = "C:/Users/Mauro/Documents/databento-data/glbx-mdp3-20250430.trades.csv"
trades_raw = load_day(csv_path)
bars_1min_ny = filter_ny_window(aggregate_to_bars(trades_raw, freq='1min'))
bars_ny = filter_ny_window(aggregate_to_bars(trades_raw, freq='5min'))

print(f"Total 1min bars: {len(bars_1min_ny)}")
print(f"Total 5min bars: {len(bars_ny)}")

ctx = build_session_context("20250430", bars_1min_ny, None)
print(f"Initial day type: {ctx.day_type}")

ET = pytz.timezone('America/New_York')

for idx, m1_bar in enumerate(bars_1min_ny):
    # Fabio active window
    t = m1_bar.timestamp.astimezone(ET)
    start_time = t.replace(hour=9, minute=31, second=0, microsecond=0)
    end_time   = t.replace(hour=11, minute=0, second=0, microsecond=0)
    if not (start_time <= t < end_time):
        continue
        
    last_m5_idx = None
    for i, b in enumerate(bars_ny):
        if b.timestamp <= m1_bar.timestamp:
            last_m5_idx = i
        else:
            break
            
    if last_m5_idx is None:
        continue
        
    bar_idx = last_m5_idx
    sub_bars = bars_ny[:bar_idx+1]
    day_type_before = ctx.day_type
    
    # We call update_day_type like in backtest_runner
    new_type = update_day_type(ctx, sub_bars)
    
    print(f"Time {t.strftime('%H:%M')} | last_m5_idx: {bar_idx} | len(sub_bars): {len(sub_bars)} | Before: {day_type_before} | After: {new_type}")
