import json

orig_stops = {}
with open('agent_memory/reasoning_log.jsonl', encoding='utf-8') as f:
    for line in f:
        r = json.loads(line)
        if r.get('trade_stop') is not None:
            k1 = f"{r['date']}_{r['bar_time_utc']}"
            orig_stops[k1] = r['trade_stop']
            k2 = f"{r['date']}_{r['trade_entry']}"
            orig_stops[k2] = r['trade_stop']

trailed_count = 0
not_trailed_count = 0
with open('agent_memory/trades_log.jsonl', encoding='utf-8') as f:
    for line in f:
        t = json.loads(line)
        if t.get('logged_at', '') > '2026-05-30T11:54:00' and t['exit_reason'] == 'stop':
            k1 = f"{t['date']}_{t['entry_time']}"
            k2 = f"{t['date']}_{t['entry']}"
            orig_stop = orig_stops.get(k1, orig_stops.get(k2))
            
            if orig_stop is not None:
                orig_dist_ticks = abs(t['entry'] - orig_stop) / 0.25
                actual_dist_ticks = abs(t['pnl_ticks'])
                if orig_dist_ticks != actual_dist_ticks:
                    print(f"{t['date']} {t['entry_time'][-14:-9]} | Orig Stop: {orig_stop} ({orig_dist_ticks} ticks) -> Exit: {actual_dist_ticks} ticks. TRAILED!")
                    trailed_count += 1
                else:
                    not_trailed_count += 1

print(f"\nTotal trailing stops: {trailed_count}")
print(f"Total original stops hit: {not_trailed_count}")
