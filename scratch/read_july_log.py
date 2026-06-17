import os
import sys

def read_july_run_log_trades():
    path = r'c:\Users\Mauro\Documents\nq-backtest\output\reports\july_run.log'
    if not os.path.exists(path):
        print("File does not exist.")
        return
        
    try:
        content = None
        with open(path, 'r', encoding='utf-16-le', errors='ignore') as f:
            content = f.read()
            
        if not content:
            print("Content is empty.")
            return
            
        if content.startswith('\ufeff'):
            content = content[1:]
            
        lines = content.splitlines()
        print(f"Total lines in log: {len(lines)}")
        
        def clean_text(text):
            return text.encode('ascii', 'replace').decode('ascii')
            
        print("\n--- Trade and Decision events inside july_run.log ---")
        for idx, line in enumerate(lines):
            line_lower = line.lower()
            if any(x in line for x in ['[TRADE', '[DECISION', '[CONSENSUS', '[AUDIT', 'pnl_usd', 'PnL']) or 'stop loss' in line_lower or 'target hit' in line_lower:
                print(f"L{idx}: {clean_text(line)}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    read_july_run_log_trades()
