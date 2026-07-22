import json
import pandas as pd
import glob
from pathlib import Path

# Load morning trades
trades_raw = []
with open('agent_memory_backup/trades_log.jsonl', 'r') as f:
    for line in f:
        if line.strip(): trades_raw.append(json.loads(line))

# Group by entry
by_entry = {}
for t in trades_raw:
    et = pd.to_datetime(t['entry_time']).tz_convert('America/New_York')
    if et.hour == 10:
        etime = t['entry_time']
        if etime not in by_entry: by_entry[etime] = []
        by_entry[etime].append(t)

# Extract 1 representative per entry
morning_trades = []
for etime, parts in by_entry.items():
    t = parts[0]
    morning_trades.append({
        'date': t['date'],
        'entry_time': t['entry_time'],
        'direction': t['direction'],
        'entry': t['entry'],
        'stop': t['stop']
    })

print(f"Analizing {len(morning_trades)} morning trades...")

DATA_DIR = Path('C:/Users/Mauro/Documents/databento-data')
results = []

for t in morning_trades:
    date_str = t['date'].replace('-', '')
    csv_file = DATA_DIR / f"glbx-mdp3-{date_str}.trades.csv"
    if not csv_file.exists(): continue
    
    df = pd.read_csv(csv_file, usecols=['ts_event', 'price', 'action'])
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    
    entry_ts = pd.to_datetime(t['entry_time'])
    # Filter after entry
    df = df[df['ts_event'] >= entry_ts]
    
    entry = t['entry']
    stop = t['stop']
    direction = t['direction']
    risk = abs(entry - stop)
    if risk == 0: continue
    
    max_favorable = entry
    hit_stop = False
    
    for price in df['price']:
        if direction == 'long':
            if price > max_favorable:
                max_favorable = price
            if price <= stop:
                hit_stop = True
                break
        else:
            if price < max_favorable or max_favorable == entry:
                max_favorable = price
            if price >= stop:
                hit_stop = True
                break
                
    mfe_pts = abs(max_favorable - entry)
    mfe_r = mfe_pts / risk
    
    results.append({
        'date': t['date'],
        'direction': direction,
        'mfe_r': mfe_r,
        'hit_stop': hit_stop
    })

if not results:
    print("Nessun risultato")
    exit()

# Analyze MFE Distribution
mfe_rs = [r['mfe_r'] for r in results]
print(f"MFE R Medio: {sum(mfe_rs)/len(mfe_rs):.2f}")
print(f"Quanti arrivano a 1.0R: {len([r for r in results if r['mfe_r'] >= 1.0])} / {len(results)}")
print(f"Quanti arrivano a 2.0R: {len([r for r in results if r['mfe_r'] >= 2.0])} / {len(results)}")
print(f"Quanti arrivano a 3.0R: {len([r for r in results if r['mfe_r'] >= 3.0])} / {len(results)}")

# Simulation: Fixed TP vs Trailing
# Let's say risk is $50.
# If Fixed TP 2.0R -> +2.0R if mfe >= 2.0 else -1R
# If Trailing at 1R -> if mfe >= 1.0, wait till MFE reverses. In reality, trailing trails by 0.5R or hits BE.
def sim_fixed_tp(tp_r):
    pnl = 0
    for r in results:
        if r['mfe_r'] >= tp_r:
            pnl += tp_r
        else:
            pnl -= 1.0
    return pnl

print("\n--- SIMULAZIONE TARGET FISSO SENZA TRAILING ---")
for tp in [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]:
    pnl = sim_fixed_tp(tp)
    print(f"Target a {tp}R: {pnl:.2f} R Totali")

print("\n--- CONCLUSIONI ---")
print("I dati mostrano chiaramente l'MFE (escursione massima) prima di prendere lo stop originale.")

