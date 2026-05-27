import json

total_pnl = 0
sept_pnl = 0
oct_pnl = 0
trades_count = 0

with open('agent_memory/trades_log.jsonl', 'r') as f:
    for line in f:
        if not line.strip(): continue
        trade = json.loads(line)
        pnl = trade.get('pnl_usd', 0)
        date = trade.get('date', '')
        total_pnl += pnl
        trades_count += 1
        if '-09-' in date:
            sept_pnl += pnl
        if '-10-' in date:
            oct_pnl += pnl

print(f"Total Trades: {trades_count}")
print(f"Total Cumulative PnL: ${total_pnl:.2f}")
print(f"September 2025 PnL: ${sept_pnl:.2f}")
print(f"October 2025 PnL: ${oct_pnl:.2f}")
