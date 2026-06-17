import json
from pathlib import Path

reasoning_log = Path('agent_memory/reasoning_log.jsonl')
trades_found = []

with open(reasoning_log) as f:
    for line in f:
        try:
            r = json.loads(line)
            if r.get('fabio_direction') in ('long','short') and r.get('fabio_confidence',0) >= 60:
                trades_found.append({
                    'date': r.get('date'),
                    'bar_time_et': r.get('bar_time_et'),
                    'bar_time_utc': r.get('bar_time_utc'),
                    'direction': r.get('fabio_direction'),
                    'confidence': r.get('fabio_confidence'),
                    'entry': r.get('fabio_entry'),
                    'stop': r.get('fabio_stop'),
                    'target': r.get('fabio_target'),
                    'decision': r.get('decision'),
                    'no_trade_reason': str(r.get('no_trade_reason',''))[:60]
                })
        except:
            pass

print(f'Trade proposti da Fabio (conf>=60): {len(trades_found)}')
for t in trades_found[:15]:
    print(f"  {t['date']} {t['bar_time_et']} {t['direction']} conf={t['confidence']} dec={t['decision']} | {t['no_trade_reason']}")
    print(f"    entry={t['entry']} stop={t['stop']} target={t['target']}")
