import re

log_file = r"C:\Users\Mauro\.gemini\antigravity\brain\e86b7458-2bf7-4121-9908-1844e8f5d6dd\.system_generated\tasks\task-7819.log"

trades = []
current_trade = None

with open(log_file, "r", encoding="utf-8") as f:
    for line in f:
        # Match trade open
        open_match = re.search(r"\[TRADE OPEN\] dir=(long|short) entry=([0-9.]+) stop=([0-9.]+) target=([0-9.]+)", line)
        if open_match:
            current_trade = {
                "dir": open_match.group(1),
                "entry": float(open_match.group(2)),
                "stop": float(open_match.group(3)),
                "target": float(open_match.group(4)),
                "outcome": "Unknown",
                "rr_blocked": [],
                "time": re.search(r"^ *(.*?) UTC", line).group(1) if re.search(r"^ *(.*?) UTC", line) else "?"
            }
            # The line format might be `  14:35 UTC [TRADE OPEN] ...` or `  [TRADE OPEN] ...`
            time_m = re.search(r"([0-9]{2}:[0-9]{2} UTC)", line)
            if time_m:
                current_trade["time"] = time_m.group(1)
            trades.append(current_trade)
            
        if current_trade:
            if "[TRAIL BLOCKED]" in line:
                rr_m = re.search(r"R:R=([-0-9.]+)", line)
                if rr_m:
                    current_trade["rr_blocked"].append(float(rr_m.group(1)))
            
            if "Stop hit." in line:
                current_trade["outcome"] = "Stop"
                current_trade = None
            elif "Target hit!" in line:
                current_trade["outcome"] = "Target"
                current_trade = None
            elif "[REVERSE OPEN]" in line:
                current_trade["outcome"] = "Reversed"
                current_trade = None
            elif "Daily stops:" in line and "Stop hit." not in line:
                # Some other exit?
                pass

print(f"Total trades parsed: {len(trades)}")
stops = [t for t in trades if t['outcome'] == 'Stop']
targets = [t for t in trades if t['outcome'] == 'Target']

print(f"Stops: {len(stops)}")
print(f"Targets: {len(targets)}")
print("\n--- ANALISI STOP PUNITIVI ---")
for i, t in enumerate(stops):
    risk = abs(t['entry'] - t['stop'])
    max_rr = max(t['rr_blocked']) if t['rr_blocked'] else 0
    print(f"Trade #{i+1}: {t['dir'].upper()} @ {t['entry']} | Stop {t['stop']} (Risk: {risk:.2f} pts) | Max R:R Visto: {max_rr:.2f}")

