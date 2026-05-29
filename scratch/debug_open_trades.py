import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
log_file = r"C:\Users\Mauro\.gemini\antigravity\brain\e86b7458-2bf7-4121-9908-1844e8f5d6dd\.system_generated\tasks\task-8037.log"

entries_to_find = ["25640.75", "25650.75", "25372.25", "25345.5"]

with open(log_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

for target_entry in entries_to_find:
    print(f"=== ANALISI TRADE CON ENTRY {target_entry} ===")
    capturing = False
    for line in lines:
        if "[TRADE OPEN]" in line and target_entry in line:
            capturing = True
            print(line.strip())
            continue
            
        if capturing:
            if "[MANAGEMENT]" in line or "APM decision" in line or "[TRAIL BLOCKED]" in line or "[TRAILING SL]" in line or "Stop hit" in line or "Target hit" in line:
                print(line.strip())
            if "[TRADE OPEN]" in line:
                capturing = False
    print("\n")
