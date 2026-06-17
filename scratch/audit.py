import json
from collections import defaultdict

try:
    with open('C:/Users/Mauro/Documents/nq-backtest/agent_memory/trades_log.jsonl', encoding='utf-8') as f:
        trades = [json.loads(line) for line in f if line.strip()]
except FileNotFoundError:
    print("No trades logged yet.")
    exit()

if not trades:
    print("No trades logged yet.")
    exit()

print(f"Total trades: {len(trades)}")
wins = sum(1 for t in trades if t['pnl_usd'] > 0)
losses = sum(1 for t in trades if t['pnl_usd'] <= 0)
total_pnl = sum(t['pnl_usd'] for t in trades)

print(f"Wins: {wins}")
print(f"Losses: {losses}")
print(f"Total PnL: ${total_pnl:.2f}\n")

by_day = defaultdict(list)
for t in trades:
    by_day[t['date']].append(t)

for date, day_trades in by_day.items():
    day_pnl = sum(t['pnl_usd'] for t in day_trades)
    print(f"--- {date} ---")
    print(f"Trades: {len(day_trades)}, PnL: ${day_pnl:.2f}")
    for t in day_trades:
        time_str = t['entry_time'].split('T')[1][:5]
        reason = t.get('exit_reason', 'unknown')[:15]
        print(f"  {time_str} {t['direction'].upper():5} @ {t['entry']:<8} -> PnL: ${t['pnl_usd']:>6.2f}  [{reason}]")
    print()
