import json
import sys
from pathlib import Path
import pytz
import pandas as pd
import datetime

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest")
from scripts.time_session_optimizer_v2 import CACHE_DIR, get_bars_for_date, compute_5day_atr, get_session_label

ET = pytz.timezone("America/New_York")

def simulate_trade(bars, entry_idx, direction, sl, tp, delay_minutes=0, base_contracts=3):
    start_idx = min(entry_idx + delay_minutes, len(bars) - 1)
    entry_price = bars[start_idx].close
    outcome = None
    pnl_pts = 0.0
    
    for i in range(start_idx + 1, len(bars)):
        bar = bars[i]
        t_et = bar.timestamp.astimezone(ET)
        
        if t_et.hour >= 16:
            outcome = "eod"
            pnl_pts = (bar.close - entry_price) if direction == "long" else (entry_price - bar.close)
            break
            
        if direction == "long":
            if bar.low <= entry_price - sl:
                pnl_pts = -sl; outcome = "loss"; break
            elif bar.high >= entry_price + tp + 0.25:
                pnl_pts = tp; outcome = "win"; break
        else:
            if bar.high >= entry_price + sl:
                pnl_pts = -sl; outcome = "loss"; break
            elif bar.low <= entry_price - tp - 0.25:
                pnl_pts = tp; outcome = "win"; break
                
    if outcome is None:
        pnl_pts = (bars[-1].close - entry_price) if direction == "long" else (entry_price - bars[-1].close)
        
    pnl_usd = ((pnl_pts - 1.5) * 2.0 - 0.50) * base_contracts
    return pnl_usd, outcome

def main():
    import scripts.time_session_optimizer_v2 as tso
    tso.cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    for d in tso.cached_dates: get_bars_for_date(d)

    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined_2025.json", encoding="utf-8") as f:
        seqs_combined_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        seqs_combined_2026 = json.load(f)
        
    seqs_combined = seqs_combined_2025 + seqs_combined_2026

    with open("scripts/time_session_rules_v2.json", "r", encoding="utf-8") as f:
        v2_rules_a = json.load(f)["v2_case_a_coarse_sessions"]["rules"]

    low_vol_setups = {
        "trend_long": {"direction": "long", "sl": 39.0, "tp": 120.0},
        "absorb_long": {"direction": "long", "sl": 49.0, "tp": 37.0},
        "trend_short": {"direction": "short", "sl": 46.0, "tp": 120.0},
        "absorb_short": {"direction": "short", "sl": 49.0, "tp": 114.0}
    }
    high_vol_setups = {
        "trend_long": {"direction": "long", "sl": 22.0, "tp": 113.0},
        "absorb_long": {"direction": "long", "sl": 50.0, "tp": 115.0},
        "trend_short": {"direction": "short", "sl": 48.0, "tp": 113.0},
        "absorb_short": {"direction": "short", "sl": 34.0, "tp": 35.0}
    }

    base_results = []
    filtered_results = []

    for s in seqs_combined:
        vol = s['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)): continue
            
        date_str = s["date"]
        time_str = s["end_time"]
        pattern = s["seq_pattern"]
        
        rule = v2_rules_a.get(pattern)
        if not rule: continue
            
        dt_obj = datetime.datetime.strptime(date_str, "%Y%m%d")
        if dt_obj.strftime("%A") not in rule["days"]: continue
            
        h, m = int(time_str.split(':')[0]), int(time_str.split(':')[1])
        t_val = h * 60 + m
        if not (9*60+30 <= t_val < 16*60): continue
        if get_session_label(t_val) not in rule["sessions"]: continue
        if rule.get("exclude_10am", False) and (9*60+55 <= t_val <= 10*60+5): continue
        
        atr = compute_5day_atr(date_str)
        setup_info = low_vol_setups.get(pattern) if atr < 200.0 else high_vol_setups.get(pattern)
        if not setup_info: continue
            
        direction = setup_info["direction"]
        bars = get_bars_for_date(date_str)
        if not bars: continue
            
        idx_T = -1
        for i, b in enumerate(bars):
            if b.timestamp.astimezone(ET).strftime("%H:%M") == time_str:
                idx_T = i; break
        if idx_T < 10: continue
            
        pnl_base, out_base = simulate_trade(bars, idx_T, direction, setup_info["sl"], setup_info["tp"], delay_minutes=0)
        base_results.append({"pattern": pattern, "pnl": pnl_base, "out": out_base})
        
        prior_bars = bars[idx_T-10 : idx_T]
        price_change = prior_bars[-1].close - prior_bars[0].open
        
        valid_context = False
        if pattern == "absorb_long" and price_change >= -10: valid_context = True 
        elif pattern == "trend_long" and price_change > 0: valid_context = True 
        elif pattern == "absorb_short" and price_change <= 10: valid_context = True 
        elif pattern == "trend_short" and price_change < 0: valid_context = True 
            
        if valid_context:
            delay = 1 if pattern == "trend_short" else 0
            pnl_filt, out_filt = simulate_trade(bars, idx_T, direction, setup_info["sl"], setup_info["tp"], delay_minutes=delay)
            filtered_results.append({"pattern": pattern, "pnl": pnl_filt, "out": out_filt})

    def print_stats(res, title):
        df = pd.DataFrame(res)
        gw = sum(p for p in df["pnl"] if p > 0)
        gl = abs(sum(p for p in df["pnl"] if p < 0))
        pf = gw/gl if gl > 0 else float('inf')
        wr = (df["out"] == "win").mean() * 100
        print(f"--- {title} ---")
        print(f"Trade totali: {len(df)}")
        print(f"Profit Factor: {pf:.2f}")
        print(f"Win Rate: {wr:.1f}%")
        print(f"Net PnL: ${df['pnl'].sum():.0f}\n")
        
    print_stats(base_results, "V2 CASO A BASELINE (Nessun filtro contesto, Ingresso Immediato)")
    print_stats(filtered_results, "V2 CASO A + CONTEXT FILTER + DELAY SHORT")

if __name__ == "__main__": main()
