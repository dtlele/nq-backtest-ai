import json
import os
import re
from collections import defaultdict
import pytz
from datetime import datetime

LOG_PAIRS = [
    {
        'trades': r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl",
        'reasoning': r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl"
    },
    {
        'trades': r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_jan2025.jsonl",
        'reasoning': r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log_jan2025.jsonl"
    },
    {
        'trades': r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_ds_feb_wide_stops.jsonl",
        'reasoning': r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log_ds_feb_wide_stops.jsonl"
    },
    {
        'trades': r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_ds_feb_no_money_mgmt.jsonl",
        'reasoning': r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log_ds_feb_no_money_mgmt.jsonl"
    },
    {
        'trades': r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_pre_fix.jsonl",
        'reasoning': r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log_pre_fix.jsonl"
    }
]

def parse_vwap_status(text):
    if not text:
        return "unknown"
    t_lower = text.lower()
    if "above vwap" in t_lower or "above rth vwap" in t_lower or "above the vwap" in t_lower or "above the rth vwap" in t_lower:
        return "above"
    if "below vwap" in t_lower or "below rth vwap" in t_lower or "below the vwap" in t_lower or "below the rth vwap" in t_lower:
        return "below"
    return "unknown"

def analyze_long_and_shorts():
    all_matched = []
    
    for pair in LOG_PAIRS:
        trade_path = pair['trades']
        reasoning_path = pair['reasoning']
        
        if not os.path.exists(trade_path) or not os.path.exists(reasoning_path):
            continue
            
        reasoning_by_date_time = {}
        with open(reasoning_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    date = data.get('date')
                    bar_time_et = data.get('bar_time_et')
                    if date and bar_time_et:
                        reasoning_by_date_time[(date, bar_time_et)] = data
                except:
                    pass
                    
        with open(trade_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    t = json.loads(line)
                    date = t.get('date')
                    entry_time_str = t.get('entry_time')
                    if not date or not entry_time_str:
                        continue
                        
                    dt = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
                    dt_et = dt.astimezone(pytz.timezone("America/New_York"))
                    et_time_str = dt_et.strftime("%H:%M")
                    
                    matched_r = None
                    if (date, et_time_str) in reasoning_by_date_time:
                        matched_r = reasoning_by_date_time[(date, et_time_str)]
                    else:
                        h_trade, m_trade = dt_et.hour, dt_et.minute
                        best_diff = 999
                        for (r_date, r_time_str), r_data in reasoning_by_date_time.items():
                            if r_date != date:
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
                        all_matched.append({
                            'trade': t,
                            'reasoning': matched_r,
                            'source': os.path.basename(trade_path)
                        })
                except Exception as e:
                    pass
                    
    # Let's filter LONG trades
    longs = [m for m in all_matched if m['trade']['direction'] == 'long']
    shorts = [m for m in all_matched if m['trade']['direction'] == 'short']
    
    print("=== DEEP LONG TRADE AUDIT ===")
    # Group longs by:
    # 1. IB location (inside_ib, above_ibh, below_ibl)
    # 2. Stop distance bins: < 15 points, 15-25 points, 25-35 points, > 35 points
    # 3. Setup types
    
    print("\n[LONG] Performance by Stop Distance (Points):")
    stop_bins = defaultdict(list)
    for m in longs:
        t = m['trade']
        entry = t.get('entry', 0.0)
        stop = t.get('stop', 0.0)
        dist = abs(entry - stop)
        if dist < 15:
            bin_name = "< 15 pts"
        elif dist <= 25:
            bin_name = "15-25 pts"
        elif dist <= 35:
            bin_name = "25-35 pts"
        else:
            bin_name = "> 35 pts"
        stop_bins[bin_name].append(m)
        
    for b_name in ["< 15 pts", "15-25 pts", "25-35 pts", "> 35 pts"]:
        items = stop_bins[b_name]
        wins = [i for i in items if i['trade']['pnl_usd'] > 0]
        wr = len(wins) / len(items) * 100 if items else 0
        pnl = sum(i['trade']['pnl_usd'] for i in items)
        print(f"  {b_name:<10} | N={len(items):<3} | Wins={len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

    print("\n[LONG] Performance of 'above_ibh' vs 'inside_ib' grouped by Setup Type:")
    setup_groups = defaultdict(lambda: defaultdict(list))
    for m in longs:
        t = m['trade']
        r = m['reasoning']
        close = r.get('bar_close')
        ibh = r.get('ib_high')
        ibl = r.get('ib_low')
        loc = "above_ibh" if (close and ibh and close > ibh) else ("below_ibl" if (close and ibl and close < ibl) else "inside_ib")
        setup = t.get('setup_type', 'unknown')
        setup_groups[loc][setup].append(m)
        
    for loc in ['inside_ib', 'above_ibh']:
        print(f"  Location: {loc}")
        for setup, items in setup_groups[loc].items():
            wins = [i for i in items if i['trade']['pnl_usd'] > 0]
            wr = len(wins) / len(items) * 100 if items else 0
            pnl = sum(i['trade']['pnl_usd'] for i in items)
            print(f"    {setup:<20} | N={len(items):<3} | Wins={len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

    print("\n=== DEEP SHORT TRADE AUDIT ===")
    # Group shorts by:
    # 1. Day type
    # 2. Stop distance bins
    # 3. Setup types
    
    print("\n[SHORT] Performance by Stop Distance (Points):")
    short_stop_bins = defaultdict(list)
    for m in shorts:
        t = m['trade']
        entry = t.get('entry', 0.0)
        stop = t.get('stop', 0.0)
        dist = abs(entry - stop)
        if dist < 15:
            bin_name = "< 15 pts"
        elif dist <= 25:
            bin_name = "15-25 pts"
        elif dist <= 35:
            bin_name = "25-35 pts"
        else:
            bin_name = "> 35 pts"
        short_stop_bins[bin_name].append(m)
        
    for b_name in ["< 15 pts", "15-25 pts", "25-35 pts", "> 35 pts"]:
        items = short_stop_bins[b_name]
        wins = [i for i in items if i['trade']['pnl_usd'] > 0]
        wr = len(wins) / len(items) * 100 if items else 0
        pnl = sum(i['trade']['pnl_usd'] for i in items)
        print(f"  {b_name:<10} | N={len(items):<3} | Wins={len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

    print("\n[SHORT] Performance of 'inside_ib' vs 'below_ibl' grouped by Setup Type:")
    short_setup_groups = defaultdict(lambda: defaultdict(list))
    for m in shorts:
        t = m['trade']
        r = m['reasoning']
        close = r.get('bar_close')
        ibh = r.get('ib_high')
        ibl = r.get('ib_low')
        loc = "above_ibh" if (close and ibh and close > ibh) else ("below_ibl" if (close and ibl and close < ibl) else "inside_ib")
        setup = t.get('setup_type', 'unknown')
        short_setup_groups[loc][setup].append(m)
        
    for loc in ['inside_ib', 'below_ibl']:
        print(f"  Location: {loc}")
        for setup, items in short_setup_groups[loc].items():
            wins = [i for i in items if i['trade']['pnl_usd'] > 0]
            wr = len(wins) / len(items) * 100 if items else 0
            pnl = sum(i['trade']['pnl_usd'] for i in items)
            print(f"    {setup:<25} | N={len(items):<3} | Wins={len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

if __name__ == '__main__':
    analyze_long_and_shorts()
