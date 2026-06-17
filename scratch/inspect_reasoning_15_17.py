import json

def main():
    rows = []
    with open('agent_memory/reasoning_log.jsonl', 'r') as f:
        for line in f:
            if not line.strip():
                continue
            t = json.loads(line)
            dt = t.get('date')
            if dt in ['2025-07-15', '2025-07-16', '2025-07-17']:
                rows.append(t)
    
    print(f"Total rows for July 15-17 in reasoning_log: {len(rows)}")
    for r in rows:
        print(f"Date: {r.get('date')} | Day Type: {r.get('day_type')} | Time: {r.get('time')} | Action: {r.get('action')} | Decision: {r.get('decision')}")

if __name__ == '__main__':
    main()
