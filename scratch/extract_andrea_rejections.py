from pathlib import Path

log_path = Path("C:/Users/Mauro/.gemini/antigravity/brain/efec7e21-027e-42ce-8b89-1dacb0e2e52c/.system_generated/tasks/task-3247.log")
if log_path.exists():
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Let's search for "REJECTED by Andrea" and show the lines preceding it to see Andrea's response and reasoning!
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        if "REJECTED by Andrea" in line:
            print(f"=== REJECTION AT LINE {idx+1} ===")
            start = max(0, idx - 15)
            end = min(len(lines), idx + 2)
            for j in range(start, end):
                print(f"{j+1}: {lines[j]}")
            print("="*60)
else:
    print("Log file not found")
