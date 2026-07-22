import json
import glob
import pandas as pd
from pathlib import Path
from src.oos_exporter import export_trades_to_csv

DATA_DIR = Path('C:/Users/Mauro/Documents/databento-data')

# 1. Load trades
week_trades = []
for p in glob.glob('agent_memory/week*/trades_log.jsonl') + glob.glob('agent_memory_backup/trades_log.jsonl'):
    with open(p, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    week_trades.append(json.loads(line))
                except: pass

by_entry = {}
for t in week_trades:
    etime = t.get('entry_time')
    if not etime: continue
    et = pd.to_datetime(etime).tz_convert('America/New_York')
    if et.hour == 10:
        if etime not in by_entry:
            by_entry[etime] = t

trades = list(by_entry.values())
trades.sort(key=lambda x: x['entry_time'])

# 2. Enrich with MFE/MAE and 3.5R strategy outputs
oos_records = []
for t in trades:
    date_str = t['date'].replace('-', '')
    csv_file = DATA_DIR / f"glbx-mdp3-{date_str}.trades.csv"
    
    entry = t['entry']
    stop = t['stop']
    direction = t['direction']
    risk = abs(entry - stop)
    if risk == 0: continue
    
    mfe_r = 0.0
    mae_r = 0.0
    exit_reason = "stop"
    pnl_usd = -50.0
    
    if csv_file.exists():
        df = pd.read_csv(csv_file, usecols=['ts_event', 'price', 'symbol'])
        df = df[~df['symbol'].str.contains('-', na=False)]
        front = df['symbol'].value_counts().idxmax()
        df = df[df['symbol'] == front]
        df['ts_event'] = pd.to_datetime(df['ts_event'])
        df = df[df['ts_event'] >= pd.to_datetime(t['entry_time'])]
        
        max_fav = entry
        max_adv = entry
        target_35r = entry + (3.5 * risk) if direction == 'long' else entry - (3.5 * risk)
        
        for price in df['price']:
            if direction == 'long':
                if price > max_fav: max_fav = price
                if price < max_adv: max_adv = price
                if price <= stop:
                    exit_reason = "stop"
                    pnl_usd = -50.0
                    break
                if price >= target_35r:
                    exit_reason = "target"
                    pnl_usd = 175.0
                    break
            else:
                if price < max_fav or max_fav == entry: max_fav = price
                if price > max_adv: max_adv = price
                if price >= stop:
                    exit_reason = "stop"
                    pnl_usd = -50.0
                    break
                if price <= target_35r:
                    exit_reason = "target"
                    pnl_usd = 175.0
                    break
                    
        mfe_r = abs(max_fav - entry) / risk
        mae_r = abs(max_adv - entry) / risk
        
    oos_records.append({
        'entry_time': t['entry_time'],
        'exit_time': t.get('exit_time', t['entry_time']),
        'direction': direction,
        'entry': entry,
        'stop': stop,
        'target': entry + (3.5 * risk) if direction == 'long' else entry - (3.5 * risk),
        'exit_price': entry + (3.5 * risk) if exit_reason == 'target' and direction == 'long' else (entry - (3.5 * risk) if exit_reason == 'target' else stop),
        'exit_reason': exit_reason,
        'pnl_usd': pnl_usd,
        'mfe_r': mfe_r,
        'mae_r': mae_r,
        'veto_reason': 'none',
        'regime': 'RUNNER_3.5R'
    })

df_export = export_trades_to_csv(oos_records, 'output/trades_2025-02.csv')
print("\n--- OOS CSV PREVIEW ---")
print(df_export.head(10).to_string(index=False))
