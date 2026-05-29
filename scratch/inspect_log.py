"""
Ispeziona la struttura reale del reasoning_log e identifica
i candidati dove il prezzo stava chiaramente muovendo in imbalance
ma Fabio ha dato conf bassa o dir=none.
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

# Mostra i campi disponibili del primo entry
print("=== CAMPI DISPONIBILI NEL REASONING LOG ===")
if entries:
    print(json.dumps(list(entries[0].keys()), indent=2))
    print()

# Conta le decisioni
decisions = Counter(e.get('decision') for e in entries)
print(f"=== DISTRIBUZIONE DECISIONI (ultimi {len(entries)} entries) ===")
for k, v in decisions.most_common():
    print(f"  {k}: {v}")

print()

# Mostra ultimi 5 NO_TRADE per capire i campi fabio
no_trades = [e for e in entries if e.get('decision') == 'NO_TRADE']
print(f"=== ULTIMI 5 NO_TRADE (su {len(no_trades)} totali) ===")
for e in no_trades[-5:]:
    print(json.dumps(e, indent=2, default=str))
    print("---")
