import json
import glob
from collections import defaultdict

trades_raw = []
files = glob.glob('agent_memory/week*/trades_log.jsonl')
for fpath in files:
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    trades_raw.append(json.loads(line))
                except: pass

if not trades_raw:
    print('Nessun trade aperto ancora in nessuno dei 4 processi paralleli.')
else:
    by_entry = {}
    for t in trades_raw:
        etime = t.get('entry_time')
        if etime not in by_entry: by_entry[etime] = []
        by_entry[etime].append(t)
    
    merged = []
    for etime, parts in by_entry.items():
        m = parts[0].copy()
        m['pnl_usd'] = sum(p.get('pnl_usd', p.get('pnl', 0)) for p in parts)
        reasons = [p.get('exit_reason', '') for p in parts]
        if 'target' in reasons: m['exit_reason'] = 'target'
        elif 'trailing_stop' in reasons: m['exit_reason'] = 'partial+trail'
        merged.append(m)
        
    wins = [t for t in merged if t.get('pnl_usd',0) > 0]
    losses = [t for t in merged if t.get('pnl_usd',0) <= 0]
    pnl = sum(t.get('pnl_usd',0) for t in merged)
    print(f'Trade Raggruppati: {len(merged)}')
    print(f'Vinte: {len(wins)} | Perse: {len(losses)} | PnL: ${pnl:.2f}')
    print('\nDettaglio Trade:')
    for t in sorted(merged, key=lambda x: x.get('entry_time', '')):
        print(f"{t.get('entry_time')} | {t.get('direction').upper()} @ {t.get('entry')} | Esito: {t.get('exit_reason')} | PnL: ${t.get('pnl_usd',0):.2f}")
