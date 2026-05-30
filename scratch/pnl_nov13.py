import json

pnl_usd = 0
ticks = 0
trades = 0

with open('agent_memory/trades_log.jsonl', 'r') as f:
    for line in f:
        try:
            t = json.loads(line)
            if t.get('date') == '2025-11-17':
                pnl_usd += t.get('pnl_usd', 0)
                ticks += t.get('pnl_ticks', 0)
                trades += 1
                time_str = t.get('entry_time', '')
                if len(time_str) >= 16: time_str = time_str[11:16]
                print(f"{time_str} | {t.get('direction').upper()} | Entry: {t.get('entry')} | Exit: {t.get('exit_reason')} | PnL Ticks: {t.get('pnl_ticks')} | PnL USD: ${t.get('pnl_usd'):.2f}")
        except: pass

print(f"\nTOTAL PNL USD per 17 Nov: ${pnl_usd:.2f}")
print(f"TOTAL TICKS per 17 Nov: {ticks}")
