import json
from pathlib import Path

def main():
    # 1. Clean reasoning_log.jsonl
    log_path = Path('agent_memory/reasoning_log.jsonl')
    cleaned_lines = []
    removed_count = 0
    if log_path.exists():
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get('date') == '2025-07-17':
                    removed_count += 1
                else:
                    cleaned_lines.append(line)
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.writelines(cleaned_lines)
        print(f"Removed {removed_count} lines for 2025-07-17 from reasoning_log.jsonl")
    else:
        print("reasoning_log.jsonl not found")

    # 2. Update session_state.json
    session_path = Path('agent_memory/session_state.json')
    state = {
        "date": "2025-07-16",
        "ib_high": None,
        "ib_low": None,
        "poc": None,
        "day_type": "unknown",
        "open_trade": None,
        "equity": 50860.10,
        "daily_pnl_usd": 0.0,
        "trade_count_today": 0,
        "session_stopped": False
    }
    with open(session_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)
    print(f"Updated session_state.json to: {state}")

if __name__ == '__main__':
    main()
