import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

# Notebook IDs
NOTEBOOKS = {
    "fabio": "4c868e52",
    "andrea": "5204f969",
}

QUESTIONS = {
    "fabio": [
        {
            "id": "stop_run_vs_discovery",
            "question": "On July 30 (NQ), we saw a Failed Auction at IB High. Price rejected, but then returned to sweep the high by 1.25 points before collapsing 80 points. How do you distinguish a 'Discovery Spike' from a 'Stop Run' on M1 delta? What footprint signal confirms the sweep is finished (e.g. passive absorption finishing, tape speeding up)?",
        },
        {
            "id": "safety_buffer_nq",
            "question": "Specifically for NQ in a balance day (D-shape), what is your preferred 'Safety Buffer' (in points/ticks) when placing a stop beyond an IB high/low? Do you prefer a tight stop hit by the sweep or a wider 'Structural Stop' that stays outside the liquidity pool?",
        },
        {
            "id": "second_drive_failed_auction",
            "question": "Regarding the 'Second Drive' protocol: If a Failed Auction setup occurs at an IB edge, do you still wait for a second rejection/test, or is the first failed probe above the level sufficient if the Delta and Wall Size (Big Trades) are high enough?",
        }
    ],
    "andrea": [
        {
            "id": "friction_vs_flow_trigger",
            "question": "On Trend Days (like July 29), we hit fixed targets early and miss big runners. When do you transition from 'Friction Management' (Fixed TP) to 'Flow Management' (Trailing)? What is the specific price action or volume trigger to switch models?",
        },
        {
            "id": "trailing_hierarchy_nq",
            "question": "For trailing a runner on NQ, what is your preferred hierarchy? (e.g. 1. Behind last M1 HVN, 2. Break-even + Fixed Offset, 3. Time-based). Please provide a rule for a 3:1 R/R runner.",
        },
        {
            "id": "failed_auction_confirmation_aggression",
            "question": "When Fabio gives a Failed Auction signal but the tape is still aggressive (high delta), how many 'failed attempts' or M1 candles do you wait for before confirming the reversal and entering the squeeze?",
        }
    ]
}

LOG_FILE = Path("agent_memory/july_audit_responses.json")

def nlm_use(notebook_id):
    print(f"Selecting notebook: {notebook_id}...")
    result = subprocess.run(
        [sys.executable, "-m", "notebooklm", "use", notebook_id],
        capture_output=True, text=True
    )
    return result.returncode == 0

def nlm_ask(question):
    print(f"Asking: {question[:100]}...")
    result = subprocess.run(
        [sys.executable, "-m", "notebooklm", "ask", question],
        capture_output=True, text=True, timeout=180
    )
    output = result.stdout.strip()
    # Clean output
    if output.startswith("Answer:"):
        output = output[7:].strip()
    return output

def main():
    responses = []
    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            responses = json.load(f)

    for agent, q_list in QUESTIONS.items():
        if not nlm_use(NOTEBOOKS[agent]):
            print(f"Error selecting notebook for {agent}")
            continue
        
        for q_item in q_list:
            # Check if already answered in this session (optional, but let's run fresh)
            answer = nlm_ask(q_item["question"])
            responses.append({
                "timestamp": datetime.now().isoformat(),
                "agent": agent,
                "id": q_item["id"],
                "question": q_item["question"],
                "answer": answer
            })
            print(f"Received answer ({len(answer)} chars)")

    with open(LOG_FILE, "w") as f:
        json.dump(responses, f, indent=2)
    print(f"All responses saved to {LOG_FILE}")

if __name__ == "__main__":
    main()
