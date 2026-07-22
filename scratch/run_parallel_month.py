import subprocess
import sys
import os
import time

def run_parallel():
    weeks = [
        ("week1", "20250203", 5),
        ("week2", "20250210", 5),
        ("week3", "20250217", 5),
        ("week4", "20250224", 5),
    ]
    
    processes = []
    
    for week_dir, start_date, days in weeks:
        # Create env with specific AGENT_MEMORY_DIR
        env = os.environ.copy()
        env['AGENT_MEMORY_DIR'] = f"agent_memory/{week_dir}"
        
        # Ensure dir exists
        os.makedirs(f"agent_memory/{week_dir}", exist_ok=True)
        
        cmd = [
            sys.executable, "run_backtest.py",
            "--start-date", start_date,
            "--days", str(days),
            "--fabio-only",
            "--quiet"
        ]
        
        print(f"Avvio {week_dir} da {start_date} per {days} giorni...")
        
        # Open log file for stdout/stderr
        log_file = open(f"output/{week_dir}.log", "w", encoding="utf-8")
        
        p = subprocess.Popen(cmd, env=env, stdout=log_file, stderr=log_file)
        processes.append((p, week_dir, log_file))
        
        # Small sleep to prevent databento concurrent disk read lock issues
        time.sleep(2)
        
    print("Tutti i 4 processi avviati. In attesa del completamento...")
    
    for p, week_dir, log_file in processes:
        p.wait()
        log_file.close()
        print(f"[{week_dir}] Completato con codice {p.returncode}")
        
    print("Backtest parallelo completato. Procedo col merge dei log in agent_memory principale...")
    
    # Merge logs
    os.makedirs("agent_memory", exist_ok=True)
    with open("agent_memory/trades_log.jsonl", "w", encoding="utf-8") as out_trades, \
         open("agent_memory/reasoning_log.jsonl", "w", encoding="utf-8") as out_reasoning:
         
        for week_dir, _, _ in weeks:
            tr_file = f"agent_memory/{week_dir}/trades_log.jsonl"
            rs_file = f"agent_memory/{week_dir}/reasoning_log.jsonl"
            
            if os.path.exists(tr_file):
                with open(tr_file, "r", encoding="utf-8") as f:
                    out_trades.write(f.read())
                    
            if os.path.exists(rs_file):
                with open(rs_file, "r", encoding="utf-8") as f:
                    out_reasoning.write(f.read())
                    
    print("Merge completato! I risultati sono pronti per essere letti dalla dashboard.")

if __name__ == "__main__":
    run_parallel()
