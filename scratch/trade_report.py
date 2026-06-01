import json
import sys
import os
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')

dates = ['2025-03-10', '2025-03-27']
trades = []
with open('agent_memory/trades_log.jsonl', encoding='utf-8-sig') as f:
    for l in f:
        if l.strip():
            try:
                d = json.loads(l)
                if d.get('date') in dates:
                    trades.append(d)
            except:
                pass

reasoning = {}
with open('agent_memory/reasoning_log.jsonl', encoding='utf-8-sig') as f:
    for l in f:
        if l.strip():
            try:
                d = json.loads(l)
                if d.get('date') in dates and d.get('decision') == 'trade':
                    reasoning[(d['date'], d['bar_time_et'])] = d
            except:
                pass

total = 0.0
for date in dates:
    day = [t for t in trades if t.get('date') == date]
    dpnl = sum(t.get('pnl_usd', 0) for t in day)
    total += dpnl
    print(f"--- {date}  {len(day)} trade  P&L: ${dpnl:+.2f}")
    if not day:
        print("  Nessun trade eseguito.")
    for i, t in enumerate(day, 1):
        et = t.get('entry_time', '')
        bar_et = None
        try:
            bar_et = (datetime.fromisoformat(et.replace('+00:00', '')) - timedelta(hours=4)).strftime('%H:%M')
        except:
            pass
        pnl = t.get('pnl_usd', 0)
        sign = "WIN" if pnl > 0 else "LOSS"
        print(f"  [{sign}] #{i} {bar_et} ET | {t.get('direction')} | entry={t.get('entry')} stop={t.get('stop')} target={t.get('target')}")
        print(f"        exit={t.get('exit_price')} ({t.get('exit_reason')}) | conf={t.get('final_confidence')}% | contracts={t.get('contracts')} | P&L=${pnl:+.2f}")
        r = reasoning.get((date, bar_et))
        if r:
            print(f"        Wall: {r.get('wall_max_size')} contratti @ {r.get('wall_level')} ({r.get('wall_side')}) | delta={r.get('bar_delta')} | vol={r.get('bar_volume')}")
            print(f"        WHY: {r.get('fabio_reasoning', '')[:280]}")
        print()
    print()

print(f"TOTALE P&L: ${total:+.2f}")
