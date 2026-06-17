import json
from src.agents.dynamic_rules_manager import get_active_rules

print("Step 1 active rules for trend_down:")
rules_s1 = get_active_rules(limit=10, day_type='trend_down', step=1)
for r in rules_s1:
    print(f"- {r['rule_id']}: {r['topic']}")

print("\nStep 2 active rules:")
rules_s2 = get_active_rules(limit=10, step=2)
for r in rules_s2:
    print(f"- {r['rule_id']}: {r['topic']}")
