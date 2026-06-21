import re
import json

log_file = r"C:\Users\Mauro\.gemini\antigravity\brain\bb315aae-2c20-475b-aa04-0107b9de870d\.system_generated\tasks\task-731.log"
out_file = r"C:\Users\Mauro\Documents\nq-backtest\dashboard\public\data\v2_proposals.json"

proposals = []
current_proposal = {}

with open(log_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("--- Barra"):
            # --- Barra 1 : 09:30 ---
            m = re.search(r"--- Barra \d+ : (\d{2}:\d{2}) ---", line)
            if m:
                if current_proposal:
                    proposals.append(current_proposal)
                current_proposal = {
                    "date": "2025-04-30",
                    "bar_time_et": m.group(1),
                    "run": "v2_executor"
                }
        elif "[Executor] Valutando" in line and current_proposal:
            m = re.search(r"al prezzo (\d+(?:\.\d+)?)", line)
            if m:
                current_proposal["entry"] = float(m.group(1))
        elif "[RESULT] Action:" in line and current_proposal:
            m = re.search(r"Action: (\w+) \(Confidenza: ([\d\.]+)\)", line)
            if m:
                action = m.group(1)
                current_proposal["direction"] = action.lower() if action != "HOLD" else "hold"
                current_proposal["decision"] = "trade" if action != "HOLD" else "no_trade"
                current_proposal["confidence"] = int(float(m.group(2)) * 100)
        elif "[REASON]" in line and current_proposal:
            current_proposal["fabio_reasoning"] = line.replace("[REASON]", "").strip()
        elif "[LEVELS]" in line and current_proposal:
            m1 = re.search(r"Stop Loss: ([\d\.]+)", line)
            m2 = re.search(r"Take Profit: ([\d\.]+)", line)
            if m1: current_proposal["stop"] = float(m1.group(1))
            if m2: current_proposal["target"] = float(m2.group(1))

if current_proposal:
    proposals.append(current_proposal)

if proposals:
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(proposals, f, indent=2)
    print(f"Recuperate {len(proposals)} decisioni dal log!")
else:
    print("Nessuna decisione trovata nel log.")
