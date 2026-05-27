import sys
from pathlib import Path
import json

# Add project root to sys.path
project_root = Path("c:/Users/Mauro/Documents/nq-backtest")
sys.path.append(str(project_root))

from build_knowledge_v2 import nlm_ask, nlm_use, NOTEBOOKS

def audit_july_trade(date_str, time_utc, side_hint):
    """
    Asks Fabio and Andrea for a fresh analysis of a specific July window.
    """
    print(f"\n--- Auditing July {date_str} at {time_utc} ({side_hint}) ---")
    
    prompt = f"""
    Analyze the raw price and order flow data for the candidate at {time_utc} UTC on {date_str}.
    
    CONTEXT: This is a July 'Summer Market' candidate. In our recent August audit, we established strict rules:
    1. Macro Timing Filter: Skip 09:55-10:15 EST.
    2. Participation Floor: 20,000 contracts per M5.
    
    QUESTION FOR EXPERTS:
    - Looking ONLY at the raw Delta and Big Trades for this candidate, was this an institutional setup that should have been taken DESPITE potentially lower volume?
    - If it's a 'Squeeze' or 'Failed Auction', does the Big Trade activity (>30 contracts) provide enough conviction to relax the 20k volume rule?
    - Where would you place a 'Surgical Stop' to protect against summer noise?
    
    Respond as if you are seeing this for the first time. Respond only with the analysis.
    """
    
    # FABIO
    print("Querying Fabio...")
    nlm_use(NOTEBOOKS["fabio"])
    fabio_resp = nlm_ask(prompt)
    print(f"Fabio: {fabio_resp[:200]}...")
    
    # ANDREA
    print("Querying Andrea...")
    nlm_use(NOTEBOOKS["andrea"])
    andrea_resp = nlm_ask(prompt)
    print(f"Andrea: {andrea_resp[:200]}...")
    
    return {
        "date": date_str,
        "time_utc": time_utc,
        "fabio": fabio_resp,
        "andrea": andrea_resp
    }

if __name__ == "__main__":
    # Audit candidates
    candidates = [
        ("2025-07-07", "15:00", "Long (Prev Winner)"),
        ("2025-07-08", "13:55", "Short (Prev Loser)"),
        ("2025-07-08", "14:15", "Short (Prev Loser)"),
        ("2025-07-11", "15:20", "Long (New Potential - rejected due to 6k vol)")
    ]
    
    results = []
    for date, time, hint in candidates:
        res = audit_july_trade(date, time, hint)
        results.append(res)
        
    with open("agent_memory/july_opportunity_audit_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nAudit complete. Results saved to agent_memory/july_opportunity_audit_results.json")
