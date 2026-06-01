import json

lines = open('agent_memory/reasoning_log.jsonl', encoding='utf-8-sig').readlines()
lines = [l for l in lines if l.strip()]
if not lines:
    print("Log vuoto, run non ancora iniziata.")
    exit()

last = json.loads(lines[-1])
print("=== STATO ATTUALE ===")
print(f"Barra: {last.get('date')} {last.get('bar_time_et')} | dir={last.get('fabio_direction')} conf={last.get('fabio_confidence')}")
print(f"Barre analizzate: {len(lines)}")
print()

signals = []
for l in lines:
    try:
        d = json.loads(l)
        if d.get('fabio_confidence', 0) >= 70 and d.get('fabio_direction') not in ['none', 'light_skip', 'prefiltered', None]:
            signals.append(d)
    except:
        pass

print(f"Segnali >= 70 conf trovati: {len(signals)}")
for s in signals:
    print(f"  {s.get('bar_time_et')} dir={s.get('fabio_direction')} conf={s.get('fabio_confidence')} entry={s.get('fabio_entry')} stop={s.get('fabio_stop')} target={s.get('fabio_target')}")
    r = s.get('fabio_reasoning', '')
    print(f"  -> {r[:160]}")
    print()
