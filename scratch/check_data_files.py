import re
from pathlib import Path

data_dir = Path(r"C:\Users\Mauro\Documents\databento-data")
if data_dir.exists():
    files = sorted(list(data_dir.glob("*.csv")))
    print(f"Total files: {len(files)}")
    may_june_files = []
    for f in files:
        match = re.search(r'(\d{8})', f.name)
        if match:
            date_str = match.group(1)
            if "20250501" <= date_str <= "20250630":
                may_june_files.append((date_str, f.name))
    print(f"May and June 2025 files count: {len(may_june_files)}")
    for date_str, name in may_june_files:
        print(f"  {date_str}: {name}")
else:
    print("Data directory does not exist.")
