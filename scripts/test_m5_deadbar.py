"""Test offline: quante candele M5 del 04/02 sono 'morte'?
Risponde alla domanda: se applicassi dead-bar filter PRIMA di detect_candidates,
quante chiamate LLM risparmieresti?
"""
import sys
sys.path.insert(0, '.')
import csv
from datetime import datetime
from src.bar_aggregator import aggregate_to_bars
from src.session_context import build_session_context

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'

# Carica barre M1
csv_path = f'{DATA_DIR}\\glbx-mdp3-20250204.trades.csv'
trades_raw = []
from datetime import datetime
from src import Trade
with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ts_str = row['ts_event'].replace('Z', '+00:00')
        ts_dt = datetime.fromisoformat(ts_str)
        trades_raw.append(Trade(
            ts_event=ts_dt,
            price=float(row['price']),
            size=int(row['size']),
            side=row.get('side', 'A'),
        ))

# Aggrega a M5
bars_m5 = aggregate_to_bars(trades_raw, freq='5min')
print(f'Total M5 bars: {len(bars_m5)}')

# Calcola dead-bar per ogni M5
dead_count = 0
alive_count = 0
for i, bar in enumerate(bars_m5):
    # Media volume ultimi 12
    recent = bars_m5[max(0, i-12):i]
    if recent:
        avg_vol = sum(b.volume for b in recent) / len(recent)
    else:
        avg_vol = bar.volume
    rng = bar.high - bar.low
    # Regole dead-bar
    is_dead = False
    reason = None
    if bar.volume < avg_vol * 0.5:
        is_dead = True
        reason = 'low_vol'
    elif rng < 5.0:
        is_dead = True
        reason = 'low_range'
    if is_dead:
        dead_count += 1
    else:
        alive_count += 1
        if i < 5 or i > len(bars_m5) - 5:
            print(f'  Alive bar #{i}: vol={bar.volume:.0f} (avg={avg_vol:.0f}) range={rng:.1f}pt')

print(f'\n=== RISULTATO ===')
print(f'Total M5: {len(bars_m5)}')
print(f'Dead (skip LLM): {dead_count} ({100*dead_count/len(bars_m5):.0f}%)')
print(f'Alive (LLM call): {alive_count} ({100*alive_count/len(bars_m5):.0f}%)')
print(f'\nRisparmio atteso: {dead_count} chiamate LLM su {len(bars_m5)} totali')
