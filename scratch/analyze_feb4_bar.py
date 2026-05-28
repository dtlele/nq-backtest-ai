import csv
from datetime import datetime, timezone

with open(r'C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250204.trades.csv', 'r') as f:
    reader = csv.DictReader(f)
    trades_1600 = []
    for row in reader:
        ts_str = row.get('ts_event', '')
        try:
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except Exception:
            continue
        if ts.hour == 16 and ts.minute == 0:
            price = float(row.get('price', 0))
            trades_1600.append((ts, price))

if trades_1600:
    prices = [p for _, p in trades_1600]
    print(f'M5 16:00 UTC: {len(trades_1600)} trades')
    print(f'First: {trades_1600[0][0].strftime("%H:%M:%S.%f")} @ {trades_1600[0][1]:.2f}')
    print(f'Last:  {trades_1600[-1][0].strftime("%H:%M:%S.%f")} @ {trades_1600[-1][1]:.2f}')
    print(f'High={max(prices):.2f}  Low={min(prices):.2f}')
    print()
    print('First 10 trades:')
    for ts, p in trades_1600[:10]:
        print(f'  {ts.strftime("%H:%M:%S.%f")} @ {p:.2f}')
    print()
    low_idx = prices.index(min(prices))
    ts_low = trades_1600[low_idx][0]
    print(f'Low {min(prices):.2f} avvenuto a: {ts_low.strftime("%H:%M:%S.%f")}')
else:
    print('Nessun trade alle 16:00 UTC')

# Mostra le prime righe per capire il formato
print()
print('Sample rows (prime 3):')
with open(r'C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250204.trades.csv', 'r') as f:
    for i, line in enumerate(f):
        print(line.strip())
        if i >= 3:
            break
