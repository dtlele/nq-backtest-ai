"""
Quantifica quante volte suggested_direction (wall_side) era in CONFLITTO
con la direzione reale dell'IB breakout (ib_position).

wall_side = 'ask' → suggested = long
wall_side = 'bid' → suggested = short

ib_position = 'above IVB' → trend is UP  → correct direction = long
ib_position = 'below IVB' → trend is DOWN → correct direction = short
ib_position = 'inside IVB' → no IB bias (balance)
"""
import json, sys
from pathlib import Path
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REASONING_LOG = Path("agent_memory/reasoning_log.jsonl")

entries = []
with open(REASONING_LOG, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try: entries.append(json.loads(line))
        except: pass

total = 0
mismatch = 0
match = 0
inside_ib = 0
mismatch_examples = []

for e in entries:
    # Ricostruisci suggested_direction dal wall_side (com'era prima del fix)
    wall_side = e.get('wall_side', '')
    old_suggested = 'long' if wall_side == 'ask' else 'short'

    # Direzione corretta dall'IB
    ib_pos = e.get('market_narrative', '') or ''
    # Cerca ib_pos nel reasoning log (non è salvato direttamente, usiamo bar vs IB)
    bar_close = e.get('bar_close', 0)
    ib_high   = e.get('ib_high', 0)
    ib_low    = e.get('ib_low', 0)

    if ib_high == 0 or ib_low == 0:
        continue

    total += 1

    if bar_close > ib_high:
        correct_dir = 'long'
        ib_status = 'above_IB'
    elif bar_close < ib_low:
        correct_dir = 'short'
        ib_status = 'below_IB'
    else:
        inside_ib += 1
        continue  # Inside IB: wall_side logic is ok

    if old_suggested != correct_dir:
        mismatch += 1
        if len(mismatch_examples) < 10:
            mismatch_examples.append({
                'ts': e.get('bar_time_utc','?'),
                'date': e.get('date','?'),
                'setup': e.get('fabio_setup','?'),
                'ib_status': ib_status,
                'wall_side': wall_side,
                'old_suggested': old_suggested,
                'correct_dir': correct_dir,
                'fabio_actual_dir': e.get('fabio_direction','?'),
                'fabio_conf': e.get('fabio_confidence',0),
                'decision': e.get('decision','?'),
            })
    else:
        match += 1

outside_ib = match + mismatch
print(f"=== ANALISI BIAS DIRECTION ===")
print(f"Totale barre analizzate: {total}")
print(f"  - Dentro IB (wall_side ok): {inside_ib}")
print(f"  - Fuori IB (imbalance):     {outside_ib}")
print(f"    - suggested_dir CORRETTA: {match}  ({match/outside_ib*100:.1f}%)")
print(f"    - suggested_dir SBAGLIATA: {mismatch}  ({mismatch/outside_ib*100:.1f}%)")
print()
print(f"Su {outside_ib} barre fuori IB, Fabio e' stato interrogato con")
print(f"il bias SBAGLIATO {mismatch} volte ({mismatch/outside_ib*100:.1f}%)!")
print()
print("=== ESEMPI DI MISMATCH ===")
for ex in mismatch_examples:
    print(f"  {ex['date']} {ex['ts']} | {ex['ib_status']} | wall={ex['wall_side']} "
          f"-> vecchio_bias={ex['old_suggested']} | corretto={ex['correct_dir']} "
          f"| fabio_ha_detto={ex['fabio_actual_dir']} conf={ex['fabio_conf']} | {ex['decision']}")
