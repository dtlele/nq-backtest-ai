import json
from pathlib import Path
from typing import List, Dict

# Path to the dynamic rules JSON file
DYNAMIC_RULES_FILE = Path(__file__).parent.parent.parent / 'knowledge' / 'dynamic_rules.json'

# Allowed actions for validation (extend as needed)
ALLOWED_ACTIONS = {
    'adjust_stop_placement_beyond_absorption_levels',
    'reduce_contracts_low_r_ratio_ivb_breakout',
    'skip_trade',
    'reduce_contracts_or_skip',
    'adjust_stop_placement_beyond_nearest_absorption',
    'skip_trade_macro_window',
    'require_delta_confirmation',
    'widen_stop_in_volatility',
}

def load_dynamic_rules() -> Dict:
    """Load dynamic rules from the JSON file, creating it if missing."""
    if not DYNAMIC_RULES_FILE.exists():
        DYNAMIC_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DYNAMIC_RULES_FILE, 'w', encoding='utf-8') as f:
            json.dump({"dynamic_rules": [], "session_learnings": []}, f, indent=2)
    try:
        with open(DYNAMIC_RULES_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        # Return empty structure on any read error
        return {"dynamic_rules": [], "session_learnings": []}

def save_dynamic_rules(rules: Dict) -> None:
    """Persist the provided rule dictionary to disk."""
    DYNAMIC_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DYNAMIC_RULES_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, indent=2)

def validate_dynamic_rule(rule: Dict) -> bool:
    """Validate a single dynamic rule.

    Required keys: rule_id, topic, description, action, status, successes, failures, probation_days.
    * ``action`` must be one of the known ALLOWED_ACTIONS.
    * ``status`` must be 'active' or 'probation'.
    Returns ``True`` if the rule is valid, ``False`` otherwise.
    """
    required_keys = {'rule_id', 'topic', 'description', 'action', 'status', 'successes', 'failures', 'probation_days'}
    if not isinstance(rule, dict):
        return False
    if not required_keys.issubset(rule.keys()):
        # Auto-migrate old rules
        if 'status' not in rule: rule['status'] = 'active'
        if 'successes' not in rule: rule['successes'] = 0
        if 'failures' not in rule: rule['failures'] = 0
        if 'probation_days' not in rule: rule['probation_days'] = 0
        if not {'rule_id', 'topic', 'description', 'action'}.issubset(rule.keys()):
            return False

    for key in ['rule_id', 'topic', 'description', 'action', 'status']:
        if not isinstance(rule[key], str) or not rule[key].strip():
            return False
            
    if not isinstance(rule['successes'], int) or not isinstance(rule['failures'], int) or not isinstance(rule['probation_days'], int):
        return False
        
    if rule['action'] not in ALLOWED_ACTIONS:
        return False
    if rule['status'] not in ['active', 'probation']:
        return False
        
    return True

def get_active_rules(limit: int = 3) -> List[Dict]:
    """Return a limited list of active dynamic rules.

    The function filters the rules to only include those with status == 'active'.
    It then returns the first ``limit`` rules from the filtered list.
    """
    data = load_dynamic_rules()
    rules = data.get('dynamic_rules', [])
    active_rules = [r for r in rules if r.get('status') == 'active']
    return active_rules[:limit]
