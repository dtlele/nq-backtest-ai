import json
from pathlib import Path

DYNAMIC_RULES_FILE = Path(r"c:\Users\Mauro\Documents\nq-backtest\knowledge\dynamic_rules.json")

with open(DYNAMIC_RULES_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

new_rules = [
    {
        "rule_id": "AMT_RULE_180",
        "topic": "Conferma dell'iniziativa SHORT",
        "description": "Evitare trade SHORT in assenza di delta negativo coerente nell'ultimo footprint, anche se il prezzo si trova sotto l'Initial Balance Low (IBL). Il delta deve allinearsi al ribasso.",
        "action": "require_delta_confirmation",
        "status": "active",
        "successes": 0,
        "failures": 0,
        "probation_days": 0
    },
    {
        "rule_id": "AMT_RULE_208",
        "topic": "Gestione Stop in Volatilita",
        "description": "Allargare gli stop loss (aggiungere ulteriore buffer ai 10 tick standard) in contesti altamente volatili o se ci sono enormi muri in opposizione (come l'assorbimento recente), per evitare stop-out prematuri in caso di spike di liquidita.",
        "action": "widen_stop_in_volatility",
        "status": "active",
        "successes": 0,
        "failures": 0,
        "probation_days": 0
    }
]

# Append new rules if not already present
for nr in new_rules:
    if not any(r.get("rule_id") == nr["rule_id"] for r in data["dynamic_rules"]):
        data["dynamic_rules"].append(nr)

with open(DYNAMIC_RULES_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)

print("Regole dinamiche aggiunte con successo.")
