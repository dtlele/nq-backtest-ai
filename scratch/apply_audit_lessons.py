
import json
from pathlib import Path

KNOWLEDGE_PATH = Path('knowledge/fabio_knowledge.json')
ANDREA_PATH = Path('knowledge/andrea_knowledge.json')

def update_lessons():
    print("Updating Knowledge with August Lessons...")
    
    # Update Fabio
    with open(KNOWLEDGE_PATH, 'r', encoding='utf-8') as f:
        fabio = json.load(f)
    
    # Add Surgical Stop and Macro Rules
    if 'trading_rules' not in fabio: fabio['trading_rules'] = {}
    
    fabio['trading_rules']['macro_timing_filter'] = {
        "rule": "Do not initiate new trades between 09:55 and 10:15 EST.",
        "reason": "Macroeconomic news releases at 10:00 AM create a 'Liquidity Void' where Market Makers pull limit orders, leading to high-slippage stop runs.",
        "priority": "CRITICAL"
    }
    
    fabio['trading_rules']['second_drive_rule'] = {
        "rule": "Never trade the 'First Drive' or the initial hit of a level.",
        "reason": "The first test only establishes the presence of a passive participant. A genuine Failed Auction/Squeeze is confirmed only on the 'Second Drive' (re-test).",
        "action": "Wait for a retracement and a second failed attempt to break the level."
    }
    
    fabio['trading_rules']['surgical_stop_protocol'] = {
        "rule": "Stop Loss must be placed 1-2 ticks behind the Big Trade cluster or the Volume Profile Ledge (LVN).",
        "constraint": "Maximum acceptable risk is $500 (0.5% of $100k). If the structural stop required is wider, reduce contracts or skip.",
        "standard": "MNQ contracts only for granular sizing."
    }
    
    with open(KNOWLEDGE_PATH, 'w', encoding='utf-8') as f:
        json.dump(fabio, f, indent=2)

    # Update Andrea (Confirmation)
    with open(ANDREA_PATH, 'r', encoding='utf-8') as f:
        andrea = json.load(f)
        
    andrea['confirmation_rules'] = andrea.get('confirmation_rules', {})
    andrea['confirmation_rules']['initiative_check'] = {
        "rule": "Wait for the 'Initiative' phase after 'Response' (Absorption).",
        "requirement": "Delta must flip to positive (for longs) or negative (for shorts) and show diagonal imbalances. Do not trade pure absorption without aggression."
    }
    
    with open(ANDREA_PATH, 'w', encoding='utf-8') as f:
        json.dump(andrea, f, indent=2)
    
    print("Knowledge updated successfully.")

if __name__ == "__main__":
    update_lessons()
