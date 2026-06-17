import json

def main():
    dates = set()
    last_dates = []
    with open('agent_memory/reasoning_log.jsonl', 'r') as f:
        for line in f:
            if not line.strip():
                continue
            t = json.loads(line)
            dt = t.get('date')
            if dt and dt.startswith('2025-07'):
                dates.add(dt)
                last_dates.append(dt)
    
    print(f"Processed July dates in reasoning_log: {sorted(list(dates))}")
    if last_dates:
        print(f"Last 10 processed July rows date: {last_dates[-10:]}")

if __name__ == '__main__':
    main()
