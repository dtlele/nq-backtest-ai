import json
from pathlib import Path
from datetime import datetime, timezone

MEMORY_DIR = Path(__file__).parent.parent / 'agent_memory'
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
SESSION_FILE  = MEMORY_DIR / 'session_state.json'
PATTERN_FILE  = MEMORY_DIR / 'pattern_memory.json'
LOG_FILE      = MEMORY_DIR / 'reasoning_log.jsonl'

def load_session() -> dict:
    with open(SESSION_FILE, encoding='utf-8') as f:
        return json.load(f)

def save_session(state: dict) -> None:
    with open(SESSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def reset_session(date_str: str) -> dict:
    state = {
        'date': date_str,
        'ib_high': None, 'ib_low': None, 'poc': None,
        'day_type': 'unknown',
        'open_trade': None,
        'daily_pnl_usd': 0.0,
        'trade_count_today': 0,
        'session_stopped': False,
    }
    save_session(state)
    return state

def log_reasoning(entry: dict) -> None:
    """Append one reasoning entry to the JSONL log."""
    entry['logged_at'] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def update_pattern_memory(closed_trade) -> None:
    """Update cross-session pattern stats after closing a trade."""
    with open(PATTERN_FILE, encoding='utf-8') as f:
        pm = json.load(f)
    pm['total_trades'] += 1
    if closed_trade.pnl_usd > 0:
        pm['wins'] += 1
    else:
        pm['losses'] += 1
    pm['win_rate'] = pm['wins'] / pm['total_trades'] if pm['total_trades'] else 0.0
    # Rolling avg R — use abs() so risk_ticks is always positive for both sides
    risk_ticks = abs(closed_trade.entry - closed_trade.stop) / 0.25
    r = closed_trade.pnl_ticks / risk_ticks if risk_ticks > 0 else 0.0
    pm['avg_r'] = (pm['avg_r'] * (pm['total_trades'] - 1) + r) / pm['total_trades']
    with open(PATTERN_FILE, 'w', encoding='utf-8') as f:
        json.dump(pm, f, indent=2)
