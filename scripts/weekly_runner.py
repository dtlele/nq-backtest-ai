"""Weekly parallel runner - 1 process per week, 12 weeks (3 months).

Each week is a separate process with isolated state.
Auto-kills on completion.
"""
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\Mauro\Documents\nq-backtest-clean")

# Generate weeks from Apr 1 to Jun 30, 2025
WEEKS = []
def week_ranges(start_date, end_date):
    """Generate (start, end) pairs for each week Mon-Fri."""
    from datetime import datetime, timedelta
    d = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    week_num = 0
    while d <= end:
        # Find Friday of this week
        days_to_friday = 4 - d.weekday()
        if days_to_friday < 0:
            d += timedelta(days=1)
            continue
        fri = d + timedelta(days=days_to_friday)
        if fri > end:
            fri = end
        week_label = f"{d.strftime('%Y%m%d')}_{fri.strftime('%Y%m%d')}"
        yield (f"wk{week_num:02d}", d.strftime("%Y%m%d"), fri.strftime("%Y%m%d"), week_label)
        d = fri + timedelta(days=3)  # skip to next Monday
        week_num += 1

WEEKS = list(week_ranges("20250401", "20250630"))
print(f"Generated {len(WEEKS)} weeks:")
for n, s, e, l in WEEKS:
    print(f"  {l}: {s} -> {e}")

LIVE_TRADES_CSV = ROOT / "output" / "live_trades.csv"
LIVE_TRADES_CSV.parent.mkdir(exist_ok=True)
# Re-initialize clean
LIVE_TRADES_CSV.write_text("run,date,time_et,dir,entry,exit,pnl_usd,reason\n", encoding='utf-8')

def launch_week(name, start_date, end_date, label):
    run_dir = ROOT / "agent_memory_weekly" / name
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = ROOT / "output" / f"weekly_{name}.log"
    env = os.environ.copy()
    env['AGENT_MEMORY_DIR'] = str(run_dir)
    env['REFLEX_MODEL'] = 'minimax/minimax-m2'
    env['AUDIT_MODEL'] = 'minimax/minimax-m2'
    env['AUDIT_PROMPT_VERSION'] = 'v2'
    env['OPENROUTER_MODEL'] = 'minimax/minimax-m2'
    env['TRAIL_TRIGGER_RR'] = '0.8'
    env['TRAIL_LOCK_50_RR'] = '1.5'
    env['TRAIL_LOCK_75_RR'] = '2.5'
    env['BACKTEST_SLIPPAGE_PTS'] = '0.5'
    env['PYTHONUNBUFFERED'] = '1'
    proc = subprocess.Popen(
        [sys.executable, "run_backtest.py",
         "--start-date", start_date, "--end-date", end_date,
         "--fabio-only", "--quiet", "--reset-equity"],
        cwd=str(ROOT), env=env,
        stdout=open(log_file, 'w', encoding='utf-8'),
        stderr=subprocess.STDOUT,
    )
    return name, proc, run_dir, log_file, label

def tail_new_trades(run_name, run_dir, seen_keys):
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
    print(f'WEEKLY PARALLEL BACKTEST - {len(WEEKS)} processes')
    print('=' * 80)
    processes = []
    # Launch in waves of 4 to avoid API burst
    WAVE_SIZE = 4
    for i in range(0, len(WEEKS), WAVE_SIZE):
        wave = WEEKS[i:i+WAVE_SIZE]
        for name, start, end, label in wave:
            n, p, rd, lf, lab = launch_week(name, start, end, label)
            processes.append((n, p, rd, lf, lab))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Launched {lab} PID={p.pid}")
            time.sleep(2)
        # Wait for wave to make progress before next
        if i + WAVE_SIZE < len(WEEKS):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting 30s before next wave...")
            time.sleep(30)

    print()
    print(f'[{datetime.now().strftime("%H:%M:%S")}] All {len(processes)} weekly processes launched.')
    print(f'Live trades: tail -f output/live_trades.csv')
    print()

    seen_keys = set()
    check_interval = 20
    while True:
        all_done = True
        for name, proc, run_dir, log_file, label in processes:
            poll = proc.poll()
            if poll is None:
                all_done = False
                # Check new trades
                new_count = tail_new_trades(name, run_dir, seen_keys)
                if new_count > 0:
                    print(f'[{datetime.now().strftime("%H:%M:%S")}] {label}: +{new_count} new trades')
            else:
                # Final tail
                tail_new_trades(name, run_dir, seen_keys)
                # Check if already announced
        if all_done:
            break
        time.sleep(check_interval)

    # Final summary
    print()
    print('=' * 80)
    print('ALL WEEKLY PROCESSES COMPLETED')
    print('=' * 80)
    for name, proc, run_dir, log_file, label in processes:
        trades_file = run_dir / 'trades_log.jsonl'
        n = 0
        if trades_file.exists():
            with open(trades_file, 'r', encoding='utf-8', errors='replace') as f:
                n = sum(1 for _ in f)
        try:
            last_lines = log_file.read_text(encoding='utf-8', errors='replace').strip().split('\n')[-5:]
            pnl_str = next((l for l in last_lines if 'Total P&L' in l), 'N/A')
        except: pnl_str = 'N/A'
        print(f'  {label:35} trades={n:>3}  {pnl_str}')

if __name__ == '__main__':
    main()
