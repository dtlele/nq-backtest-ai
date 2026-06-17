import json
import os
import datetime
import pytz

def run_volume_threshold_search():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    reasoning_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl"
    
    if os.path.exists(trades_path + ".test_temp"):
        trades_path += ".test_temp"
    if os.path.exists(reasoning_path + ".test_temp"):
        reasoning_path += ".test_temp"
        
    print(f"Loading data from: {trades_path} and {reasoning_path}")
    
    # 1. Load active reasoning log for May-Nov 2025
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
                
    # 2. Load and match active trades log
    matched_records = []
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
                
                # Match nearest reasoning
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
            except Exception as e:
                pass
                
    print(f"Matched {len(matched_records)} trades for threshold search.\n")
    
    thresholds = [3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000]
    
    print("=== VOLUME THRESHOLD PERFORMANCE FOR A+ SETUPS ===")
    print(f"{'Threshold (Vol >= X)':<25} | {'Trades (N)':<10} | {'Wins':<5} | {'Win Rate':<8} | {'Net P&L (USD)':<15}")
    print("-" * 75)
    for th in thresholds:
        items = []
        for record in matched_records:
            t = record['trade']
            r = record['reasoning']
            pnl = t.get('pnl_usd', 0.0)
            win = 1 if pnl > 0 else 0
            bar_vol = r.get('bar_volume', 0)
            
            if bar_vol >= th:
                items.append({'win': win, 'pnl': pnl})
                
        if not items:
            print(f"Volume >= {th:<13} | 0          | 0     | 0.0%     | +$0.00")
            continue
            
        wins = sum(i['win'] for i in items)
        wr = wins / len(items) * 100
        pnl = sum(i['pnl'] for i in items)
        print(f"Volume >= {th:<13} | {len(items):<10} | {wins:<5} | {wr:>5.1f}%   | {pnl:>+13.2f}")

if __name__ == '__main__':
    run_volume_threshold_search()
