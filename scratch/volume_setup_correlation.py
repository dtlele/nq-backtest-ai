import json
import os
from collections import defaultdict

def run_volume_setup_analysis():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    if not os.path.exists(trades_path):
        trades_path += ".test_temp"
        
    print(f"Loading trades from: {trades_path}")
    
    setup_volume_groups = defaultdict(list)
    
    with open(trades_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                t = json.loads(line)
                date_str = t.get('date', '')
                if not (date_str >= '2025-05-01' and date_str <= '2025-11-30'):
                    continue
                    
                pnl = t.get('pnl_usd', 0.0)
                win = 1 if pnl > 0 else 0
                setup = t.get('setup_type', 'unknown')
                
                # Let's extract the volume if it is logged, or match it
                # Wait, the trades log does not contain bar volume directly, but we can look at pnl and setup!
                # Wait, can we match it with the reasoning log to get the actual volume of the entry bar?
                # Yes, let's load reasoning log and match!
            except:
                pass
                
    # Let's do the matched records loading
    reasoning_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl"
    if not os.path.exists(reasoning_path):
        reasoning_path += ".test_temp"
        
    reasoning_by_date_time = {}
    with open(reasoning_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                date_str = data.get('date', '')
                if not (date_str >= '2025-05-01' and date_str <= '2025-11-30'):
                    continue
                bar_time_et = data.get('bar_time_et')
                if date_str and bar_time_et:
                    reasoning_by_date_time[(date_str, bar_time_et)] = data
            except:
                pass
                
    # Match trades to reasoning
    matched_records = []
    import datetime, pytz
    with open(trades_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                t = json.loads(line)
                date_str = t.get('date', '')
                if not (date_str >= '2025-05-01' and date_str <= '2025-11-30'):
                    continue
                    
                entry_time_str = t.get('entry_time')
                dt = datetime.datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
                dt_et = dt.astimezone(pytz.timezone("America/New_York"))
                et_time_str = dt_et.strftime("%H:%M")
                
                matched_r = None
                if (date_str, et_time_str) in reasoning_by_date_time:
                    matched_r = reasoning_by_date_time[(date_str, et_time_str)]
                else:
                    h_trade, m_trade = dt_et.hour, dt_et.minute
                    best_diff = 999
                    for (r_date, r_time_str), r_data in reasoning_by_date_time.items():
                        if r_date != date_str:
                            continue
                        try:
                            h_r, m_r = map(int, r_time_str.split(':'))
                            diff = abs((h_trade * 60 + m_trade) - (h_r * 60 + m_r))
                            if diff < best_diff and diff <= 10:
                                best_diff = diff
                                matched_r = r_data
                        except:
                            pass
                            
                if matched_r:
                    matched_records.append({
                        'trade': t,
                        'reasoning': matched_r
                    })
            except:
                pass
                
    # Group by volume_bucket and setup_type
    combo_groups = defaultdict(list)
    for record in matched_records:
        t = record['trade']
        r = record['reasoning']
        
        pnl = t.get('pnl_usd', 0.0)
        win = 1 if pnl > 0 else 0
        setup = t.get('setup_type', 'unknown')
        
        bar_vol = r.get('bar_volume', 0)
        
        if bar_vol < 1500:
            vol_bucket = "<1.5k"
        elif bar_vol < 3000:
            vol_bucket = "1.5k-3k"
        elif bar_vol < 6000:
            vol_bucket = "3k-6k"
        else:
            vol_bucket = ">=6k"
            
        combo_groups[(vol_bucket, setup)].append({'win': win, 'pnl': pnl})
        
    print("\n=== VOLUME BUCKET + SETUP TYPE COMBINATORIAL PERFORMANCE ===")
    print(f"{'Vol Bucket':<12} | {'Setup Type':<25} | {'N':<4} | {'WR%':<6} | {'Net P&L (USD)':<15}")
    print("-" * 75)
    for key, items in sorted(combo_groups.items(), key=lambda x: sum(i['pnl'] for i in x[1]), reverse=True):
        vol, setup = key
        wins = sum(i['win'] for i in items)
        wr = wins / len(items) * 100
        pnl = sum(i['pnl'] for i in items)
        print(f"{vol:<12} | {setup:<25} | {len(items):<4} | {wr:>5.1f}% | {pnl:>+13.2f}")

if __name__ == '__main__':
    run_volume_setup_analysis()
