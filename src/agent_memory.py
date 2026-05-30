import json
from pathlib import Path
from datetime import datetime, timezone

MEMORY_DIR = Path(__file__).parent.parent / 'agent_memory'
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
SESSION_FILE  = MEMORY_DIR / 'session_state.json'
PATTERN_FILE  = MEMORY_DIR / 'pattern_memory.json'
LOG_FILE      = MEMORY_DIR / 'reasoning_log.jsonl'
HUMAN_FILE    = MEMORY_DIR / 'human_decisions.jsonl'
TRADES_FILE   = MEMORY_DIR / 'trades_log.jsonl'

def load_session() -> dict:
    with open(SESSION_FILE, encoding='utf-8') as f:
        return json.load(f)

def save_session(state: dict) -> None:
    with open(SESSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def reset_session(date_str: str) -> dict:
    try:
        with open(SESSION_FILE, encoding='utf-8') as f:
            old_state = json.load(f)
            current_equity = old_state.get('equity', 50000.0)
    except FileNotFoundError:
        current_equity = 50000.0

    state = {
        'date': date_str,
        'ib_high': None, 'ib_low': None, 'poc': None,
        'day_type': 'unknown',
        'open_trade': None,
        'equity': current_equity,      # Preserve compounding equity
        'daily_pnl_usd': 0.0,
        'trade_count_today': 0,
        'session_stopped': False,
    }
    save_session(state)
    return state

def force_reset_equity(starting_equity: float = 50000.0) -> None:
    try:
        with open(SESSION_FILE, encoding='utf-8') as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {}
    state['equity'] = starting_equity
    save_session(state)

def log_reasoning(entry: dict) -> None:
    """Append one reasoning entry to the JSONL log."""
    entry['logged_at'] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def log_trade_result(closed_trade) -> None:
    """Append one closed trade to the trades JSONL log."""
    date_str = closed_trade.entry_time.strftime('%Y-%m-%d')
    entry_iso = closed_trade.entry_time.isoformat()
    
    # IDEMPOTENCY CHECK: Prevent duplicates (unless BACKTEST_FORCE is True)
    import os
    if not os.getenv('BACKTEST_FORCE') == 'true':
        if is_trade_already_logged(date_str, entry_iso):
            return

    entry = {
        'date': date_str,
        'entry_time': entry_iso,
        'exit_time': closed_trade.exit_time.isoformat(),
        'direction': closed_trade.direction,
        'entry': closed_trade.entry,
        'stop': closed_trade.stop,
        'target': closed_trade.target,
        'exit_price': closed_trade.exit_price,
        'exit_reason': closed_trade.exit_reason,
        'pnl_ticks': closed_trade.pnl_ticks,
        'pnl_usd': closed_trade.pnl_usd,
        'r_ratio': closed_trade.r_ratio,
        'setup_type': closed_trade.setup_type,
        'final_confidence': closed_trade.final_confidence,
        'fabio_reasoning': closed_trade.fabio_reasoning,
        'andrea_reasoning': closed_trade.andrea_reasoning,
        'contracts': closed_trade.contracts,
        'news_flag': getattr(closed_trade, "news_flag", "none"),
        'logged_at': datetime.now(timezone.utc).isoformat(),
    }
    with open(TRADES_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def get_already_processed_candidates() -> set:
    """Return a set of (date, bar_time_et) that have already been processed or answered by human."""
    processed = set()
    
    # 1. Check reasoning log (includes prefiltered and light skips)
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        # We use date + bar_time_et for identification
                        processed.add((data.get('date'), data.get('bar_time_et')))
        except Exception:
            pass

    # 2. Check human decisions (to skip re-asking for already answered but not yet traded candles)
    if HUMAN_FILE.exists():
        try:
            with open(HUMAN_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        # human_decisions.jsonl entries: {"key": "...", "decision": {"reasoning": "... bar_time_et: 10:45 ...", ...}}
                        # Wait, human_decisions.jsonl only has the key and the decision.
                        # It's better to log a reasoning entry for every human decision too.
                        # I will modify llm_client to log reasoning when human replies.
                        pass
        except Exception:
            pass
            
    return processed

def is_trade_already_logged(date: str, entry_time_iso: str) -> bool:
    """Check if a trade with this date and entry time already exists."""
    if not TRADES_FILE.exists():
        return False
    try:
        with open(TRADES_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if data.get('date') == date and data.get('entry_time') == entry_time_iso:
                        return True
    except Exception:
        pass
    return False


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
