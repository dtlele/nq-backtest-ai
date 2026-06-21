import sys
sys.path.append('.')

from src.data_loader import load_day
from src.bar_aggregator import aggregate_to_bars
from pathlib import Path
import pytz

ET = pytz.timezone('America/New_York')

file_path = Path(r"C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250128.trades.csv")
if not file_path.exists():
    print("File not found:", file_path)
    exit()

print("Loading file...")
trades = load_day(str(file_path))
print(f"Loaded {len(trades)} trades")

print("Aggregating to M5 bars...")
bars_m5 = aggregate_to_bars(trades, freq='5min')
print(f"Aggregated to {len(bars_m5)} M5 bars")

print("Aggregating to M1 bars...")
bars_m1 = aggregate_to_bars(trades, freq='1min')
print(f"Aggregated to {len(bars_m1)} M1 bars")

# Filter NY session (9:30 to 16:00 ET)
m1_ny = []
for b in bars_m1:
    t_et = b.timestamp.astimezone(ET)
    if t_et.hour == 10 and 0 <= t_et.minute <= 45:
        m1_ny.append((t_et, b))

print("\n--- M1 Bars between 10:00 and 10:45 ET ---")
for t_et, b in m1_ny:
    print(f"Time: {t_et.strftime('%H:%M:%S')} | O:{b.open:.2f} H:{b.high:.2f} L:{b.low:.2f} C:{b.close:.2f} | Vol:{b.volume} | Delta:{b.delta} | Big Trades count: {len(b.big_trades)}")
    for bt in b.big_trades:
        print(f"   Big Trade: {bt.side} at {bt.price:.2f} size {bt.size}")
