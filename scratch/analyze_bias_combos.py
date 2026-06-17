import json
import os
import re
from collections import defaultdict
from datetime import datetime

# Define log pairs to join trades and reasoning context
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

def run_combo_analysis():
    all_matched_trades = []
    
    for pair in LOG_PAIRS:
        trade_path = pair['trades']
        reasoning_path = pair['reasoning']
        
        if not os.path.exists(trade_path) or not os.path.exists(reasoning_path):
            print(f"Skipping missing pair: {os.path.basename(trade_path)} / {os.path.basename(reasoning_path)}")
            continue
            
        print(f"Processing pair: {os.path.basename(trade_path)}")
        
        # Load reasoning entries
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
                        # Store by date and ET time for easy matching
                        reasoning_by_date_time[(date, bar_time_et)] = data
                except Exception as e:
                    pass
                    
        # Load trades and join
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
                        
                    # Extract ET hour and minute from entry_time to match reasoning
                    # entry_time is like "2025-05-01T14:37:00+00:00"
                    from datetime import datetime
                    import pytz
                    
                    dt = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
                    dt_et = dt.astimezone(pytz.timezone("America/New_York"))
                    et_time_str = dt_et.strftime("%H:%M")
                    
                    # Try to find matching reasoning
                    # The trade is entered based on a candidate bar. Let's look for a reasoning
                    # entry on the same date with the closest time (within 3 minutes)
                    matched_r = None
                    # First try exact match
                    if (date, et_time_str) in reasoning_by_date_time:
                        matched_r = reasoning_by_date_time[(date, et_time_str)]
                    else:
                        # Search for closest time
                        h_trade, m_trade = dt_et.hour, dt_et.minute
                        best_diff = 999
                        for (r_date, r_time_str), r_data in reasoning_by_date_time.items():
                            if r_date != date:
                                continue
                            try:
                                h_r, m_r = map(int, r_time_str.split(':'))
                                diff = abs((h_trade * 60 + m_trade) - (h_r * 60 + m_r))
                                if diff < best_diff and diff <= 5: # Match within 5 minutes
                                    best_diff = diff
                                    matched_r = r_data
                            except:
                                pass
                                
                    if matched_r:
                        all_matched_trades.append({
                            'trade': t,
                            'reasoning': matched_r,
                            'source': os.path.basename(trade_path)
                        })
                except Exception as e:
                    print(f"Error parsing trade: {e}")
                    
    print(f"Successfully matched {len(all_matched_trades)} trades with reasoning context.")
    
    # ── Analyze Performance by Feature Combinations ──
    # Features to extract:
    # 1. Direction (long/short)
    # 2. Relation to IB: above_ibh, below_ibl, inside_ib
    # 3. Relation to POC: above_poc, below_poc
    # 4. Day Type: trend_up, trend_down, balance, transition_state, etc.
    # 5. VWAP status parsed from text (above/below)
    
    for direction in ['long', 'short']:
        dir_trades = [m for m in all_matched_trades if m['trade']['direction'] == direction]
        print(f"\n==================================================================")
        print(f"ANALYSIS FOR {direction.upper()} TRADES (Total matched: {len(dir_trades)})")
        print(f"==================================================================")
        
        # 1. Relation to IB
        ib_groups = defaultdict(list)
        for m in dir_trades:
            t = m['trade']
            r = m['reasoning']
            close = r.get('bar_close')
            ibh = r.get('ib_high')
            ibl = r.get('ib_low')
            
            if close is None or ibh is None or ibl is None:
                ib_groups['unknown'].append(m)
            elif close > ibh:
                ib_groups['above_ibh'].append(m)
            elif close < ibl:
                ib_groups['below_ibl'].append(m)
            else:
                ib_groups['inside_ib'].append(m)
                
        print(f"\n--- Relation to Initial Balance (IB) ---")
        for group, items in ib_groups.items():
            wins = [i for i in items if i['trade']['pnl_usd'] > 0]
            wr = len(wins) / len(items) * 100 if items else 0
            pnl = sum(i['trade']['pnl_usd'] for i in items)
            print(f"  {group:<12} | N={len(items):<3} | Wins={len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")
            
        # 2. Relation to POC
        poc_groups = defaultdict(list)
        for m in dir_trades:
            t = m['trade']
            r = m['reasoning']
            close = r.get('bar_close')
            poc = r.get('poc')
            
            if close is None or poc is None:
                poc_groups['unknown'].append(m)
            elif close > poc:
                poc_groups['above_poc'].append(m)
            else:
                poc_groups['below_poc'].append(m)
                
        print(f"\n--- Relation to Volume Profile POC ---")
        for group, items in poc_groups.items():
            wins = [i for i in items if i['trade']['pnl_usd'] > 0]
            wr = len(wins) / len(items) * 100 if items else 0
            pnl = sum(i['trade']['pnl_usd'] for i in items)
            print(f"  {group:<12} | N={len(items):<3} | Wins={len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

        # 3. Relation to VWAP (parsed from reasoning text)
        vwap_groups = defaultdict(list)
        for m in dir_trades:
            t = m['trade']
            r = m['reasoning']
            text = str(r.get('fabio_reasoning', '')) + " " + str(r.get('market_narrative', '')) + " " + str(t.get('fabio_reasoning', ''))
            vwap_status = parse_vwap_status(text)
            vwap_groups[vwap_status].append(m)
            
        print(f"\n--- Relation to RTH VWAP (parsed from text) ---")
        for group, items in vwap_groups.items():
            wins = [i for i in items if i['trade']['pnl_usd'] > 0]
            wr = len(wins) / len(items) * 100 if items else 0
            pnl = sum(i['trade']['pnl_usd'] for i in items)
            print(f"  {group:<12} | N={len(items):<3} | Wins={len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

        # 4. Day Type
        dt_groups = defaultdict(list)
        for m in dir_trades:
            t = m['trade']
            r = m['reasoning']
            dt = r.get('day_type', 'unknown')
            dt_groups[dt].append(m)
            
        print(f"\n--- Day Type (Macro Trend Context) ---")
        for group, items in sorted(dt_groups.items(), key=lambda x: len(x[1]), reverse=True):
            wins = [i for i in items if i['trade']['pnl_usd'] > 0]
            wr = len(wins) / len(items) * 100 if items else 0
            pnl = sum(i['trade']['pnl_usd'] for i in items)
            print(f"  {group:<18} | N={len(items):<3} | Wins={len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

        # 5. Multi-Feature Combinations (Find the "Slam Dunk" patterns)
        combo_groups = defaultdict(list)
        for m in dir_trades:
            t = m['trade']
            r = m['reasoning']
            close = r.get('bar_close')
            ibh = r.get('ib_high')
            ibl = r.get('ib_low')
            poc = r.get('poc')
            dt = r.get('day_type', 'unknown')
            
            text = str(r.get('fabio_reasoning', '')) + " " + str(r.get('market_narrative', '')) + " " + str(t.get('fabio_reasoning', ''))
            vwap_status = parse_vwap_status(text)
            
            # Formulate location features
            loc_ib = "above_ibh" if (close and ibh and close > ibh) else ("below_ibl" if (close and ibl and close < ibl) else "inside_ib")
            loc_vwap = vwap_status
            
            # Combine
            combo = (loc_ib, loc_vwap, dt)
            combo_groups[combo].append(m)
            
        print(f"\n--- Top Combinations (IB Position + VWAP Position + Day Type) ---")
        sorted_combos = sorted(combo_groups.items(), key=lambda x: len(x[1]), reverse=True)
        for combo, items in sorted_combos:
            if len(items) < 2:
                continue # Skip small samples
            wins = [i for i in items if i['trade']['pnl_usd'] > 0]
            wr = len(wins) / len(items) * 100 if items else 0
            pnl = sum(i['trade']['pnl_usd'] for i in items)
            print(f"  {str(combo):<55} | N={len(items):<3} | Wins={len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

if __name__ == "__main__":
    run_combo_analysis()
