import json
from pathlib import Path

log_path = Path('agent_memory/trades_log.jsonl')
entries = []
if log_path.exists():
    for line in log_path.read_text(encoding='utf-8-sig').splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass

# Filter for the Apr 3-4 2025 run (date field likely '2025-04-03' etc.)
win_conf = []
loss_conf = []
for e in entries:
    date = e.get('date')
    if date not in ('2025-04-03', '2025-04-04'):
        continue
    pnl = float(e.get('pnl_usd', 0))
    conf = e.get('final_confidence')
    if pnl > 0:
        win_conf.append(conf)
    elif pnl < 0:
        loss_conf.append(conf)

print('Wins:', len(win_conf), 'Confidences:', win_conf)
print('Losses:', len(loss_conf), 'Confidences:', loss_conf)
