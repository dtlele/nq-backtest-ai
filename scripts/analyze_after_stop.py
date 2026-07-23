"""Analisi tick-data: cosa e' successo DOPO lo stop del trade?
Trade entry 15:50 UTC @ 21873.75, stop 21833.25, target 21935.00
Stop hit quando il prezzo ha toccato 21833.25.
Vediamo: candele M5 successive, c'e' stata una 'last liquidation' che ha invalidato il setup?
"""
import csv
import datetime as dt
from collections import defaultdict

csv_path = r'C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250210.trades.csv'

# Aggrega in M1 bars
m1_bars = defaultdict(lambda: {'high': 0, 'low': 1e9, 'open': None, 'close': None, 'volume': 0, 'trades': 0})
trades = []
with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ts_str = row['ts_event'].replace('Z', '+00:00')
        ts = dt.datetime.fromisoformat(ts_str)
        # Filtra 15:50-17:00 UTC
        if dt.datetime(2025, 2, 10, 15, 50, tzinfo=dt.timezone.utc) <= ts <= dt.datetime(2025, 2, 10, 17, 0, tzinfo=dt.timezone.utc):
            price = float(row['price'])
            if 21000 < price < 22000:  # filtra outlier
                minute = ts.replace(second=0, microsecond=0)
                m1_bars[minute]['volume'] += int(row['size'])
                m1_bars[minute]['trades'] += 1
                m1_bars[minute]['high'] = max(m1_bars[minute]['high'], price)
                m1_bars[minute]['low'] = min(m1_bars[minute]['low'], price)
                if m1_bars[minute]['open'] is None:
                    m1_bars[minute]['open'] = price
                m1_bars[minute]['close'] = price
                trades.append({'ts': ts, 'price': price, 'size': int(row['size'])})

print(f'\nM1 BARS 15:50-17:00 UTC del 10/02 (rilevanti, prezzo 21-22k):')
print(f'{"Time":<10} {"O":<8} {"H":<8} {"L":<8} {"C":<8} {"Vol":<8} {"#":<6} {"Net":<6}')
for minute in sorted(m1_bars.keys()):
    b = m1_bars[minute]
    if b['volume'] > 0 and 21000 < b['close'] < 22000:
        net = b['close'] - b['open']
        print(f'{minute.strftime("%H:%M")} {b["open"]:.2f}   {b["high"]:.2f}  {b["low"]:.2f}  {b["close"]:.2f}  {b["volume"]:>5} {b["trades"]:>4} {net:+.1f}')

# Cerca il MIN esatto (touch dello stop 21833.25)
print(f'\nCerca tocco stop 21833.25:')
hits = [t for t in trades if 21830 <= t['price'] <= 21837]
for t in hits[:20]:
    print(f'  {t["ts"]} price={t["price"]:.2f} size={t["size"]}')

# Verifica se dopo lo stop, il prezzo e' risalito (take profit mancato) o sceso ancora
print(f'\n--- Andamento DOPO il tocco dello stop ---')
if hits:
    first_hit_ts = hits[0]['ts']
    print(f'Primo tocco stop 21833.25: {first_hit_ts} @ {hits[0]["price"]:.2f}')
    after = [t for t in trades if t['ts'] > first_hit_ts and t['ts'] < first_hit_ts + dt.timedelta(minutes=30)]
    if after:
        prices_after = [t['price'] for t in after]
        print(f'30 min dopo: range {min(prices_after):.2f} - {max(prices_after):.2f}')
        print(f'30 min dopo: net {after[-1]["price"] - hits[0]["price"]:+.1f} pts')
