import json
from pathlib import Path

# Check oldest cache snapshot timestamp
snap_dir = Path('agent_memory/cache_snapshots')
snaps = sorted(snap_dir.glob('*.json'))
print('=== CACHE SNAPSHOTS (ordine cronologico) ===')
for s in snaps:
    data = json.loads(s.read_text(encoding='utf-8'))
    entries = data.get('entries', {})
    print(f'{s.name} -> {len(entries)} entries')

print()

# Analyze trades_log by run period - look at dates and confidence distribution
log = Path('agent_memory/trades_log.jsonl')
trades = [json.loads(l) for l in log.read_text(encoding='utf-8-sig').splitlines() if l.strip()]
print(f'=== TRADES LOG: {len(trades)} trade totali ===')

# Group by approximate run period using confidence as proxy
conf_by_date = {}
for t in trades:
    d = t.get('date', '')[:7]  # YYYY-MM
    conf = t.get('final_confidence', 0)
    pnl = float(t.get('pnl_usd', 0))
    if d not in conf_by_date:
        conf_by_date[d] = {'confs': [], 'pnls': []}
    conf_by_date[d]['confs'].append(conf)
    conf_by_date[d]['pnls'].append(pnl)

print(f"{'Mese':<10} | {'Trades':<7} | {'Avg Conf':<10} | {'Conf Range':<15} | {'PnL totale':<12}")
print('-'*62)
for month, v in sorted(conf_by_date.items()):
    n = len(v['confs'])
    avg_c = sum(v['confs'])/n
    pnl = sum(v['pnls'])
    c_range = f"{min(v['confs'])}-{max(v['confs'])}"
    print(f"{month:<10} | {n:<7} | {avg_c:<10.1f} | {c_range:<15} | ${pnl:<12.2f}")

# Also look at confidence distribution overall
all_confs = [t.get('final_confidence', 0) for t in trades]
unique_confs = sorted(set(all_confs))
print(f"\n=== DISTRIBUZIONE CONFIDENZE ===")
for c in unique_confs:
    count = all_confs.count(c)
    wins = sum(1 for t in trades if t.get('final_confidence') == c and float(t.get('pnl_usd', 0)) > 10)
    losses = sum(1 for t in trades if t.get('final_confidence') == c and float(t.get('pnl_usd', 0)) < -10)
    wr = wins/(wins+losses)*100 if (wins+losses) > 0 else 0
    print(f"  Conf {c}: {count} trade | {wins}W/{losses}L | WR {wr:.0f}%")
