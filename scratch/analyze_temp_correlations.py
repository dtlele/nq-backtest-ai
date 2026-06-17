import json
import os
from collections import defaultdict
from datetime import datetime
import pytz

def parse_vwap_status(text):
    if not text:
        return "unknown"
    t_lower = text.lower()
    if "above vwap" in t_lower or "above rth vwap" in t_lower or "above the vwap" in t_lower or "above the rth vwap" in t_lower:
        return "above"
    if "below vwap" in t_lower or "below rth vwap" in t_lower or "below the vwap" in t_lower or "below the rth vwap" in t_lower:
        return "below"
    return "unknown"

def run_correlation_mining():
    # Force test_temp paths to analyze the full historical run
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl.test_temp"
    reasoning_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl.test_temp"
    
    print(f"Loading trades from: {trades_path}")
    print(f"Loading reasoning from: {reasoning_path}")
    
    if not os.path.exists(trades_path) or not os.path.exists(reasoning_path):
        print("Error: test_temp files do not exist. Using standard paths as fallback.")
        trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
        reasoning_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl"
    
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
                
    print(f"Matched {len(matched_records)} trades for mining.")
    
    samples = []
    for m in matched_records:
        t = m['trade']
        r = m['reasoning']
        dt_et = m['dt_et']
        
        close = r.get('bar_close')
        ibh = r.get('ib_high')
        ibl = r.get('ib_low')
        vah = r.get('va_high')
        val = r.get('va_low')
        poc = r.get('poc')
        dt = r.get('day_type', 'unknown')
        pnl = t.get('pnl_usd', 0.0)
        
        # Hour & minute
        h = dt_et.hour
        m_val = dt_et.minute
        
        # Hour bucket
        time_minutes = h * 60 + m_val
        if 9*60+30 <= time_minutes <= 11*60+30:
            hour_bucket = "first_2_hours (09:30-11:30)"
        else:
            hour_bucket = "later_hours (after 11:30)"
            
        # Day of week
        dow = dt_et.strftime('%A')
        
        # IB Location
        if close is None or ibh is None or ibl is None:
            ib_loc = 'unknown'
        elif close > ibh:
            ib_loc = 'above_ibh'
        elif close < ibl:
            ib_loc = 'below_ibl'
        else:
            ib_loc = 'inside_ib'
            
        # VA Location
        if close is None or vah is None or val is None:
            va_loc = 'unknown'
        elif close > vah:
            va_loc = 'above_vah'
        elif close < val:
            va_loc = 'below_val'
        else:
            va_loc = 'inside_va'
            
        # POC Location
        if close is None or poc is None:
            poc_loc = 'unknown'
        elif close > poc:
            poc_loc = 'above_poc'
        else:
            poc_loc = 'below_poc'
            
        # VWAP
        text = str(r.get('fabio_reasoning', '')) + " " + str(r.get('market_narrative', '')) + " " + str(t.get('fabio_reasoning', ''))
        vwap_loc = parse_vwap_status(text)
        
        # Stop distance
        stop_dist = abs(t.get('entry', 0.0) - t.get('stop', 0.0))
        if stop_dist < 15:
            stop_bucket = "<15_pts"
        elif stop_dist <= 25:
            stop_bucket = "15-25_pts"
        elif stop_dist <= 35:
            stop_bucket = "25-35_pts"
        else:
            stop_bucket = ">35_pts"
            
        samples.append({
            'hour': f"{h:02d}:00",
            'hour_bucket': hour_bucket,
            'day_of_week': dow,
            'ib_loc': ib_loc,
            'va_loc': va_loc,
            'poc_loc': poc_loc,
            'vwap_loc': vwap_loc,
            'day_type': dt,
            'stop_bucket': stop_bucket,
            'pnl': pnl,
            'win': 1 if pnl > 0 else 0
        })
        
    print(f"Generated {len(samples)} samples for combinatorial analysis.\n")
    
    features = ['hour', 'hour_bucket', 'day_of_week', 'ib_loc', 'va_loc', 'poc_loc', 'vwap_loc', 'day_type', 'stop_bucket']
    
    print("=== SINGLE FEATURE PERFORMANCE ===")
    for f in features:
        groups = defaultdict(list)
        for s in samples:
            groups[s[f]].append(s)
            
        print(f"\nFeature: {f.upper()}")
        for g_name, items in sorted(groups.items(), key=lambda x: len(x[1]), reverse=True):
            wins = sum(i['win'] for i in items)
            wr = wins / len(items) * 100
            pnl = sum(i['pnl'] for i in items)
            print(f"  {g_name:<30} | N={len(items):<3} | Wins={wins:<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

    print("\n" + "="*80)
    print("COMBINATORIAL SEARCH: GOLDEN COMBINATIONS (Win Rate >= 45% & N >= 5)")
    print("="*80)
    
    combos_2 = defaultdict(list)
    for s in samples:
        for i in range(len(features)):
            for j in range(i+1, len(features)):
                f1, f2 = features[i], features[j]
                combos_2[(f1, s[f1], f2, s[f2])].append(s)
                
    valid_combos_2 = []
    for key, items in combos_2.items():
        wins = sum(i['win'] for i in items)
        wr = wins / len(items) * 100
        pnl = sum(i['pnl'] for i in items)
        if len(items) >= 5 and wr >= 45.0:
            valid_combos_2.append((key, len(items), wins, wr, pnl))
            
    print("\n--- Top 20 Double-Feature Combinations (by PnL) ---")
    for key, count, wins, wr, pnl in sorted(valid_combos_2, key=lambda x: x[4], reverse=True)[:20]:
        f1, val1, f2, val2 = key
        desc = f"{f1}={val1} & {f2}={val2}"
        print(f"  {desc:<60} | N={count:<3} | W={wins:<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

    combos_3 = defaultdict(list)
    for s in samples:
        for i in range(len(features)):
            for j in range(i+1, len(features)):
                for k in range(j+1, len(features)):
                    f1, f2, f3 = features[i], features[j], features[k]
                    combos_3[(f1, s[f1], f2, s[f2], f3, s[f3])].append(s)
                    
    valid_combos_3 = []
    for key, items in combos_3.items():
        wins = sum(i['win'] for i in items)
        wr = wins / len(items) * 100
        pnl = sum(i['pnl'] for i in items)
        if len(items) >= 5 and wr >= 45.0:
            valid_combos_3.append((key, len(items), wins, wr, pnl))
            
    print("\n--- Top 25 Triple-Feature Combinations (by PnL) ---")
    for key, count, wins, wr, pnl in sorted(valid_combos_3, key=lambda x: x[4], reverse=True)[:25]:
        f1, val1, f2, val2, f3, val3 = key
        desc = f"{val1} & {val2} & {val3}"
        keys_desc = f"({f1}, {f2}, {f3})"
        print(f"  {desc:<55} | N={count:<3} | W={wins:<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f} | Features: {keys_desc}")

if __name__ == '__main__':
    run_correlation_mining()
