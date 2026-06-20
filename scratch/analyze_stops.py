import json
import collections

trades_file = "c:/Users/Mauro/Documents/nq-backtest/agent_memory/trades_log.jsonl"
reasoning_file = "c:/Users/Mauro/Documents/nq-backtest/agent_memory/reasoning_log.jsonl"

trades = []
with open(trades_file, "r") as f:
    for line in f:
        if not line.strip(): continue
        t = json.loads(line)
        # focus on recent trades (assuming backtest output from yesterday)
        trades.append(t)

stops = [t for t in trades if t.get('pnl_usd', 0) < 0 or t.get('exit_reason') in ['stop_hit', 'stop_loss']]

print(f"Total trades: {len(trades)}")
print(f"Stopped trades: {len(stops)}")

# Let's aggregate by setup type, day type, etc.
setups = collections.Counter([t.get('setup_type', 'unknown') for t in stops])
print("\nStops by setup type:")
for s, count in setups.items():
    print(f"{s}: {count}")

# Print reasoning for the last 5 stopped trades to analyze flaws
print("\nLast 5 Stopped Trades Analysis:")
for t in stops[-5:]:
    print(f"Date: {t.get('entry_time')}, PnL: {t.get('pnl_usd')}")
    print(f"Setup: {t.get('setup_type')}, Direction: {t.get('direction')}")
    
    # find corresponding reasoning
    matching_reasoning = None
    with open(reasoning_file, "r") as f:
        for line in f:
            if not line.strip(): continue
            r = json.loads(line)
            # Match by entry_time approx
            if r.get('trade_entry') == t.get('entry_price') and r.get('trade_direction') == t.get('direction'):
                matching_reasoning = r.get('fabio_reasoning')
                break
    print(f"Reasoning: {matching_reasoning}")
    print("-" * 50)
