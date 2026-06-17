import json
import os
import glob
from datetime import datetime
import pytz

TRADES_FILES = [
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_ds_feb_no_money_mgmt.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_ds_feb_restrictive.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_ds_feb_wide_stops.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_jan2025.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_june.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_ds_feb_dynamic_mgmt_part1_no_apm.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_gemini_feb_week1.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_pre_fix.jsonl",
]

def find_bearish_longs():
    memory_dir = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory"
    
    # Let's load all reasoning from all reasoning files to have a massive database
    reasoning_by_date = {}
    reasoning_files = glob.glob(os.path.join(memory_dir, "*reasoning_log*.jsonl*"))
    
    for rf in reasoning_files:
        try:
            with open(rf, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        date = data.get('date')
                        bar_time_et = data.get('bar_time_et')
                        if date and bar_time_et:
                            if date not in reasoning_by_date:
                                reasoning_by_date[date] = {}
                            reasoning_by_date[date][bar_time_et] = data
                    except:
                        pass
        except Exception as e:
            print(f"Error loading {rf}: {e}")

    print(f"Loaded reasoning data for {len(reasoning_by_date)} dates.")
    print("=== AUDIT OF LONG TRADES IN BEARISH STRUCTURES (ALL HISTORICAL RUNS) ===")
    print(f"{'File':<30} | {'Date':<10} | {'ET':<5} | {'PnL':<8} | {'IBL':<8} | {'Close':<8} | {'Day Type':<12}")
    print("-" * 100)
    
    for tf in TRADES_FILES:
        if not os.path.exists(tf):
            continue
        with open(tf, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    t = json.loads(line)
                    if t.get('direction') != 'long':
                        continue
                    date = t.get('date')
                    entry_time_str = t.get('entry_time')
                    pnl = t.get('pnl_usd', 0.0)
                    
                    # Match nearest reasoning
                    dt = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
                    dt_et = dt.astimezone(pytz.timezone("America/New_York"))
                    h_trade, m_trade = dt_et.hour, dt_et.minute
                    
                    day_reasonings = reasoning_by_date.get(date, {})
                    matched_r = None
                    best_diff = 999
                    for r_time_str, r_data in day_reasonings.items():
                        try:
                            h_r, m_r = map(int, r_time_str.split(':'))
                            diff = abs((h_trade * 60 + m_trade) - (h_r * 60 + m_r))
                            if diff < best_diff and diff <= 10:
                                best_diff = diff
                                matched_r = r_data
                        except:
                            pass
                    
                    if matched_r:
                        close = matched_r.get('bar_close')
                        ibh = matched_r.get('ib_high')
                        ibl = matched_r.get('ib_low')
                        dt_type = matched_r.get('day_type')
                        
                        is_below_ibl = (close is not None and ibl is not None and close < ibl)
                        is_bearish_day = (dt_type == 'trend_down' or 'down' in str(dt_type).lower())
                        
                        if is_below_ibl or is_bearish_day:
                            fname = os.path.basename(tf)
                            print(f"{fname:<30} | {date:<10} | {dt_et.strftime('%H:%M'):<5} | {pnl:>+8.2f} | {ibl:>8.2f} | {close:>8.2f} | {dt_type:<12}")
                except Exception as e:
                    pass

if __name__ == '__main__':
    find_bearish_longs()
