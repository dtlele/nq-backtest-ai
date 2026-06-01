import csv

filename = r'C:\Users\Mauro\Documents\databento-data\glbx-mdp3-20250403.trades.csv'
entry_time = '2025-04-03T14:57:00'
target = 18744.0
stop = 18816.75

print(f"Tracing trade from {entry_time}...")
with open(filename, 'r') as f:
    reader = csv.reader(f)
    header = next(reader)
    
    started = False
    for row in reader:
        ts = row[1]
        if not started:
            if ts >= entry_time:
                started = True
                print(f"Started tracking at {ts}")
            else:
                continue
                
        price = float(row[8])
        if price <= target:
            print(f"[{ts}] TARGET HIT! Price reached {price}")
            break
        elif price >= stop:
            print(f"[{ts}] STOP LOSS HIT! Price reached {price}")
            break
