import json

trades = []
with open('agent_memory/trades_log.jsonl', 'r') as f:
    for line in f:
        if line.strip():
            trades.append(json.loads(line))

valid_pnls = [t.get('pnl_usd') for t in trades if t.get('pnl_usd') is not None]
total_pnl = sum(valid_pnls)

print(f'Total PNL USD: ')
