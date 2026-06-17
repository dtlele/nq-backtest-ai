from pathlib import Path
import re

data_dir = Path("C:/Users/Mauro/Documents/databento-data")
files = sorted(list(data_dir.glob("*.trades.csv")))

dates = []
for f in files:
    match = re.search(r'(\d{8})', f.name)
    if match:
        dates.append(match.group(1))

print(f"Total files: {len(files)}")
print(f"Dates available (first 30): {dates[:30]}")

# Find index of 20250430
if "20250430" in dates:
    idx = dates.index("20250430")
    print(f"20250430 is at index {idx}")
    print(f"Next 14 days start from index {idx+1}: {dates[idx+1:idx+15]}")
else:
    print("20250430 not found in dates")
