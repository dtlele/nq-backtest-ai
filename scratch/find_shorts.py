import os
import json
import glob

def find_shorts():
    memory_dir = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory"
    
    # 1. Search trades_log.jsonl and its backups for executed short trades
    trade_files = glob.glob(os.path.join(memory_dir, "*trades_log*.jsonl*"))
    print(f"Found {len(trade_files)} trade log files.")
    for tf in trade_files:
        short_count = 0
        total_count = 0
        with open(tf, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    total_count += 1
                    if data.get('direction') == 'short':
                        short_count += 1
                except:
                    pass
        if short_count > 0:
            print(f"  {os.path.basename(tf)}: {short_count} short trades out of {total_count} total trades.")

    # 2. Search reasoning_log.jsonl and backups for short evaluations that were NOT bypassed
    reasoning_files = glob.glob(os.path.join(memory_dir, "*reasoning_log*.jsonl*"))
    print(f"\nFound {len(reasoning_files)} reasoning log files.")
    for rf in reasoning_files:
        short_evaluated = 0
        short_bypassed = 0
        total_eval = 0
        with open(rf, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    total_eval += 1
                    if data.get('fabio_direction') == 'short':
                        # Check if it was bypassed or evaluated
                        if data.get('fabio_entry') is not None:
                            short_evaluated += 1
                        else:
                            short_bypassed += 1
                except:
                    pass
        if short_evaluated > 0 or short_bypassed > 0:
            print(f"  {os.path.basename(rf)}: {short_evaluated} evaluated shorts, {short_bypassed} bypassed shorts out of {total_eval} total records.")

if __name__ == '__main__':
    find_shorts()
