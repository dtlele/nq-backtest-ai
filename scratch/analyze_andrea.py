from pathlib import Path
import re

log_path = Path("C:/Users/Mauro/.gemini/antigravity/brain/efec7e21-027e-42ce-8b89-1dacb0e2e52c/.system_generated/tasks/task-3247.log")
if log_path.exists():
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    # Let's search for "Andrea" and the surrounding lines (10 lines before, 20 lines after)
    for idx, line in enumerate(lines):
        if "Requesting confirmation from Andrea..." in line:
            print(f"=== FOUND AT LINE {idx+1} ===")
            start = max(0, idx - 8)
            end = min(len(lines), idx + 25)
            for j in range(start, end):
                print(f"{j+1}: {lines[j].strip()}")
            print("="*60)
else:
    print("Log file not found")
