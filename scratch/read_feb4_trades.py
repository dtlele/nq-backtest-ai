import json
from pathlib import Path

trades_file = Path('agent_memory/trades_log.jsonl')
feb4_trades = []
with open(trades_file, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            t = json.loads(line)
            if t.get('date') == '2025-02-04':
                feb4_trades.append(t)

print(f'Trade del 4 Feb trovati: {len(feb4_trades)}')
for i, t in enumerate(feb4_trades, 1):
    print()
    print(f'--- Trade {i} ---')
    print(f'  Direzione : {t["direction"].upper()}')
    print(f'  Entry     : {t["entry"]} @ {t["entry_time"]}')
    print(f'  Stop      : {t["stop"]}')
    print(f'  Target    : {t["target"]}')
    print(f'  Exit      : {t["exit_price"]} @ {t["exit_time"]}')
    print(f'  Motivo    : {t["exit_reason"]}')
    print(f'  PnL       : ${t["pnl_usd"]:.2f}  ({t["pnl_ticks"]:.1f} ticks)')
    print(f'  Contracts : {t.get("contracts", "n/a")}')
