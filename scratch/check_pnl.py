import json

with open('dashboard/public/data/status.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

for t in d.get('ALL_TRADES', []):
    print(f"{t['date']} {t['direction']} target:{t['target']} entry:{t['entry']} stop:{t['stop']}")
