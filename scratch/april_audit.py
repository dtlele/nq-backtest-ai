import json

lines = open('agent_memory/reasoning_log.jsonl', encoding='utf-8-sig').readlines()
lines = [l for l in lines if l.strip()]

# Raggruppa per data
from collections import defaultdict
by_date = defaultdict(list)
for l in lines:
    try:
        d = json.loads(l)
        by_date[d.get('date','?')].append(d)
    except:
        pass

print(f"=== STATO BACKTEST - {len(lines)} barre totali ===\n")
for date in sorted(by_date.keys()):
    bars = by_date[date]
    trades = [b for b in bars if b.get('decision') == 'trade']
    signals_78 = [b for b in bars if b.get('fabio_confidence', 0) >= 78 and b.get('fabio_direction') not in ['none', None]]
    print(f"  {date}  |  {len(bars)} barre  |  segnali>=78: {len(signals_78)}  |  TRADE: {len(trades)}")
    for t in trades:
        print(f"    -> TRADE {t.get('bar_time_et')} {t.get('fabio_direction')} conf={t.get('fabio_confidence')} entry={t.get('fabio_entry')}")
