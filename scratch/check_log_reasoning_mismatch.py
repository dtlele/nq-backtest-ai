import json

def check_mismatches():
    reasonings = {}
    with open('agent_memory/reasoning_log.jsonl', 'r') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            if data.get('decision') == 'trade' or data.get('trade_direction') is not None:
                # Store by date and bar_time_utc or entry_time
                t_utc = data.get('bar_time_utc')
                if t_utc:
                    reasonings[t_utc] = data
                else:
                    # try date + time
                    pass

    print(f"Loaded {len(reasonings)} trade decisions from reasoning_log.")
    
    mismatches = 0
    with open('agent_memory/trades_log.jsonl', 'r') as f:
        for line in f:
            if not line.strip(): continue
            t = json.loads(line)
            entry_time = t.get('entry_time') # e.g. "2025-06-02T13:47:00+00:00"
            if not entry_time: continue
            
            # Match with reasoning log using entry_time
            matched = reasonings.get(entry_time)
            if matched:
                r_entry = matched.get('trade_entry')
                t_entry = t.get('entry')
                if r_entry and abs(r_entry - t_entry) > 0.1:
                    print(f"Mismatch on {t.get('date')} {entry_time}:")
                    print(f"  Reasoning Log entry: {r_entry}")
                    print(f"  Trades Log entry:    {t_entry}")
                    print(f"  Diff:                {abs(r_entry - t_entry):.2f} pts")
                    mismatches += 1
            else:
                # Try finding by date and close entry time
                pass
                
    print(f"Total Mismatches found: {mismatches}")

if __name__ == '__main__':
    check_mismatches()
