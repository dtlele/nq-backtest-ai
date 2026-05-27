import json
from pathlib import Path

log_file = Path(r'c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl')
september_trades = []

if log_file.exists():
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if '2025-09' in line:
                try:
                    september_trades.append(json.loads(line))
                except:
                    pass

print(f"Found {len(september_trades)} trades in September.")
for t in september_trades:
    print(f"{t['date']} | {t['direction']} | {t['entry']} -> {t['exit_price']} ({t['exit_reason']}) | PnL: {t['pnl_usd']} | Contracts: {t.get('contracts', 'N/A')}")
