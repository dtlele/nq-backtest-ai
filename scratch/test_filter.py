import os
from pathlib import Path

files = [
    r"C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250730.trades.csv",
    r"C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250903.trades.csv",
    r"C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20251201.trades.csv"
]

start_date = "20250903"

def test_split(f):
    name = Path(f).name
    parts = name.split('-')
    print(f"File: {name} | Parts: {parts}")
    if len(parts) < 3:
        return None
    date_part = parts[2].split('.')[0]
    return date_part

print(f"Testing start_date: {start_date}")
for f in files:
    d = test_split(f)
    print(f"  Extracted: {d} | Result: {d >= start_date if d else 'FAIL'}")
