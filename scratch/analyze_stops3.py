import json

trades_file = "c:/Users/Mauro/Documents/nq-backtest/agent_memory/trades_log.jsonl"

trades = []
with open(trades_file, "r") as f:
    for line in f:
        if not line.strip(): continue
        t = json.loads(line)
        trades.append(t)

stops = [t for t in trades if t.get('pnl_usd', 0) < 0 or t.get('exit_reason') in ['stop_hit', 'stop_loss']]

print(f"Total stopped trades: {len(stops)}")

print("\nLast 5 Stopped Trades Analysis:")
for t in stops[-5:]:
    print(f"Date: {t.get('entry_time')}, PnL: {t.get('pnl_usd')}")
    print(f"Setup: {t.get('setup_type')}, Direction: {t.get('direction')}")
    print(f"Entry: {t.get('entry')}, Stop: {t.get('stop')}, Exit: {t.get('exit_price')}")
    print(f"Reasoning: {t.get('fabio_reasoning')}")
    print("-" * 50)
