import json
import sys
from pathlib import Path
import pytz
import pandas as pd
from datetime import datetime

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest-clean")
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
    return pnl_usd

def is_valid_climax_sequence(seq, pattern):
    steps = seq.get("steps", [])
    if not steps: return False
    
    cvd = steps[-1].get("session_cvd", 0)
    if abs(cvd) >= 1200:
        return False
        
    prices = [s["price"] for s in steps]
    vwap = sum(prices)/len(prices)
    if "long" in pattern and vwap < 15000:
        return False
        
    return True

def main():
    import scripts.time_session_optimizer_v2 as tso
    tso.cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    for d in tso.cached_dates:
        get_bars_for_date(d)

    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined_2025.json", encoding="utf-8") as f:
        seqs_combined_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2025.json", encoding="utf-8") as f:
        seqs_raw_2025 = json.load(f)
        
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        seqs_combined_2026 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2026.json", encoding="utf-8") as f:
        seqs_raw_2026 = json.load(f)

    raw_lookup = {}
    for s in seqs_raw_2025 + seqs_raw_2026:
        raw_lookup[(s["date"], s["end_time"])] = s
        
    seqs_combined = seqs_combined_2025 + seqs_combined_2026

    # Load V2 rules (we will use Caso B rules which are stricter)
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

    results = []

    for s in seqs_combined:
        vol = s['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)): continue
            
        date_str = s["date"]
        time_str = s["end_time"]
        pattern = s["seq_pattern"]
        
        raw_seq = raw_lookup.get((date_str, time_str))
        if not raw_seq: continue
            
        # CLIMAX FILTER
        if not is_valid_climax_sequence(raw_seq, pattern):
            continue
            
        # V2 SESSIONS FILTER (Caso A rules, but on filtered dataset)
        rule = v2_rules_a.get(pattern)
        if not rule: continue
            
        dt_obj = datetime.strptime(date_str, "%Y%m%d")
        day_of_week = dt_obj.strftime("%A")
        if day_of_week not in rule["days"]: continue
            
        h, m = int(time_str.split(':')[0]), int(time_str.split(':')[1])
        t_val = h * 60 + m
        if not (9*60+30 <= t_val < 16*60): continue
            
        session = get_session_label(t_val)
        if session not in rule["sessions"]: continue
            
        if rule.get("exclude_10am", False):
            if 9 * 60 + 55 <= t_val <= 10 * 60 + 5:
                continue
        
        atr = compute_5day_atr(date_str)
        setup_info = low_vol_setups.get(pattern) if atr < 200.0 else high_vol_setups.get(pattern)
        if not setup_info: continue
            
        direction = setup_info["direction"]
        tp = setup_info["tp"]
        sl = setup_info["sl"]
        
        bars = get_bars_for_date(date_str)
        if not bars: continue
            
        idx_T = -1
        for i, b in enumerate(bars):
            t_et = b.timestamp.astimezone(ET)
            if t_et.strftime("%H:%M") == time_str:
                idx_T = i
                break
                
        if idx_T == -1: continue
            
        # DELAY LOGIC: 1 min per trend_short, 0 per gli altri
        delay = 1 if pattern == "trend_short" else 0
        pnl = simulate_trade(bars, idx_T, direction, sl, tp, delay_minutes=delay)
        
        results.append({
            "pattern": pattern,
            "pnl": pnl
        })

    df = pd.DataFrame(results)
    
    print("\n=======================================================")
    print("TEST FINALE: CLIMAX FILTER + V2 SESSIONS + SHORT DELAY")
    print("=======================================================\n")
    
    tot_trades = len(df)
    tot_pnl = df["pnl"].sum()
    gw = sum(p for p in df["pnl"] if p > 0)
    gl = abs(sum(p for p in df["pnl"] if p < 0))
    pf_tot = gw/gl if gl > 0 else float('inf')
    
    print(f"TOTALE TRADE (18 mesi): {tot_trades} (Circa {tot_trades/1.5:.0f} all'anno)")
    print(f"PROFIT FACTOR GLOBALE:  {pf_tot:.2f}")
    print(f"NET PNL GLOBALE:        ${tot_pnl:.0f}\n")
    
    for pat in ["trend_long", "absorb_long", "trend_short", "absorb_short"]:
        sub = df[df["pattern"] == pat]
        if sub.empty: continue
            
        gw = sum(p for p in sub["pnl"] if p > 0)
        gl = abs(sum(p for p in sub["pnl"] if p < 0))
        pf = gw/gl if gl > 0 else float('inf')
        
        print(f"  {pat.upper():<13}: N={len(sub):<3} | PF={pf:.2f} | PnL=${sub['pnl'].sum():.0f}")

if __name__ == "__main__":
    main()

