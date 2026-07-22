import json
import pandas as pd
from src.data_loader import load_databento_csv

def analyze_trails():
    trades = []
    with open('agent_memory/trades_log.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                trades.append(json.loads(line))
    
    trail_trades = [t for t in trades if t.get('exit_reason') in ('trailing_stop', 'partial_tp')]
    print(f"Total Trailed/Partial Trades: {len(trail_trades)}")
    
    reached_target_count = 0
    
    # Group by date to load data once per day
    by_date = {}
    for t in trail_trades:
        by_date.setdefault(t['date'], []).append(t)
        
    for date_str, daily_trades in by_date.items():
        try:
            df = load_databento_csv(f'C:/Users/Mauro/Documents/nq-backtest-clean/data/xnas-itch-{date_str.replace("-","")}.csv.zst')
            if df.empty:
                continue
            for t in daily_trades:
                entry_time = pd.to_datetime(t['entry_time'])
                # Filter data after entry
                future_df = df[df.index >= entry_time]
                target = t['target']
                orig_stop = t['stop']
                direction = t['direction']
                
                would_hit_target = False
                for idx, row in future_df.iterrows():
                    high = row['high']
                    low = row['low']
                    
                    if direction == 'long':
                        if low <= orig_stop:
                            break # Hit original stop first
                        if high >= target:
                            would_hit_target = True
                            break
                    else:
                        if high >= orig_stop:
                            break # Hit original stop first
                        if low <= target:
                            would_hit_target = True
                            break
                if would_hit_target:
                    reached_target_count += 1
                    print(f"Trade {t['entry_time']} ({direction}) AT {t['entry']} WOULD HAVE HIT TARGET {target}")
                else:
                    print(f"Trade {t['entry_time']} ({direction}) AT {t['entry']} correctly exited by trail/BE before hitting original stop.")
        except Exception as e:
            print(f"Error loading {date_str}: {e}")
            
    print(f"\n--- SUMMARY ---")
    print(f"Total Trailed/Partial Trades analyzed: {len(trail_trades)}")
    print(f"Would have hit full target: {reached_target_count}")
    print(f"Correctly trailed (would have hit stop): {len(trail_trades) - reached_target_count}")

if __name__ == '__main__':
    analyze_trails()
