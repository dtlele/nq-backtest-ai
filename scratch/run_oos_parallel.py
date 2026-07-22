import subprocess
import sys
import os
import time
from pathlib import Path
from src.oos_exporter import export_trades_to_csv

def run_oos():
    # Define tasks: (task_name, start_date, days)
    tasks = [
        # January 2025 (OOS)
        ("jan_w1", "20250106", 5),
        ("jan_w2", "20250113", 5),
        ("jan_w3", "20250120", 5),
        ("jan_w4", "20250127", 5),
        
        # February 2025 (Baseline)
        ("feb_w1", "20250203", 5),
        ("feb_w2", "20250210", 5),
        ("feb_w3", "20250217", 5),
        ("feb_w4", "20250224", 5),
        
        # March 2025 (OOS)
        ("mar_w1", "20250303", 5),
        ("mar_w2", "20250310", 5),
        ("mar_w3", "20250317", 5),
        ("mar_w4", "20250324", 5),
    ]
    
    processes = []
    print(f"[START] Launching {len(tasks)} parallel backtest processes for Jan, Feb, Mar 2025...")
    
    os.makedirs("output/logs", exist_ok=True)
    
    for task_name, start_date, days in tasks:
        mem_dir = f"agent_memory/{task_name}"
        os.makedirs(mem_dir, exist_ok=True)
        
        env = os.environ.copy()
        env['AGENT_MEMORY_DIR'] = mem_dir
        
        cmd = [
            sys.executable, "run_backtest.py",
            "--start-date", start_date,
            "--days", str(days),
            "--fabio-only",
            "--quiet"
        ]
        
        log_file = open(f"output/logs/{task_name}.log", "w", encoding="utf-8")
        p = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=log_file)
        processes.append((p, task_name, log_file, start_date))
        print(f"  [PARALLEL] Started {task_name} (Start: {start_date}, Days: {days})")
        time.sleep(1.5)
        
    print("\n[WAITING] All processes launched. Waiting for completion...")
    
    for p, task_name, log_file, _ in processes:
        p.wait()
        log_file.close()
        print(f"  [COMPLETED] {task_name} (Code: {p.returncode})")
        
    print("\n[EXPORT] Aggregating results and exporting OOS CSVs...")
    
    # Group outputs by month
    month_groups = {
        '2025-01': [t for t in tasks if t[0].startswith('jan')],
        '2025-02': [t for t in tasks if t[0].startswith('feb')],
        '2025-03': [t for t in tasks if t[0].startswith('mar')],
    }
    
    for m_name, m_tasks in month_groups.items():
        month_trades = []
        for t_name, _, _ in m_tasks:
            t_file = f"agent_memory/{t_name}/trades_log.jsonl"
            if os.path.exists(t_file):
                import json
                with open(t_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                month_trades.append(json.loads(line))
                            except: pass
                            
        if month_trades:
            csv_path = f"output/trades_{m_name}.csv"
            export_trades_to_csv(month_trades, csv_path)
            print(f"  [EXPORTED] {m_name}: {len(month_trades)} trades saved to {csv_path}")
        else:
            print(f"  [WARN] No trades generated for {m_name}")
            
    print("\n[AGGREGATION] Merging all logs into main agent_memory for dashboard...")
    os.makedirs("agent_memory", exist_ok=True)
    
    # Merge trades and reasoning
    all_reasoning = []
    all_trades = []
    
    for t_name, _, _ in tasks:
        r_file = f"agent_memory/{t_name}/reasoning_log.jsonl"
        t_file = f"agent_memory/{t_name}/trades_log.jsonl"
        
        if os.path.exists(r_file):
            with open(r_file, "r", encoding="utf-8") as f:
                all_reasoning.extend(f.readlines())
        if os.path.exists(t_file):
            with open(t_file, "r", encoding="utf-8") as f:
                all_trades.extend(f.readlines())
                
    # Write aggregated logs to main directory
    with open("agent_memory/reasoning_log.jsonl", "w", encoding="utf-8") as f:
        f.writelines(all_reasoning)
    with open("agent_memory/trades_log.jsonl", "w", encoding="utf-8") as f:
        f.writelines(all_trades)
        
    print(f"  [MERGED] {len(all_reasoning)} reasoning steps and {len(all_trades)} trades into agent_memory/ for dashboard visualization.")

if __name__ == "__main__":
    run_oos()
