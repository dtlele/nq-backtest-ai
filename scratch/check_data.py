import os
from pathlib import Path

data_dir = Path(r"C:\Users\Mauro\Documents\databento-data")
if data_dir.exists():
    files = list(data_dir.glob("*"))
    print(f"Total files: {len(files)}")
    for f in sorted(files)[:20]:
        print(f"  {f.name} ({f.stat().st_size / 1024 / 1024:.2f} MB)")
else:
    print("Data directory not found")
