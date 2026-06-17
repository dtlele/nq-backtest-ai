import json
from pathlib import Path

f = Path('agent_memory/reasoning_log.jsonl')
with open(f, 'r', encoding='utf-8') as fp:
    for line in fp:
        if not line.strip():
            continue
        r = json.loads(line)
        bt = r.get('bar_time_et', '')
        if bt.startswith('10:4') or bt.startswith('10:46'):
            print("Date:", r.get('date'), "| Bar:", bt,
                  "| conf=", r.get('fabio_confidence'),
                  "| dir=", r.get('fabio_direction'),
                  "| decision=", r.get('decision'),
                  "| reason=", r.get('no_trade_reason', ''))
            print("  entry=", r.get('fabio_entry'),
                  "stop=", r.get('fabio_stop'),
                  "target=", r.get('fabio_target'))
            print()
