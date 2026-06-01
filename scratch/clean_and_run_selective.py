import json
from pathlib import Path
import subprocess

BASE_DIR = Path(r"c:\Users\Mauro\Documents\nq-backtest")
MEM_DIR = BASE_DIR / "agent_memory"
TRADES_FILE = MEM_DIR / "trades_log.jsonl"
SESSION_FILE = MEM_DIR / "session_state.json"

def clean_trades(dates_to_remove):
    print("--- Cleaning old trades for dates:", dates_to_remove)
    if not TRADES_FILE.exists():
        print("Trades file does not exist. Nothing to clean.")
        return

    cleaned_lines = []
    removed_count = 0
    with open(TRADES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    if data.get('date') in dates_to_remove:
                        removed_count += 1
                    else:
                        cleaned_lines.append(line)
                except Exception as e:
                    cleaned_lines.append(line)

    with open(TRADES_FILE, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)
    print(f"Removed {removed_count} old trade records from trades_log.jsonl.")

def reset_equity(value=100000.0):
    print(f"--- Resetting session equity to ${value}...")
    if not SESSION_FILE.exists():
        print("Session file does not exist. Resetting default session state.")
        state = {
            "date": "2025-01-02",
            "ib_high": None, "ib_low": None, "poc": None,
            "day_type": "unknown",
            "open_trade": None,
            "equity": value,
            "daily_pnl_usd": 0.0,
            "trade_count_today": 0,
            "session_stopped": False
        }
    else:
        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
        state['equity'] = value
        state['daily_pnl_usd'] = 0.0
        state['trade_count_today'] = 0
        state['open_trade'] = None
        state['session_stopped'] = False

    with open(SESSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)
    print(f"Session equity reset successfully to ${value}.")

def run_day_backtest(date_str):
    print(f"\n==========================================")
    print(f"RUNNING BACKTEST FOR DAY: {date_str}")
    print(f"==========================================")
    
    # We must run it using python src/backtest_runner.py --start_date YYYYMMDD --end_date YYYYMMDD
    # We strip hyphens from YYYY-MM-DD to get YYYYMMDD
    date_arg = date_str.replace("-", "")
    
    # Run in subprocess to ensure fresh environment
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE_DIR)
    
    cmd = [
        "python",
        "src/backtest_runner.py",
        "--start_date", date_arg,
        "--end_date", date_arg
    ]
    
    result = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True, encoding='utf-8', env=env)
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
        
    print(f"Finished backtest run for {date_str}.")

def collect_new_trades(dates):
    print("\n--- Summary of executed trades for:", dates)
    if not TRADES_FILE.exists():
        print("No trades_log.jsonl found.")
        return

    trades_by_date = {d: [] for d in dates}
    with open(TRADES_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    t_date = data.get('date')
                    if t_date in trades_by_date:
                        trades_by_date[t_date].append(data)
                except Exception:
                    pass

    for date, list_trades in trades_by_date.items():
        print(f"\nDate: {date} - Total Trades: {len(list_trades)}")
        if not list_trades:
            print("  No trades executed.")
            continue
            
        pnl_sum = 0.0
        for i, t in enumerate(list_trades, 1):
            pnl = t.get('pnl_usd', 0.0)
            pnl_sum += pnl
            print(f"  Trade #{i}: Time={t.get('entry_time')} | Dir={t.get('direction')} | Entry={t.get('entry')} | Stop={t.get('stop')} | Target={t.get('target')} | Exit={t.get('exit_price')} | Reason={t.get('exit_reason')} | Contracts={t.get('contracts')} | Conf={t.get('final_confidence')}% | P&L=${pnl:.2f}")
        print(f"  --> Total Day P&L: ${pnl_sum:.2f}")

if __name__ == "__main__":
    dates = ["2025-03-10", "2025-03-27"]
    clean_trades(dates)
    
    # Run first date
    reset_equity(100000.0)
    run_day_backtest("2025-03-10")
    
    # Run second date (also starting clean at $100k for absolute isolated comparison)
    reset_equity(100000.0)
    run_day_backtest("2025-03-27")
    
    # Print results
    collect_new_trades(dates)
