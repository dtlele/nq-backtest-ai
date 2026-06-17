import json

def main():
    with open('agent_memory/reasoning_log.jsonl', 'r') as f:
        lines = [json.loads(line) for line in f if line.strip()]
    
    july_lines = [l for l in lines if l.get('date', '').startswith('2025-07')]
    print(f"Total July reasoning lines: {len(july_lines)}")
    
    # Group by date and find max time or bars processed
    from collections import defaultdict
    by_date = defaultdict(list)
    for l in july_lines:
        by_date[l.get('date')].append(l)
        
    for date in sorted(by_date.keys()):
        day_lines = by_date[date]
        print(f"Date: {date} | Rows: {len(day_lines)} | First bar: {day_lines[0].get('bar_time_et')} | Last bar: {day_lines[-1].get('bar_time_et')}")

if __name__ == '__main__':
    main()
