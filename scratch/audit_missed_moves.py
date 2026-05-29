import json
import pandas as pd
from pathlib import Path
from datetime import timedelta

def analyze_missed_moves():
    log_path = Path('agent_memory/reasoning_log.jsonl')
    if not log_path.exists():
        print("No reasoning log found.")
        return

    records = []
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                records.append(json.loads(line))
            except:
                pass

    if not records:
        print("No records found.")
        return

    df = pd.DataFrame(records)
    df['bar_time_utc'] = pd.to_datetime(df['bar_time_utc'])
    df = df.sort_values('bar_time_utc')

    print(f"Loaded {len(df)} reasonings.")
    
    missed_moves = []
    
    price_curve = df[['bar_time_utc', 'bar_close']].drop_duplicates().set_index('bar_time_utc')['bar_close']
    
    for _, row in df.iterrows():
        if row['decision'] == 'no_trade':
            wall_side = row.get('wall_side')
            expected_dir = 'long' if wall_side == 'bid' else ('short' if wall_side == 'ask' else None)
            
            if not expected_dir: continue
            
            entry_time = row['bar_time_utc']
            entry_price = row['bar_close']
            
            end_time = entry_time + timedelta(minutes=60)
            future_prices = price_curve[(price_curve.index > entry_time) & (price_curve.index <= end_time)]
            
            if future_prices.empty:
                continue
                
            if expected_dir == 'long':
                max_price = future_prices.max()
                min_price = future_prices.min()
                mfe = max_price - entry_price
                mae = entry_price - min_price
            else:
                min_price = future_prices.min()
                max_price = future_prices.max()
                mfe = entry_price - min_price
                mae = max_price - entry_price
                
            if mfe >= 20 and mae <= 15:
                missed_moves.append({
                    'time': entry_time,
                    'dir': expected_dir,
                    'setup': row.get('fabio_setup') or row.get('setup_category'),
                    'reasoning': row.get('fabio_reasoning'),
                    'mfe_pts': mfe,
                    'mae_pts': mae
                })

    missed_df = pd.DataFrame(missed_moves)
    if missed_df.empty:
        print("No heavily missed moves found (MFE > 20 pts, MAE < 15 pts).")
    else:
        print(f"\n--- FOUND {len(missed_df)} MISSED OPPORTUNITIES ---")
        # Print top 10 missed moves by MFE
        top = missed_df.sort_values('mfe_pts', ascending=False).head(10)
        for _, m in top.iterrows():
            print(f"\nTime: {m['time']} | Dir: {m['dir']} | Setup: {m['setup']}")
            print(f"MFE: +{m['mfe_pts']:.2f} pts | MAE: -{m['mae_pts']:.2f} pts")
            print(f"Fabio said: {m['reasoning']}")

if __name__ == '__main__':
    analyze_missed_moves()
