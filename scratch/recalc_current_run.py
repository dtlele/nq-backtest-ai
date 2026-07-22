import json
import pandas as pd
import glob
from pathlib import Path

trades_raw = []
for fpath in glob.glob('agent_memory/week*/trades_log.jsonl'):
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip(): trades_raw.append(json.loads(line))

by_entry = {}
for t in trades_raw:
    etime = t['entry_time']
    if etime not in by_entry: by_entry[etime] = []
    by_entry[etime].append(t)

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

print(f'Riadattando i {len(morning_trades)} trade della run attuale (eseguito in background)...')
DATA_DIR = Path('C:/Users/Mauro/Documents/databento-data')
pnl_totale_r = 0

for t in sorted(morning_trades, key=lambda x: x['entry_time']):
    date_str = t['date'].replace('-', '')
    csv_file = DATA_DIR / f'glbx-mdp3-{date_str}.trades.csv'
    if not csv_file.exists(): continue
    
    df = pd.read_csv(csv_file, usecols=['ts_event', 'price', 'action'])
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    df = df[df['ts_event'] >= pd.to_datetime(t['entry_time'])]
    
    entry = t['entry']
    stop = t['stop']
    direction = t['direction']
    risk = abs(entry - stop)
    if risk == 0: continue
    
    max_favorable = entry
    hit_stop = False
    
    for price in df['price']:
        if direction == 'long':
            if price > max_favorable: max_favorable = price
            if price <= stop:
                hit_stop = True
                break
        else:
            if price < max_favorable or max_favorable == entry: max_favorable = price
            if price >= stop:
                hit_stop = True
                break
                
    mfe_pts = abs(max_favorable - entry)
    mfe_r = mfe_pts / risk
    
    # Simulate All-In 3.5R
    if mfe_r >= 3.5:
        pnl_r = 3.5
        esito = 'Target Pieno (+3.5R)'
    else:
        pnl_r = -1.0
        esito = 'Stop Loss (-1.0R)'
    
    pnl_totale_r += pnl_r
    print(f"{t['entry_time']} | {t['direction'].upper()} @ {t['entry']} | MFE Raggiunto: {mfe_r:.2f}R | Nuovo Esito: {esito}")

print(f'\nPnL TOTALE Ricalcolato (Run Attuale): {pnl_totale_r:.2f}R (circa ${pnl_totale_r*50:.2f})')
