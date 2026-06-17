import json

initial_equity = 50488.40 # starting before May 19 (after May 19 rerun it became 50704.40)
equity = initial_equity

print(f"Initial: {equity}")
with open("agent_memory/trades_log.jsonl", "r") as f:
    for line in f:
        t = json.loads(line.strip())
        # only look at trades from 2025-05-19 onwards
        if t["date"] >= "2025-05-19":
            equity += t["pnl_usd"]
            print(f"{t['date']} | pnl: {t['pnl_usd']:.2f} | equity: {equity:.2f} | reason: {t['exit_reason']}")
