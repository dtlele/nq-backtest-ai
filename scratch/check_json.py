import json
from pathlib import Path

json_path = Path("dashboard/public/data/2025-04-30.json")
if json_path.exists():
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        print("Keys in JSON:", list(data.keys()))
        if "dev_va" in data:
            print(f"dev_va length: {len(data['dev_va'])}")
            if len(data['dev_va']) > 0:
                print("First dev_va entry:", data['dev_va'][0])
        else:
            print("dev_va is NOT in JSON!")
        
        if "vp" in data:
            print("vp values:", data["vp"])
        else:
            print("vp is NOT in JSON!")
            
        if "m1_ny" in data:
            print(f"m1_ny length: {len(data['m1_ny'])}")
            if len(data['m1_ny']) > 0:
                print("First m1_ny entry:", data['m1_ny'][0])
else:
    print("JSON file does not exist")
