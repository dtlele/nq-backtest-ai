import json
import os
from collections import defaultdict

def run_delta_alignment_analysis():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    if not os.path.exists(trades_path):
        trades_path += ".test_temp"
        
    reasoning_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl"
    if not os.path.exists(reasoning_path):
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
                
    print(f"Matched {len(matched_records)} trades for delta analysis.\n")
    
    alignment_groups = defaultdict(list)
    delta_size_groups = defaultdict(list)
    
    for record in matched_records:
        t = record['trade']
        r = record['reasoning']
        
        pnl = t.get('pnl_usd', 0.0)
        win = 1 if pnl > 0 else 0
        direction = t.get('direction', '')
        
        # Get entry bar delta
        delta = r.get('bar_delta', 0)
        
        # Determine alignment
        if direction == 'long':
            is_concordant = (delta > 0)
        elif direction == 'short':
            is_concordant = (delta < 0)
        else:
            continue
            
        if delta == 0:
            align_type = "Neutral Delta (0)"
        elif is_concordant:
            align_type = "Concordant Delta (Same Direction as Trade)"
        else:
            align_type = "Discordant Delta (Opposite to Trade - Absorption)"
            
        alignment_groups[align_type].append({'win': win, 'pnl': pnl, 'delta': delta})
        
        # Determine delta size effect
        abs_delta = abs(delta)
        if abs_delta < 150:
            size_bucket = "Low Delta (<150)"
        elif abs_delta < 400:
            size_bucket = "Medium Delta (150-400)"
        else:
            size_bucket = "High Delta (>=400)"
            
        delta_size_groups[size_bucket].append({'win': win, 'pnl': pnl})

    print("=== DELTA CONCORDANCE (ALIGNMENT) PERFORMANCE ===")
    print(f"{'Delta Alignment':<55} | {'N':<4} | {'WR%':<6} | {'Net P&L (USD)':<15}")
    print("-" * 90)
    for key, items in sorted(alignment_groups.items()):
        wins = sum(i['win'] for i in items)
        wr = wins / len(items) * 100
        pnl = sum(i['pnl'] for i in items)
        avg_d = sum(abs(i['delta']) for i in items) / len(items)
        print(f"{key:<55} | {len(items):<4} | {wr:>5.1f}% | {pnl:>+13.2f} (Avg |Delta|: {avg_d:.1f})")
        
    print("\n=== ABSOLUTE DELTA SIZE PERFORMANCE ===")
    print(f"{'Delta Size Bucket':<30} | {'N':<4} | {'WR%':<6} | {'Net P&L (USD)':<15}")
    print("-" * 65)
    for key, items in sorted(delta_size_groups.items()):
        wins = sum(i['win'] for i in items)
        wr = wins / len(items) * 100
        pnl = sum(i['pnl'] for i in items)
        print(f"{key:<30} | {len(items):<4} | {wr:>5.1f}% | {pnl:>+13.2f}")

if __name__ == '__main__':
    run_delta_alignment_analysis()
