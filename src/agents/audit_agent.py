import json
from pathlib import Path
from src.agents.llm_client import llm_ask
from src.agent_memory import LOG_FILE, TRADES_FILE
# Import dynamic rules manager utilities
from src.agents.dynamic_rules_manager import load_dynamic_rules, save_dynamic_rules, validate_dynamic_rule

DYNAMIC_RULES_FILE = Path(__file__).parent.parent.parent / 'knowledge' / 'dynamic_rules.json'

SYSTEM_AUDIT_PROMPT = """You are the Principal AMT Auditing Agent. Your job is to analyze the trading session's reasoning logs and actual executed trade outcomes under the Auction Market Theory (AMT) framework.
You must identify:
1. Systemic errors (e.g. trading reversals during strong initiative imbalances, bad stops, early entries).
2. Missed setups or highly profitable skipped candidates.
3. Lessons learned to avoid future losses.

You will be given:
1. The existing dynamic rules and heuristics.
2. The day's trading logs (Closed Trades).
3. The day's candidate decisions (including prefiltered/skipped ones).

You must review and update our Active Live Corrections/Dynamic Rules.
- You have full permission to ADD new rules, MODIFY existing rules, or DELETE/PRUNE obsolete or conflicting rules.
- Keep the total number of rules concise (under 10 high-impact rules) to avoid context clutter.

Respond ONLY with valid JSON matching this schema:
{
  "dynamic_rules": [
    {
      "rule_id": "AMT_RULE_XYZ",
      "topic": "<short category, e.g. Reversal, Stop Loss, Initiative>",
      "description": "<detailed, actionable rule, e.g. Do not short the first test of VAH if delta is > 5000 and day_type is trend_up.>",
      "action": "<what the agent should do when encountering this, e.g. skip_trade or reduce_contracts>"
    }
  ],
  "session_learnings": [
    "<bullet point summaries of what went right/wrong today>"
  ]
}"""

def load_dynamic_rules() -> dict:
    if not DYNAMIC_RULES_FILE.exists():
        DYNAMIC_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DYNAMIC_RULES_FILE, 'w', encoding='utf-8') as f:
            json.dump({"dynamic_rules": [], "session_learnings": []}, f, indent=2)
    try:
        with open(DYNAMIC_RULES_FILE, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"dynamic_rules": [], "session_learnings": []}

def save_dynamic_rules(rules: dict) -> None:
    with open(DYNAMIC_RULES_FILE, 'w', encoding='utf-8') as f:
        json.dump(rules, f, indent=2)

def audit_session(date_str: str) -> dict:
    """Read logs for date_str, call Gemini to audit, and update dynamic_rules.json."""
    existing_rules = load_dynamic_rules()

# Validation helper (if not already imported from manager)
# def validate_dynamic_rule(rule: dict) -> bool:
#     """Validate a dynamic rule structure."""
#     required_keys = {'rule_id', 'topic', 'description', 'action'}
#     if not isinstance(rule, dict):
#         return False
#     if not required_keys.issubset(rule.keys()):
#         return False
#     for k in required_keys:
#         if not isinstance(rule[k], str) or not rule[k].strip():
#         return False
#     # Simple action validation could be added here
#     return True
    
    # Read trades log
    trades = []
    if TRADES_FILE.exists():
        try:
            with open(TRADES_FILE, encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        t = json.loads(line)
                        if t.get('date') == date_str:
                            trades.append(t)
        except Exception:
            pass

    # Read reasoning log
    reasonings = []
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        r = json.loads(line)
                        if r.get('date') == date_str:
                            # Truncate long strings to save prompt tokens
                            if 'fabio_reasoning' in r:
                                r['fabio_reasoning'] = r['fabio_reasoning'][:200]
                            if 'andrea_reasoning' in r:
                                r['andrea_reasoning'] = r['andrea_reasoning'][:200]
                            reasonings.append(r)
        except Exception:
            pass

    if not trades and not reasonings:
        print(f"  [AUDIT] No trades or reasonings found for {date_str}. Skipping audit.")
        return existing_rules

    print(f"  [AUDIT] Auditing {len(trades)} trades and {len(reasonings)} decisions for {date_str}...")

    # Build prompt
    prompt_payload = {
        "existing_rules": existing_rules.get("dynamic_rules", []),
        "date": date_str,
        "trades": trades,
        "decisions": reasonings
    }

    user_msg = f"""Analyze the following session log and update our Dynamic Rules:
{json.dumps(prompt_payload, indent=2)}

Respond with JSON only."""

    raw_response = llm_ask(SYSTEM_AUDIT_PROMPT, user_msg)
    if raw_response.startswith('```'):
        raw_response = raw_response.split('```')[1].lstrip('json').strip()

    try:
        updated_data = json.loads(raw_response)
        if "dynamic_rules" in updated_data:
            valid_rules = [r for r in updated_data["dynamic_rules"] if validate_dynamic_rule(r)]
            updated_data["dynamic_rules"] = valid_rules
            save_dynamic_rules(updated_data)
            print(f"  [AUDIT] Success! Dynamic Rules updated. Total rules: {len(updated_data['dynamic_rules'])}")
            return updated_data
    except Exception as e:
        print(f"  [AUDIT] Error parsing Gemini audit response: {e}. Raw response: {raw_response[:500]}")
    
    return existing_rules
