import os
import shutil
import subprocess

def main():
    memory_dir = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory"
    reasoning_log = os.path.join(memory_dir, "reasoning_log.jsonl")
    trades_log = os.path.join(memory_dir, "trades_log.jsonl")
    
    reasoning_bak = os.path.join(memory_dir, "reasoning_log.jsonl.test_temp")
    trades_bak = os.path.join(memory_dir, "trades_log.jsonl.test_temp")
    
    # 1. Back up existing active logs
    print("Backing up active logs...")
    if os.path.exists(reasoning_log):
        shutil.move(reasoning_log, reasoning_bak)
        print("  Moved reasoning_log.jsonl to reasoning_log.jsonl.test_temp")
    if os.path.exists(trades_log):
        shutil.move(trades_log, trades_bak)
        print("  Moved trades_log.jsonl to trades_log.jsonl.test_temp")
        
    try:
        # 2. Run backtest for May 5, 2025 (20250505)
        # May 5 is glbx-mdp3-20250505.trades.csv
        print("\nLaunching backtest for May 5, 2025 (Fresh run)...")
        cmd = [
            "python",
            "run_backtest.py",
            "--start-date", "20250505",
            "--end-date", "20250505",
            "--data-dir", "archive_data",
            "--quiet",
            "--reset-equity"
        ]
        
        # Run command and capture output
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=r"c:\Users\Mauro\Documents\nq-backtest")
        
        print("\n--- Command Output ---")
        print(res.stdout)
        if res.stderr:
            print("\n--- Error Output ---")
            print(res.stderr)
            
        # 3. Read the generated reasoning log and verify results
        print("\nVerifying test results in the generated reasoning_log.jsonl...")
        if os.path.exists(reasoning_log):
            import json
            with open(reasoning_log, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    time = data.get('bar_time_et')
                    fd = data.get('fabio_direction')
                    decision = data.get('decision')
                    reason = data.get('no_trade_reason')
                    target = data.get('fabio_target')
                    entry = data.get('fabio_entry')
                    stop = data.get('fabio_stop')
                    r_ratio = data.get('r_ratio')
                    
                    print(f"Time: {time} | Direction: {fd} | Decision: {decision} | Reason: {reason}")
                    if fd in ['long', 'short'] and entry is not None:
                        print(f"  Entry: {entry} | Stop: {stop} | Target: {target} | R:R: {r_ratio}")
                    print("-" * 80)
        else:
            print("Error: No reasoning log was generated!")
            
        # Also print trades if any were taken
        if os.path.exists(trades_log):
            print("\nVerifying test results in trades_log.jsonl...")
            with open(trades_log, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    t = json.loads(line)
                    print(f"TRADE TAKEN: Date: {t.get('date')} | Dir: {t.get('direction')} | Entry: {t.get('entry')} | Target: {t.get('target')} | Stop: {t.get('stop')} | PnL: {t.get('pnl_usd')}")
        else:
            print("\nNo trades were executed on this test day.")
            
    finally:
        # 4. Clean up test logs and restore active logs
        print("\nCleaning up test logs and restoring active logs...")
        if os.path.exists(reasoning_log):
            os.remove(reasoning_log)
        if os.path.exists(trades_log):
            os.remove(trades_log)
            
        if os.path.exists(reasoning_bak):
            shutil.move(reasoning_bak, reasoning_log)
            print("  Restored reasoning_log.jsonl")
        if os.path.exists(trades_bak):
            shutil.move(trades_bak, trades_log)
            print("  Restored trades_log.jsonl")

if __name__ == '__main__':
    main()
