import json
from pathlib import Path

DYNAMIC_RULES_FILE = Path(r"c:\Users\Mauro\Documents\nq-backtest\knowledge\dynamic_rules.json")

with open(DYNAMIC_RULES_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Rimuovi le ultime due regole aggiunte (AMT_RULE_180 e AMT_RULE_208)
data["dynamic_rules"] = [r for r in data["dynamic_rules"] if r.get("rule_id") not in ["AMT_RULE_180", "AMT_RULE_208"]]

with open(DYNAMIC_RULES_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print("Regole rimosse con successo dal file JSON.")
