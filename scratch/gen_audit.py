import json
import glob
from pathlib import Path
from collections import defaultdict
import pandas as pd

# Load reasonings to count days analyzed
reasonings = []
for fpath in glob.glob('agent_memory/week*/reasoning_log.jsonl'):
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    reasonings.append(json.loads(line))
                except: pass

days_analyzed = set()
for r in reasonings:
    d = r.get('date')
    if d: days_analyzed.add(d)

# Load trades
trades_raw = []
for fpath in glob.glob('agent_memory/week*/trades_log.jsonl'):
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    trades_raw.append(json.loads(line))
                except: pass

by_entry = {}
for t in trades_raw:
    etime = t['entry_time']
    if etime not in by_entry: by_entry[etime] = []
    by_entry[etime].append(t)

merged_trades = []
for etime, parts in by_entry.items():
    t = parts[0].copy()
    
    t['pnl_usd'] = sum(p.get('pnl_usd', p.get('pnl', 0)) for p in parts)
    reasons = [p.get('exit_reason', '') for p in parts]
    
    if 'target' in reasons:
        t['final_esito'] = 'Target'
    elif 'trailing_stop' in reasons:
        t['final_esito'] = 'Partial+Trail'
    else:
        t['final_esito'] = 'Stop Loss'
        
    merged_trades.append(t)

# Sort trades
merged_trades.sort(key=lambda x: x['entry_time'])

out = []
out.append(f"# Audit Run Sospesa (Parallela)")
out.append(f"**Giorni Analizzati:** {len(days_analyzed)} ({', '.join(sorted(list(days_analyzed)))})")
out.append(f"**Trade Totali:** {len(merged_trades)}")

wins = [t for t in merged_trades if t.get('pnl_usd',0) > 0]
losses = [t for t in merged_trades if t.get('pnl_usd',0) <= 0]
pnl = sum(t.get('pnl_usd',0) for t in merged_trades)

out.append(f"**Win Rate:** {len(wins)} Vinte | {len(losses)} Perse")
out.append(f"**P&L Netto:** ${pnl:.2f}\n")

out.append("## Dettaglio Trade")

for t in merged_trades:
    date_str = t.get('date', 'N/A')
    time_str = t.get('entry_time', 'N/A')
    direc = t.get('direction', 'N/A').upper()
    esito = t.get('final_esito', 'N/A')
    pnl_usd = t.get('pnl_usd', 0)
    
    # Try to find strategy/reasoning from the trade's consensus object
    consensus = t.get('consensus', {})
    strat = consensus.get('logic_flow', 'Sconosciuta')
    
    # Extract audit reasoning from the reasonings log corresponding to this trade's entry_time
    trade_reasoning = "N/A"
    for r in reasonings:
        if r.get('bar_time_utc') == time_str or r.get('bar_time_et') == time_str:
            trade_reasoning = r.get('deep_audit', r.get('logic_flow', 'N/A'))
            strat = r.get('logic_flow', strat)
            break
            
    out.append(f"### {time_str} | {direc} @ {t.get('entry')}")
    out.append(f"- **Esito:** {esito}")
    out.append(f"- **Profitto (PNL):** ${pnl_usd:.2f}")
    out.append(f"- **Strategia / Logica:** {strat}")
    out.append(f"- **Ragionamento Agente:**\n> {trade_reasoning}\n")

with open('audit_suspended.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
    
print("Audit generato in audit_suspended.md")
