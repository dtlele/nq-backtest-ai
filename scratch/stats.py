import json
with open('agent_memory/trades_log.jsonl', 'r', encoding='utf-8') as f:
    trades = [json.loads(line) for line in f if line.strip()]

partial = [t for t in trades if t.get('exit_reason') == 'partial_tp']
trail = [t for t in trades if t.get('exit_reason') == 'trailing_stop']

print('Partial TP (half at target, half BE):', len(partial))
print('Trailing Stop (closed before target/stop):', len(trail))
for t in trail:
    print(f"  -> Dir: {t.get('direction')} | Entry: {t.get('entry')} | Target: {t.get('target')} | Exit: {t.get('exit_price')} | PnL: ${t.get('pnl_usd')}")
