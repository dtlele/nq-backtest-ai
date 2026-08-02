"""Parallel backtest runner - launches 4 backtest processes in parallel.

Each process:
- Has its own AGENT_MEMORY_DIR (session_state, trades_log, reasoning_log)
- Has its own output log file
- Runs a different time range
- Reports trades in real-time to a shared CSV

Usage:
    python scripts/parallel_runner.py
"""
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\Mauro\Documents\nq-backtest-clean")
RUNS = [
    # (name, start_date, end_date, run_label)
    ("apr_w1", "20250401", "20250413", "Aprile W1-2"),
    ("apr_w2", "20250414", "20250427", "Aprile W3-4"),
    ("may_w1", "20250428", "20250518", "Maggio W1-4"),
    ("may_w2", "20250519", "20250615", "Maggio W5 - Giugno W2"),
]

LIVE_TRADES_CSV = ROOT / "output" / "live_trades.csv"
LIVE_TRADES_CSV.parent.mkdir(exist_ok=True)
# Initialize live_trades.csv with header
if not LIVE_TRADES_CSV.exists():
    LIVE_TRADES_CSV.write_text("run,date,time_et,dir,entry,exit,pnl_usd,reason\n", encoding='utf-8')

def launch_run(name, start_date, end_date, label):
    """Launch a backtest process in parallel, with isolated state."""
    run_dir = ROOT / "agent_memory_runs" / name
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = ROOT / "output" / f"parallel_{name}.log"

    env = os.environ.copy()
    env['AGENT_MEMORY_DIR'] = str(run_dir)
    env['REFLEX_MODEL'] = 'minimax/minimax-m2'
    env['AUDIT_MODEL'] = 'minimax/minimax-m2'
    env['AUDIT_PROMPT_VERSION'] = 'v2'
    env['OPENROUTER_MODEL'] = 'minimax/minimax-m2'
    # prod2-yellow settings (trailing + time gate + slippage)
    env['TRAIL_TRIGGER_RR'] = '0.8'
    env['TRAIL_LOCK_50_RR'] = '1.5'
    env['TRAIL_LOCK_75_RR'] = '2.5'
    env['BACKTEST_SLIPPAGE_PTS'] = '0.5'
    env['PYTHONUNBUFFERED'] = '1'

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Launching {label} ({start_date} -> {end_date}) as PID ...")
    proc = subprocess.Popen(
        [sys.executable, "run_backtest.py",
         "--start-date", start_date,
         "--end-date", end_date,
         "--fabio-only",
         "--quiet",
         "--reset-equity"],
        cwd=str(ROOT),
        env=env,
        stdout=open(log_file, 'w', encoding='utf-8'),
        stderr=subprocess.STDOUT,
    )
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {label} launched as PID {proc.pid}, log -> {log_file.name}")
    return name, proc, run_dir, log_file

def tail_trades(run_name, run_dir, seen_keys):
    """Read trades from this run's log and append to live_trades.csv.
    DEDUP via in-memory seen_keys set (shared across all runs).
    Returns count of NEW trades appended.
    """
    trades_file = run_dir / 'trades_log.jsonl'
    if not trades_file.exists():
        return 0
    count = 0
    try:
        with open(trades_file, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    import json
                    t = json.loads(line)
                    et = t.get('entry_time','')
                    time_et = et[11:16] if 'T' in et else ''
                    # dedup key: (run, date, time, dir, entry)
                    key = (run_name, t.get('date',''), time_et, t.get('direction',''), round(float(t.get('entry',0) or 0), 2))
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    row = f"{run_name},{t.get('date','')},{time_et},{t.get('direction','')},{t.get('entry',0):.2f},{t.get('exit_price',0):.2f},{t.get('pnl_usd',0):.2f},{t.get('exit_reason','')}\n"
                    with open(LIVE_TRADES_CSV, 'a', encoding='utf-8') as out:
                        out.write(row)
                    count += 1
                except: pass
    except: pass
    return count

def main():
    print('=' * 80)
    print(f'PARALLEL BACKTEST RUNNER - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print('=' * 80)
    print(f'Launching {len(RUNS)} parallel backtest processes:')
    for n, s, e, l in RUNS:
        print(f'  - {l:25} {s} -> {e}  (run_id={n})')
    print()

    processes = []
    for name, start, end, label in RUNS:
        n, p, rd, lf = launch_run(name, start, end, label)
        processes.append((n, p, rd, lf, label))
        time.sleep(3)  # Stagger launch to avoid simultaneous API burst

    print()
    print(f'[{datetime.now().strftime("%H:%M:%S")}] All {len(processes)} processes launched.')
    print(f'Live trades: tail -f {LIVE_TRADES_CSV.relative_to(ROOT)}')
    print()

    # Monitor loop with global dedup
    seen_trade_counts = {n: 0 for n, _, _, _, _ in processes}
    seen_keys = set()  # global dedup across all runs and ticks
    check_interval = 30  # seconds
    while True:
        all_done = True
        for name, proc, run_dir, log_file, label in processes:
            poll = proc.poll()
            if poll is None:
                all_done = False
                # Tail trades
                trades_file = run_dir / 'trades_log.jsonl'
                current_count = 0
                if trades_file.exists():
                    with open(trades_file, 'r', encoding='utf-8', errors='replace') as f:
                        current_count = sum(1 for _ in f)
                delta = current_count - seen_trade_counts[name]
                if delta > 0:
                    appended = tail_trades(name, run_dir, seen_keys)
                    seen_trade_counts[name] = current_count
                    print(f'[{datetime.now().strftime("%H:%M:%S")}] {label}: +{appended} new (total in log: {current_count})')
            else:
                if seen_trade_counts[name] == 0 or current_count_unknown(name):
                    # Final tail
                    trades_file = run_dir / 'trades_log.jsonl'
                    if trades_file.exists():
                        with open(trades_file, 'r', encoding='utf-8', errors='replace') as f:
                            current_count = sum(1 for _ in f)
                    else:
                        current_count = 0
                    if current_count > seen_trade_counts[name]:
                        tail_trades(name, run_dir, seen_keys)
                        seen_trade_counts[name] = current_count
                    print(f'[{datetime.now().strftime("%H:%M:%S")}] {label}: FINISHED (exit={poll}, total_trades={seen_trade_counts[name]})')

        if all_done:
            break
        time.sleep(check_interval)

    # Final summary
    print()
    print('=' * 80)
    print('ALL PROCESSES COMPLETED')
    print('=' * 80)
    for name, proc, run_dir, log_file, label in processes:
        n = seen_trade_counts[name]
        # Get last line of log for PnL
        try:
            last_lines = log_file.read_text(encoding='utf-8', errors='replace').strip().split('\n')[-5:]
            pnl_str = next((l for l in last_lines if 'Total P&L' in l), 'N/A')
        except: pnl_str = 'N/A'
        print(f'  {label:25} trades={n:>3}  {pnl_str}')

    print(f'\nLive trades CSV: {LIVE_TRADES_CSV.relative_to(ROOT)}')
    print('To see real-time: tail -f output/live_trades.csv')

def current_count_unknown(name):
    return False  # placeholder

if __name__ == '__main__':
    main()
