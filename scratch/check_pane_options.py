with open("dashboard/node_modules/klinecharts/dist/index.d.ts", "r") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "PaneOptions" in line:
        print(f"Line {i+1}: {line.strip()}")
