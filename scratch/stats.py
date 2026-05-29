import json

state = json.load(open("agent_memory/session_state.json"))
print(state)

wins = 0
losses = 0
total_pnl = 0

with open("agent_memory/trades_log.jsonl", "r") as f:
    for line in f:
        if not line.strip(): continue
        t = json.loads(line)
        pnl = t.get("pnl_usd", 0)
        total_pnl += pnl
        if pnl > 0:
            wins += 1
        else:
            losses += 1

print(f"Total trades: {wins + losses}")
print(f"Wins: {wins}, Losses: {losses}")
print(f"Total PnL in trades_log: {total_pnl}")
