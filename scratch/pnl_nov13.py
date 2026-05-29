import json

trades = []
with open('agent_memory/trades_log.jsonl', 'r') as f:
    for line in f:
        try:
            t = json.loads(line)
            if t.get('date') == '2025-11-14':
                trades.append(t)
        except: pass

pnl_usd = 0
for t in trades:
    pnl_usd += t.get('pnl_usd', 0)
    time_str = t.get('entry_time', '')
    if len(time_str) >= 16: time_str = time_str[11:16]
    print(f"{time_str} | {t.get('direction').upper()} | Entry: {t.get('entry')} | Exit: {t.get('exit_reason')} | PnL Ticks: {t.get('pnl_ticks')} | PnL USD: ${t.get('pnl_usd'):.2f}")

print(f"\nTOTAL PNL USD per 14 Nov: ${pnl_usd:.2f}")
