import sys
from pathlib import Path

# Add src to path
sys.path.append("c:\\Users\\Mauro\\Documents\\nq-backtest")

from src.data_loader import load_day
from src.bar_aggregator import aggregate_to_bars

data_path = Path("c:/Users/Mauro/Documents/nq-backtest/data/20250407_ticks.csv")
if not data_path.exists():
    print(f"Data file not found: {data_path}")
    sys.exit(1)

ticks = load_day(str(data_path))
m1_bars = aggregate_to_bars(ticks, freq='1min')

import pytz
ET = pytz.timezone('America/New_York')

for b in m1_bars:
    t_et = b.timestamp.astimezone(ET)
    if t_et.hour == 10 and 5 <= t_et.minute <= 10:
        print(f"--- {t_et.strftime('%H:%M ET')} ---")
        print(f"O={b.open} H={b.high} L={b.low} C={b.close} Vol={b.volume} Delta={b.delta}")
        if b.big_trades:
            for bt in b.big_trades:
                print(f"  Big Trade: {bt.size} contracts at {bt.price} ({'Buy/Ask' if bt.side == 'A' else 'Sell/Bid'})")
        else:
            print("  No big trades")
