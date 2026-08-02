"""Aug-Sep 2025 weekly parallel runner - prod3-yellow complete.
8 processes for 8 weeks of Aug-Sep 2025.

Setup (prod3-yellow):
- Time gate: 9:30-10:00 ET blocked
- Slippage: 0.5pt per side
- Trailing: rr=0.8 trigger, 50% lock 1.5R, 75% lock 2.5R
- R3 absorption, R6, early_drive_detection (from prod2)

Launched in waves of 4 to avoid API burst.
"""
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\Mauro\Documents\nq-backtest-clean")

WEEKS = []
def week_ranges(start_date, end_date):
    from datetime import datetime, timedelta
    d = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    week_num = 0
    while d <= end:
        days_to_friday = 4 - d.weekday()
        if days_to_friday < 0:
            d += timedelta(days=1)
            continue
        fri = d + timedelta(days=days_to_friday)
        if fri > end:
            fri = end
        week_label = f"aug_sep_w{week_num:02d}_{d.strftime('%Y%m%d')}_{fri.strftime('%Y%m%d')}"
        yield (week_label, d.strftime("%Y%m%d"), fri.strftime("%Y%m%d"))
        d = fri + timedelta(days=3)
        week_num += 1

WEEKS = list(week_ranges("20250801", "20250930"))
print(f"Generated {len(WEEKS)} weeks for Aug-Sep 2025:")
for n, s, e in WEEKS:
    print(f"  {n}: {s} -> {e}")

LIVE_TRADES_CSV = ROOT / "output" / "live_trades_aug_sep.csv"
LIVE_TRADES_CSV.parent.mkdir(exist_ok=True)
LIVE_TRADES_CSV.write_text("run,date,time_et,dir,entry,exit,pnl_usd,reason\n", encoding='utf-8')

def launch_week(name, start_date, end_date):
    run_dir = ROOT / "agent_memory_aug_sep" / name
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = ROOT / "output" / f"aug_sep_{name}.log"
    env = os.environ.copy()
    env['AGENT_MEMORY_DIR'] = str(run_dir)
    env['REFLEX_MODEL'] = 'minimax/minimax-m2'
    env['AUDIT_MODEL'] = 'minimax/minimax-m2'
    env['AUDIT_PROMPT_VERSION'] = 'v2'
    env['OPENROUTER_MODEL'] = 'minimax/minimax-m2'
    # prod3-yellow COMPLETE
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
    return name, proc, run_dir, log_file

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
    print(f'AUG-SEP 2025 WEEKLY RUNNER (prod3-yellow) - {len(WEEKS)} processes')
    print('=' * 80)
    processes = []
    for i in range(0, len(WEEKS), 4):
        wave = WEEKS[i:i+4]
        for name, start, end in wave:
            n, p, rd, lf = launch_week(name, start, end)
            processes.append((n, p, rd, lf))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Launched {n} ({start}->{end}) PID={p.pid}")
            time.sleep(2)
        if i + 4 < len(WEEKS):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Wave done. Waiting 30s...")
            time.sleep(30)

    print(f'[{datetime.now().strftime("%H:%M:%S")}] All {len(processes)} processes launched.')
    print(f'Live trades: tail -f {LIVE_TRADES_CSV.relative_to(ROOT)}')
    print()

    seen_keys = set()
    check_interval = 20
    while True:
        all_done = True
        for name, proc, run_dir, log_file in processes:
            if proc.poll() is None:
                all_done = False
                new = tail_new_trades(name, run_dir, seen_keys)
                if new > 0:
                    print(f'[{datetime.now().strftime("%H:%M:%S")}] {name}: +{new} new')
            else:
                tail_new_trades(name, run_dir, seen_keys)
        if all_done:
            break
        time.sleep(check_interval)

    print()
    print('=' * 80)
    print('ALL AUG-SEP PROCESSES COMPLETED')
    print('=' * 80)
    for name, proc, run_dir, log_file in processes:
        trades_file = run_dir / 'trades_log.jsonl'
        n = 0
        if trades_file.exists():
            with open(trades_file, 'r', encoding='utf-8', errors='replace') as f:
                n = sum(1 for _ in f)
        try:
            last_lines = log_file.read_text(encoding='utf-8', errors='replace').strip().split('\n')[-5:]
            pnl_str = next((l for l in last_lines if 'Total P&L' in l), 'N/A')
        except: pnl_str = 'N/A'
        print(f'  {name:35} trades={n:>3}  {pnl_str}')

if __name__ == '__main__':
    main()
