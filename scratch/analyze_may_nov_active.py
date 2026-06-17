import json
import os
import re
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

def run_active_analysis():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    reasoning_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl"
    
    # 1. Load active reasoning log for May-Nov 2025
    reasoning_by_date_time = {}
    total_short_candidates = 0
    bypassed_shorts = 0
    evaluated_shorts = []
    
    with open(reasoning_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                date_str = data.get('date', '')
                # Filter May-Nov 2025
                if not (date_str >= '2025-05-01' and date_str <= '2025-11-30'):
                    continue
                
                bar_time_et = data.get('bar_time_et')
                if date_str and bar_time_et:
                    reasoning_by_date_time[(date_str, bar_time_et)] = data
                    
                # Track short candidates
                fd = data.get('fabio_direction')
                if fd == 'short':
                    total_short_candidates += 1
                    no_trade_r = data.get('no_trade_reason', '')
                    if 'short_trades_disabled' in str(no_trade_r) or 'disabled_by_risk_filter' in str(no_trade_r):
                        if data.get('fabio_entry') is None:
                            bypassed_shorts += 1
                        else:
                            evaluated_shorts.append(data)
            except Exception as e:
                pass
                
    print(f"Loaded {len(reasoning_by_date_time)} reasoning entries for May-Nov 2025.")
    print(f"Total short candidates evaluated or bypassed: {total_short_candidates}")
    print(f"  Bypassed (deterministic pre-filter, no LLM): {bypassed_shorts}")
    print(f"  Evaluated by Fabio but rejected by risk filter: {len(evaluated_shorts)}")

    # 2. Load active trades log for May-Nov 2025 and join
    matched_trades = []
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
                
                # Match reasoning
                matched_r = None
                if (date_str, et_time_str) in reasoning_by_date_time:
                    matched_r = reasoning_by_date_time[(date_str, et_time_str)]
                else:
                    # Find closest within 10 minutes on same day
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
                    matched_trades.append({
                        'trade': t,
                        'reasoning': matched_r
                    })
            except Exception as e:
                pass
                
    print(f"Matched {len(matched_trades)} active trades out of {len(matched_trades)} loaded.")
    
    # ── 3. ANALYZE ACTIVE LONG TRADES ──
    print("\n" + "="*80)
    print("ANALYSIS OF ACTIVE LONG TRADES (MAY-NOV 2025)")
    print("="*80)
    
    # A. Position relative to IB boundaries
    ib_groups = defaultdict(list)
    for m in matched_trades:
        t = m['trade']
        r = m['reasoning']
        close = r.get('bar_close')
        ibh = r.get('ib_high')
        ibl = r.get('ib_low')
        
        if close is None or ibh is None or ibl is None:
            loc = 'unknown'
        elif close > ibh:
            loc = 'above_ibh'
        elif close < ibl:
            loc = 'below_ibl'
        else:
            loc = 'inside_ib'
        ib_groups[loc].append(m)
        
    print("\n--- Position relative to Initial Balance (IB) ---")
    for group, items in ib_groups.items():
        wins = [i for i in items if i['trade']['pnl_usd'] > 0]
        wr = len(wins) / len(items) * 100 if items else 0
        pnl = sum(i['trade']['pnl_usd'] for i in items)
        print(f"  {group:<12} | N={len(items):<3} | Wins={len(wins):<3} | Losses={len(items)-len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

    # B. Position relative to VWAP (parsed from text)
    vwap_groups = defaultdict(list)
    for m in matched_trades:
        t = m['trade']
        r = m['reasoning']
        text = str(r.get('fabio_reasoning', '')) + " " + str(r.get('market_narrative', '')) + " " + str(t.get('fabio_reasoning', ''))
        vwap_status = parse_vwap_status(text)
        vwap_groups[vwap_status].append(m)
        
    print("\n--- Position relative to RTH VWAP (parsed from text) ---")
    for group, items in vwap_groups.items():
        wins = [i for i in items if i['trade']['pnl_usd'] > 0]
        wr = len(wins) / len(items) * 100 if items else 0
        pnl = sum(i['trade']['pnl_usd'] for i in items)
        print(f"  {group:<12} | N={len(items):<3} | Wins={len(wins):<3} | Losses={len(items)-len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

    # C. Day Type
    dt_groups = defaultdict(list)
    for m in matched_trades:
        r = m['reasoning']
        dt = r.get('day_type', 'unknown')
        dt_groups[dt].append(m)
        
    print("\n--- Day Type (Macro Trend Context) ---")
    for group, items in sorted(dt_groups.items(), key=lambda x: len(x[1]), reverse=True):
        wins = [i for i in items if i['trade']['pnl_usd'] > 0]
        wr = len(wins) / len(items) * 100 if items else 0
        pnl = sum(i['trade']['pnl_usd'] for i in items)
        print(f"  {group:<18} | N={len(items):<3} | Wins={len(wins):<3} | Losses={len(items)-len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

    # D. Stop Distance Bins
    stop_bins = defaultdict(list)
    for m in matched_trades:
        t = m['trade']
        entry = t.get('entry', 0.0)
        stop = t.get('stop', 0.0)
        dist = abs(entry - stop)
        if dist < 15:
            b_name = "< 15 pts"
        elif dist <= 25:
            b_name = "15-25 pts"
        elif dist <= 35:
            b_name = "25-35 pts"
        else:
            b_name = "> 35 pts"
        stop_bins[b_name].append(m)
        
    print("\n--- Stop Distance (Points) ---")
    for b_name in ["< 15 pts", "15-25 pts", "25-35 pts", "> 35 pts"]:
        items = stop_bins[b_name]
        wins = [i for i in items if i['trade']['pnl_usd'] > 0]
        wr = len(wins) / len(items) * 100 if items else 0
        pnl = sum(i['trade']['pnl_usd'] for i in items)
        print(f"  {b_name:<10} | N={len(items):<3} | Wins={len(wins):<3} | Losses={len(items)-len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

    # E. Top Combinations for LONG setups (Active Run Only!)
    combo_groups = defaultdict(list)
    for m in matched_trades:
        t = m['trade']
        r = m['reasoning']
        close = r.get('bar_close')
        ibh = r.get('ib_high')
        ibl = r.get('ib_low')
        dt = r.get('day_type', 'unknown')
        
        text = str(r.get('fabio_reasoning', '')) + " " + str(r.get('market_narrative', '')) + " " + str(t.get('fabio_reasoning', ''))
        vwap_status = parse_vwap_status(text)
        
        loc_ib = "above_ibh" if (close and ibh and close > ibh) else ("below_ibl" if (close and ibl and close < ibl) else "inside_ib")
        combo = (loc_ib, vwap_status, dt)
        combo_groups[combo].append(m)
        
    print("\n--- Top Combinations (IB Position + VWAP Position + Day Type) ---")
    sorted_combos = sorted(combo_groups.items(), key=lambda x: len(x[1]), reverse=True)
    for combo, items in sorted_combos:
        if len(items) < 2:
            continue
        wins = [i for i in items if i['trade']['pnl_usd'] > 0]
        wr = len(wins) / len(items) * 100 if items else 0
        pnl = sum(i['trade']['pnl_usd'] for i in items)
        print(f"  {str(combo):<50} | N={len(items):<3} | Wins={len(wins):<3} | WR={wr:>5.1f}% | PnL={pnl:>+8.2f}")

    # ── 4. AUDIT OF DISCARDED/BYPASSED SHORT CANDIDATES ──
    print("\n" + "="*80)
    print("AUDIT OF BYPASSED/DISCARDED SHORT CANDIDATES (MAY-NOV 2025)")
    print("="*80)
    
    # Let's inspect all reasoning entries in May-Nov where fabio_direction == 'short'
    # We want to understand what the context was when Fabio wanted to short.
    short_ib_groups = defaultdict(int)
    short_dt_groups = defaultdict(int)
    short_vwap_groups = defaultdict(int)
    
    with open(reasoning_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                date_str = data.get('date', '')
                if not (date_str >= '2025-05-01' and date_str <= '2025-11-30'):
                    continue
                if data.get('fabio_direction') != 'short':
                    continue
                    
                close = data.get('bar_close')
                ibh = data.get('ib_high')
                ibl = data.get('ib_low')
                dt = data.get('day_type', 'unknown')
                text = str(data.get('fabio_reasoning', '')) + " " + str(data.get('market_narrative', ''))
                
                # IB Location
                if close is None or ibh is None or ibl is None:
                    loc = 'unknown'
                elif close > ibh:
                    loc = 'above_ibh'
                elif close < ibl:
                    loc = 'below_ibl'
                else:
                    loc = 'inside_ib'
                short_ib_groups[loc] += 1
                
                # Day Type
                short_dt_groups[dt] += 1
                
                # VWAP
                vwap_status = parse_vwap_status(text)
                short_vwap_groups[vwap_status] += 1
            except Exception as e:
                pass
                
    print("\n--- Distribution of Discarded Shorts by IB Position ---")
    for group, count in short_ib_groups.items():
        print(f"  {group:<12}: {count:<4} ({count/total_short_candidates*100:.1f}%)")
        
    print("\n--- Distribution of Discarded Shorts by Day Type ---")
    for group, count in sorted(short_dt_groups.items(), key=lambda x: x[1], reverse=True):
        print(f"  {group:<18}: {count:<4} ({count/total_short_candidates*100:.1f}%)")

    print("\n--- Distribution of Discarded Shorts by VWAP Position (mentioned in text) ---")
    for group, count in short_vwap_groups.items():
        print(f"  {group:<12}: {count:<4} ({count/total_short_candidates*100:.1f}%)")

if __name__ == '__main__':
    run_active_analysis()
