import sys
from pathlib import Path
import json

# Add project root to sys.path
project_root = Path("c:/Users/Mauro/Documents/nq-backtest")
sys.path.append(str(project_root))

from build_knowledge_v2 import nlm_ask, nlm_use, NOTEBOOKS

def ask_methodology():
    print("\n--- INTERVIEWING EXPERTS ON METHODOLOGY ---")
    
    prompt = """
    We are conducting a systematic backtest on NQ (E-mini) futures and we have some critical methodology questions:
    
    1. VOLUME THRESHOLD: We are using a 20,000 contract per M5 candle floor to identify institutional participation. 
       - Does Fabio's '20k rule' refer to the Micro (MNQ) or the Full E-mini (NQ)? 
       - If it's for MNQ, what is the equivalent 'Institutional Floor' for the Full NQ contract (e.g., 2,000, 5,000, 10,000)?
    
    2. REVERSAL STRATEGY: In months with low liquidity (like July or August) where the 20k momentum participation floor is rarely met, how does Fabio transition to a 'Reversal' or 'Fading' strategy? 
       - What are the rules for identifying a Reversal setup on the Value Area High/Low or Initial Balance high/low? 
       - Does he still require a minimum volume floor for Reversals?
    
    3. THE 30-MINUTE OPEN RULE: We currently skip candidates before 10:00 EST (09:30-10:00 window). Is this correct even if we see massive volume (e.g. 24k) exactly at 09:30?
    
    Please provide clear, direct answers based on Fabio's and Andrea's teachings.
    """
    
    # FABIO
    print("\nQuerying Fabio...")
    nlm_use(NOTEBOOKS["fabio"])
    fabio_resp = nlm_ask(prompt)
    print(f"\nFABIO'S RESPONSE:\n{fabio_resp}")
    
    # ANDREA
    print("\nQuerying Andrea...")
    nlm_use(NOTEBOOKS["andrea"])
    andrea_resp = nlm_ask(prompt)
    print(f"\nANDREA'S RESPONSE:\n{andrea_resp}")
    
    with open("agent_memory/methodology_interview_results.json", "w") as f:
        json.dump({"fabio": fabio_resp, "andrea": andrea_resp}, f, indent=2)

if __name__ == "__main__":
    ask_methodology()
