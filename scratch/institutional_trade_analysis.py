import json
import os
import re
from datetime import datetime
import pytz
from collections import defaultdict

def run_institutional_analysis():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    reasoning_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl"
    
    if not os.path.exists(trades_path):
        trades_path += ".test_temp"
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
                dt = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
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
                        'reasoning': matched_r,
                        'dt_et': dt_et
                    })
            except Exception as e:
                pass
                
    print(f"Successfully matched {len(matched_records)} trades for deep analysis.\n")
    
    # ── METRICS TO COMPUTE ──
    # 1. Volume and Big Trade Size/Count Correlation
    # 2. Entry Proximity to Institutional Wall
    # 3. Stop Placement: Where are stops protected and how do they perform?
    
    wall_size_groups = defaultdict(list)
    wall_count_groups = defaultdict(list)
    bar_vol_groups = defaultdict(list)
    
    entry_proximity_groups = defaultdict(list)
    stop_protection_groups = defaultdict(list)
    stop_buffer_groups = defaultdict(list)
    
    for record in matched_records:
        t = record['trade']
        r = record['reasoning']
        
        pnl = t.get('pnl_usd', 0.0)
        win = 1 if pnl > 0 else 0
        entry = t.get('entry', 0.0)
        stop = t.get('stop', 0.0)
        
        # A. Volumes & Big Trades
        bar_vol = r.get('bar_volume', 0)
        wall_size = r.get('wall_max_size', 0)
        wall_count = r.get('wall_trade_count', 0)
        
        # Categorize bar volume
        if bar_vol < 1500:
            vol_bucket = "<1.5k (Low/Pullback)"
        elif bar_vol < 3000:
            vol_bucket = "1.5k-3k (Average)"
        elif bar_vol < 6000:
            vol_bucket = "3k-6k (High Institutional)"
        else:
            vol_bucket = ">=6k (Extreme Drive/Panic)"
            
        # Categorize big trade size
        if wall_size == 0:
            size_bucket = "0 (No Big Trade)"
        elif wall_size < 50:
            size_bucket = "<50 contracts (Small)"
        elif wall_size < 150:
            size_bucket = "50-150 contracts (Medium)"
        elif wall_size < 400:
            size_bucket = "150-400 contracts (Heavy)"
        else:
            size_bucket = ">=400 contracts (Blockbuster)"
            
        # Categorize big trade count
        if wall_count == 0:
            count_bucket = "0"
        elif wall_count <= 2:
            count_bucket = "1-2 (Single orders)"
        elif wall_count <= 10:
            count_bucket = "3-10 (Cluster)"
        else:
            count_bucket = ">10 (Heavy Battle)"
            
        bar_vol_groups[vol_bucket].append({'win': win, 'pnl': pnl})
        wall_size_groups[size_bucket].append({'win': win, 'pnl': pnl})
        wall_count_groups[count_bucket].append({'win': win, 'pnl': pnl})
        
        # B. Entry Proximity to Institutional Wall
        wall_level = r.get('wall_level', 0.0)
        if wall_level and entry:
            dist_to_wall = abs(entry - wall_level)
            if dist_to_wall == 0:
                prox_bucket = "Exact Match (0 pts)"
            elif dist_to_wall <= 2.0:
                prox_bucket = "Tight (0-2 pts / 0-8 ticks)"
            elif dist_to_wall <= 5.0:
                prox_bucket = "Moderate (2-5 pts / 8-20 ticks)"
            else:
                prox_bucket = "Wide (>5 pts / >20 ticks)"
            entry_proximity_groups[prox_bucket].append({'win': win, 'pnl': pnl})
            
        # C. Stop Protection Analysis
        # Where is the stop placed relative to macro/micro structures?
        ib_high = r.get('ib_high', 0.0)
        ib_low = r.get('ib_low', 0.0)
        va_high = r.get('va_high', 0.0)
        va_low = r.get('va_low', 0.0)
        poc = r.get('poc', 0.0)
        
        # Identify the closest key level to the stop to see what "protected" it
        levels = [
            (ib_high, "IB_HIGH (Macro)"),
            (ib_low, "IB_LOW (Macro)"),
            (va_high, "VA_HIGH (Macro)"),
            (va_low, "VA_LOW (Macro)"),
            (poc, "POC (Micro)"),
            (wall_level, "Institutional Wall (Micro)")
        ]
        
        # Find which level the stop was placed behind (within 10 points)
        best_level_name = "Undefined/Other"
        best_dist = 999.0
        
        for level_val, level_name in levels:
            if not level_val:
                continue
            # Check if stop is protected (i.e. if LONG, stop is below the level; if SHORT, stop is above)
            is_protected = False
            if t.get('direction') == 'long' and stop <= level_val + 1.0: # allow 1pt tolerance
                is_protected = True
            elif t.get('direction') == 'short' and stop >= level_val - 1.0:
                is_protected = True
                
            if is_protected:
                dist = abs(stop - level_val)
                if dist < best_dist:
                    best_dist = dist
                    best_level_name = level_name
                    
        stop_protection_groups[best_level_name].append({'win': win, 'pnl': pnl})
        
        # Stop buffer distance from the protective level
        if best_level_name != "Undefined/Other" and best_dist < 20.0:
            if best_dist <= 1.0:
                buf_bucket = "Aggressive (0-1 pts / 0-4 ticks)"
            elif best_dist <= 3.0:
                buf_bucket = "Standard (1-3 pts / 4-12 ticks)"
            elif best_dist <= 6.0:
                buf_bucket = "Conservative (3-6 pts / 12-24 ticks)"
            else:
                buf_bucket = "Wide (>6 pts)"
            stop_buffer_groups[buf_bucket].append({'win': win, 'pnl': pnl})

    # ── PRINT RESULTS ──
    print("================================================================================")
    print("INSTITUTIONAL TRADE ANALYSIS: VOLUMES, BIG TRADES, ENTRIES AND PROTECTION")
    print("================================================================================")
    
    print("\n1. BAR VOLUME EFFECT ON WIN RATE")
    print(f"{'Volume Bucket':<30} | {'N':<4} | {'WR%':<6} | {'Net P&L (USD)':<15}")
    print("-" * 65)
    for bucket, items in sorted(bar_vol_groups.items()):
        wins = sum(i['win'] for i in items)
        wr = wins / len(items) * 100
        pnl = sum(i['pnl'] for i in items)
        print(f"{bucket:<30} | {len(items):<4} | {wr:>5.1f}% | {pnl:>+13.2f}")
        
    print("\n2. BIG TRADE SIZE (SINGLE ORDER) EFFECT ON WIN RATE")
    print(f"{'Big Trade Size':<30} | {'N':<4} | {'WR%':<6} | {'Net P&L (USD)':<15}")
    print("-" * 65)
    for bucket, items in sorted(wall_size_groups.items()):
        wins = sum(i['win'] for i in items)
        wr = wins / len(items) * 100
        pnl = sum(i['pnl'] for i in items)
        print(f"{bucket:<30} | {len(items):<4} | {wr:>5.1f}% | {pnl:>+13.2f}")
        
    print("\n3. BIG TRADE TRANSACTION COUNT EFFECT ON WIN RATE")
    print(f"{'Big Trade Count':<30} | {'N':<4} | {'WR%':<6} | {'Net P&L (USD)':<15}")
    print("-" * 65)
    for bucket, items in sorted(wall_count_groups.items()):
        wins = sum(i['win'] for i in items)
        wr = wins / len(items) * 100
        pnl = sum(i['pnl'] for i in items)
        print(f"{bucket:<30} | {len(items):<4} | {wr:>5.1f}% | {pnl:>+13.2f}")
        
    print("\n4. ENTRY PROXIMITY TO THE INSTITUTIONAL WALL (LIMIT ORDER TIGHTNESS)")
    print(f"{'Proximity to Wall':<30} | {'N':<4} | {'WR%':<6} | {'Net P&L (USD)':<15}")
    print("-" * 65)
    for bucket, items in sorted(entry_proximity_groups.items(), key=lambda x: x[0]):
        wins = sum(i['win'] for i in items)
        wr = wins / len(items) * 100
        pnl = sum(i['pnl'] for i in items)
        print(f"{bucket:<30} | {len(items):<4} | {wr:>5.1f}% | {pnl:>+13.2f}")
        
    print("\n5. STOP LOSS PROTECTION LEVEL (THE SHIELD)")
    print(f"{'Protective Level':<30} | {'N':<4} | {'WR%':<6} | {'Net P&L (USD)':<15}")
    print("-" * 65)
    for bucket, items in sorted(stop_protection_groups.items(), key=lambda x: sum(i['pnl'] for i in x[1]), reverse=True):
        wins = sum(i['win'] for i in items)
        wr = wins / len(items) * 100
        pnl = sum(i['pnl'] for i in items)
        print(f"{bucket:<30} | {len(items):<4} | {wr:>5.1f}% | {pnl:>+13.2f}")
        
    print("\n6. STOP BUFFER DISTANCE BEHIND THE SHIELD")
    print(f"{'Stop Buffer Size':<30} | {'N':<4} | {'WR%':<6} | {'Net P&L (USD)':<15}")
    print("-" * 65)
    for bucket, items in sorted(stop_buffer_groups.items()):
        wins = sum(i['win'] for i in items)
        wr = wins / len(items) * 100
        pnl = sum(i['pnl'] for i in items)
        print(f"{bucket:<30} | {len(items):<4} | {wr:>5.1f}% | {pnl:>+13.2f}")

if __name__ == '__main__':
    run_institutional_analysis()
