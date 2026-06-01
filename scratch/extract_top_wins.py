import json

trades = []
with open('agent_memory/trades_log.jsonl', encoding='utf-8') as f:
    for line in f:
        t = json.loads(line)
        if t.get('logged_at', '') > '2026-05-30T11:54:00':
            trades.append(t)

# Sort by pnl
trades.sort(key=lambda x: x.get('pnl_usd', 0), reverse=True)

top_5 = trades[:5]

print("=== TOP 5 PROFITABLE TRADES ===\n")
for i, t in enumerate(top_5, 1):
    print(f"#{i} Date: {t['date']} | Entry: {t['entry_time']} | PnL: ${t['pnl_usd']:.2f}")
    print(f"Setup: {t.get('setup_type', 'unknown')}")
    print(f"Fabio Reasoning:\n{t.get('fabio_reasoning', 'N/A')}")
    print("-" * 50)
