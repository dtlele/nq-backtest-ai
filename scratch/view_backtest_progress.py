import re
from pathlib import Path

log_path = Path("C:/Users/Mauro/.gemini/antigravity/brain/efec7e21-027e-42ce-8b89-1dacb0e2e52c/.system_generated/tasks/task-3247.log")
if log_path.exists():
    with open(log_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    processing_days = re.findall(r'Processing \((.*?)\)\.\.\.', content)
    decisions = re.findall(r'\[DECISION\] (.*?)\n', content)
    errors = re.findall(r'\[ERROR\] (.*?)\n', content)
    consensuses = re.findall(r'\[CONSENSUS\] (.*?)\n', content)
    
    print(f"Total processing days: {len(processing_days)}")
    for day in processing_days:
        print("  - Day:", Path(day).name)
        
    print("\nDecisions count:")
    from collections import Counter
    c = Counter([d.split(" - ")[0] for d in decisions])
    for k, v in c.items():
        print(f"  {k}: {v}")
        
    print(f"\nAndrea Consensuses: {len(consensuses)}")
    for con in consensuses[:10]:
        print("  -", con)
else:
    print("Log file not found")
