import re
import sys

log_file = r"C:\Users\Mauro\.gemini\antigravity\brain\e86b7458-2bf7-4121-9908-1844e8f5d6dd\.system_generated\tasks\task-8037.log"

trades = []
current_trade = None

with open(log_file, "r", encoding="utf-8") as f:
    for line in f:
        # Match reasoning block
        if line.strip().startswith("reason:"):
            reason = line.strip().replace("reason: ", "")
            # We save it in a temporary variable, it belongs to the next TRADE OPEN
            # Actually, reasoning appears *before* [TRADE OPEN]
            last_reason = reason
            continue
            
        open_match = re.search(r"\[TRADE OPEN\] dir=(long|short) entry=([0-9.]+) stop=([0-9.]+) target=([0-9.]+)", line)
        if open_match:
            time_m = re.search(r"([0-9]{2}:[0-9]{2} UTC)", line)
            current_trade = {
                "dir": open_match.group(1),
                "entry": float(open_match.group(2)),
                "stop": float(open_match.group(3)),
                "target": float(open_match.group(4)),
                "outcome": "IN CORSO",
                "pnl": 0.0,
                "reason": last_reason if 'last_reason' in locals() else "N/A",
                "time": time_m.group(1) if time_m else "?",
                "apm_notes": []
            }
            trades.append(current_trade)
            
        if current_trade:
            if "Trailing SL" in line or "[TRAILED SL]" in line or "[TRAILING SL]" in line:
                current_trade["apm_notes"].append("Trailed SL")
            elif "[TRAIL BLOCKED]" in line:
                current_trade["apm_notes"].append("Trail Blocked")
            
            if "Stop hit." in line:
                current_trade["outcome"] = "STOP LOSS"
                # rough pnl calculation
                if current_trade["dir"] == "long":
                    current_trade["pnl"] = current_trade["stop"] - current_trade["entry"]
                else:
                    current_trade["pnl"] = current_trade["entry"] - current_trade["stop"]
                current_trade = None
            elif "Target hit!" in line:
                current_trade["outcome"] = "TARGET"
                if current_trade["dir"] == "long":
                    current_trade["pnl"] = current_trade["target"] - current_trade["entry"]
                else:
                    current_trade["pnl"] = current_trade["entry"] - current_trade["target"]
                current_trade = None
            elif "EOD" in line and "Close" in line:
                current_trade["outcome"] = "CHIUSURA EOD"
                current_trade = None

print("=== AUDIT TRADE BACKTEST IN CORSO ===")
print(f"Totale Trade Registrati: {len(trades)}\n")

for i, t in enumerate(trades):
    status = t['outcome']
    pnl_str = f"{t['pnl']:+.2f} pts" if status != "IN CORSO" else "TBD"
    notes = ", ".join(set(t['apm_notes'])) if t['apm_notes'] else "Nessun intervento APM"
    print(f"Trade #{i+1} [{t['time']}] | {t['dir'].upper()} | Entry: {t['entry']} | Stop: {t['stop']} | Target: {t['target']}")
    print(f"  Esito: {status} ({pnl_str})")
    print(f"  Note Gestione: {notes}")
    print(f"  Ragionamento: {t['reason']}\n")

# Summary
stops = sum(1 for t in trades if t['outcome'] == "STOP LOSS")
targets = sum(1 for t in trades if t['outcome'] == "TARGET")
open_t = sum(1 for t in trades if t['outcome'] == "IN CORSO")

print("--- RIASSUNTO ---")
print(f"Finiti a Target: {targets}")
print(f"Finiti a Stop:   {stops}")
print(f"Attualmente In Corso: {open_t}")
