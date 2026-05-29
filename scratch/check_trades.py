import json
from pathlib import Path

log_file = Path('agent_memory/trades_log.jsonl')
if not log_file.exists():
    print("No trades logged yet.")
    exit(0)

trades = []
with open(log_file, 'r') as f:
    for line in f:
        try:
            t = json.loads(line)
            if t.get('date') in ['2025-11-13', '2025-11-14'] and t.get('decision') == 'trade':
                trades.append(t)
        except:
            pass

unique_trades = {}
for t in trades:
    # use bar time or logged time as key
    key = t.get('bar_time_utc')
    if key:
        unique_trades[key] = t

for k, t in unique_trades.items():
    d = t.get('trade_direction')
    e = t.get('trade_entry')
    x = t.get('trade_exit_reason')
    pnl = t.get('trade_pnl_ticks')
    c = t.get('contracts', 1)
    
    over = ""
    if "override" in str(t.get('fabio_reasoning', '')).lower() or "chaser" in str(t.get('fabio_reasoning', '')).lower() or "override" in str(t.get('no_trade_reason', '')):
        over = "[CHASER]"
        
    print(f"{t.get('date')} Time: {k[11:16]} | {over} {str(d).upper()} | Entry: {e} | Exit: {x} | PnL Ticks: {pnl} | Contracts: {c}")
