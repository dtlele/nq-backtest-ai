"""
Analisi opportunità perse: quanti no_trade avevano direzione definita
e come è andato effettivamente il prezzo (direzione verificata sul close della stessa barra)
"""
import json
from pathlib import Path
from collections import Counter

REASONING_LOG = Path("agent_memory/reasoning_log.jsonl")

entries = []
with open(REASONING_LOG, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except:
            pass

# ── 1. No_trade CON direzione definita (fabio_direction != none) ──
missed_with_dir = [
    e for e in entries
    if e.get('decision') == 'no_trade'
    and e.get('fabio_direction') not in ('none', None, '')
]

print(f"=== NO_TRADE CON DIREZIONE DEFINITA: {len(missed_with_dir)} ===\n")

# Raggruppa per conf
conf_buckets = Counter()
winning_if_taken = 0
losing_if_taken  = 0
for e in missed_with_dir:
    conf = e.get('fabio_confidence', 0)
    bucket = (conf // 10) * 10
    conf_buckets[bucket] += 1

    # Stima se avrebbe vinto: direzione Fabio vs movimento close vs open
    fab_dir   = e.get('fabio_direction')
    bar_open  = e.get('bar_open', 0)
    bar_close = e.get('bar_close', 0)
    bar_move  = bar_close - bar_open  # positivo = salita
    if fab_dir == 'long' and bar_move > 0:
        winning_if_taken += 1
    elif fab_dir == 'short' and bar_move < 0:
        winning_if_taken += 1
    else:
        losing_if_taken += 1

print("Distribuzione per confidence:")
for bucket in sorted(conf_buckets.keys()):
    print(f"  conf {bucket}-{bucket+9}: {conf_buckets[bucket]} candidati")

print(f"\nSe fossero stati presi (stima direzione barra):")
print(f"  Avrebbero vinto: {winning_if_taken}")
print(f"  Avrebbero perso: {losing_if_taken}")
pct = winning_if_taken / len(missed_with_dir) * 100 if missed_with_dir else 0
print(f"  Win rate teorico: {pct:.1f}%")

# ── 2. No_trade per no_trade_reason che contiene 'prudenza' o 'confidence' ──
print("\n=== NO_TRADE REASON BREAKDOWN ===")
reasons = Counter(e.get('no_trade_reason', 'unknown') for e in entries if e.get('decision') == 'no_trade')
for r, cnt in reasons.most_common(15):
    print(f"  [{cnt:4d}] {r}")

# ── 3. Mostra i top 10 missed con conf più alta e direzione definita ──
top_missed = sorted(missed_with_dir, key=lambda e: e.get('fabio_confidence', 0), reverse=True)[:10]
print(f"\n=== TOP 10 MISSED CON CONF PIÙ ALTA ===")
for e in top_missed:
    fab_dir  = e.get('fabio_direction')
    conf     = e.get('fabio_confidence')
    entry    = e.get('fabio_entry')
    target   = e.get('fabio_target')
    ts       = e.get('bar_time_utc', '?')
    reason   = e.get('no_trade_reason', '?')
    bar_open  = e.get('bar_open', 0)
    bar_close = e.get('bar_close', 0)
    move = bar_close - bar_open
    went_right = (fab_dir == 'long' and move > 0) or (fab_dir == 'short' and move < 0)
    emoji = '✅' if went_right else '❌'
    print(f"  {emoji} {ts} | {fab_dir} conf={conf} | entry={entry} target={target}")
    print(f"     bar move: {move:+.2f} pts | skip reason: {reason}")
