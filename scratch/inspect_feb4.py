import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.data_loader import load_day
from src.bar_aggregator import aggregate_to_bars

def main():
    csv_path = r"C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250204.trades.csv"
    print("Loading data for Feb 4th...")
    trades = load_day(csv_path)
    print(f"Loaded {len(trades)} raw trades. Aggregating to 1-min bars...")
    bars_1min = aggregate_to_bars(trades, freq='1min')
    
    print("\n--- 1-MIN BARS FOR FEB 4th FROM 15:50 to 16:40 UTC ---")
    import pytz
    for b in bars_1min:
        ts_utc = b.timestamp.strftime('%H:%M')
        # Check if between 15:50 and 16:40 UTC
        if '15:50' <= ts_utc <= '16:40':
            big_trades_str = ""
            if b.big_trades:
                big_trades_str = f" | BIG: {[{'side': t.side, 'price': t.price, 'size': t.size} for t in b.big_trades]}"
            print(f"[{ts_utc} UTC] O={b.open:.2f} H={b.high:.2f} L={b.low:.2f} C={b.close:.2f} V={b.volume} delta={b.delta:+d}{big_trades_str}")

if __name__ == "__main__":
    main()
