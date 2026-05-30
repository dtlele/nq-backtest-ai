import json
from collections import defaultdict

wins = []
losses = []

with open('agent_memory/trades_log.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        try:
            t = json.loads(line)
            if t.get('logged_at', '') < "2026-05-30T07:55:00":
                continue
            
            # Filter backward stops
            direction = t.get('direction', 'none')
            entry = t.get('entry')
            stop = t.get('stop')
            if direction == 'long' and stop is not None and entry is not None and stop >= entry:
                continue
            if direction == 'short' and stop is not None and entry is not None and stop <= entry:
                continue
                
            pnl = float(t.get('pnl_usd', 0))
            if pnl > 10:
                wins.append(t)
            elif pnl < -10:
                losses.append(t)
        except Exception:
            pass

print(f"Total Wins: {len(wins)}")
print(f"Total Losses: {len(losses)}")

print("\n--- WINS ANALYTICS ---")
for w in wins:
    print(f"[{w.get('date')} {w.get('entry_time')[11:16]}] {w.get('direction')} +${w.get('pnl_usd')} (Contracts: {w.get('contracts')})")
    print(f"Fabio Conf: {w.get('fabio_confidence')} | Andrea Conf: {w.get('andrea_confidence')}")
    print(f"Fabio: {w.get('fabio_reasoning')}")
    print(f"Andrea: {w.get('andrea_reasoning')}")
    print("-")

print("\n--- LOSSES ANALYTICS ---")
for l in losses:
    print(f"[{l.get('date')} {l.get('entry_time')[11:16]}] {l.get('direction')} -${abs(float(l.get('pnl_usd')))} (Contracts: {l.get('contracts')})")
    print(f"Fabio Conf: {l.get('fabio_confidence')} | Andrea Conf: {l.get('andrea_confidence')}")
    print(f"Fabio: {l.get('fabio_reasoning')}")
    print(f"Andrea: {l.get('andrea_reasoning')}")
    print("-")
