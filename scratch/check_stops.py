import json
with open('agent_memory/trades_log.jsonl', 'r') as f:
    for line in f:
        try:
            t = json.loads(line)
            if t.get('logged_at', '') >= '2026-05-29T17:11:00' and t.get('pnl_usd', 0) > 0:
                print(f"{t['date']} {t['direction']} Entry: {t['entry']} - Exit_Stop: {t['stop']} - Target: {t['target']} - PnL: ${t['pnl_usd']}")
        except: pass
