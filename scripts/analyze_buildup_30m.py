import json
import sys
from pathlib import Path
import pytz
import pandas as pd

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest")
from scripts.time_session_optimizer_v2 import CACHE_DIR, get_bars_for_date, precompute_raw_trades

ET = pytz.timezone("America/New_York")

def main():
    import scripts.time_session_optimizer_v2 as tso
    tso.cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    for d in tso.cached_dates: get_bars_for_date(d)

    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined_2025.json", encoding="utf-8") as f:
        seqs_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        seqs_2026 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2025.json", encoding="utf-8") as f:
        raw_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2026.json", encoding="utf-8") as f:
        raw_2026 = json.load(f)

    raw_lookup = {}
    for s in raw_2025 + raw_2026: raw_lookup[(s["date"], s["end_time"])] = s
    seqs_combined = sorted(seqs_2025 + seqs_2026, key=lambda x: (x["date"], x["end_time"]))

    trades_base = precompute_raw_trades(seqs_combined, raw_lookup, filtered_mode=False)
    
    with open("scripts/time_session_rules_v2.json", "r", encoding="utf-8") as f:
        v2_rules = json.load(f)["v2_case_a_coarse_sessions"]["rules"]
        
    v2_trades = []
    for t in trades_base:
        r = v2_rules.get(t["pattern"])
        if not r: continue
        if t["day_of_week"] not in r["days"]: continue
        if t["session"] not in r["sessions"]: continue
        if r.get("exclude_10am", False):
            h, m = map(int, t["time_str"].split(':'))
            tv = h*60+m
            if 9*60+55 <= tv <= 10*60+5: continue
        v2_trades.append(t)
        
    stats = []
    for t in v2_trades:
        bars = get_bars_for_date(t["date"])
        if not bars: continue
            
        idx_T = -1
        for i, b in enumerate(bars):
            if b.timestamp.astimezone(ET).strftime("%H:%M") == t["time_str"]:
                idx_T = i; break
                
        if idx_T < 30: continue
            
        prior_30 = bars[idx_T-30 : idx_T]
        high_30 = max(b.high for b in prior_30)
        low_30 = min(b.low for b in prior_30)
        range_30 = high_30 - low_30
        
        sma_30 = sum(b.close for b in prior_30) / 30.0
        entry_price = bars[idx_T].close
        dist_sma = entry_price - sma_30
        
        stats.append({
            "pattern": t["pattern"],
            "range_30": range_30,
            "dist_sma": dist_sma,
            "outcome": "win" if t["pnl_usd"] > 0 else "loss"
        })

    df = pd.DataFrame(stats)
    
    print("\n=======================================================")
    print("ANALISI 30 MINUTI PRIMA (Elastico e Compressione)")
    print("=======================================================\n")
    
    for pat in ["trend_long", "absorb_long", "trend_short", "absorb_short"]:
        sub = df[df["pattern"] == pat]
        if sub.empty: continue
            
        wins = sub[sub["outcome"] == "win"]
        losses = sub[sub["outcome"] == "loss"]
        
        print(f"--- {pat.upper()} ---")
        w_rng = wins['range_30'].mean() if len(wins) else 0
        l_rng = losses['range_30'].mean() if len(losses) else 0
        w_dist = wins['dist_sma'].mean() if len(wins) else 0
        l_dist = losses['dist_sma'].mean() if len(losses) else 0
        
        print(f"  Range Medio a 30m dei TRADE VINCENTI:  {w_rng:.1f} pt")
        print(f"  Range Medio a 30m dei TRADE PERDENTI:  {l_rng:.1f} pt")
        
        print(f"  Distanza dalla Media a 30m (VINCENTI): {w_dist:+.1f} pt")
        print(f"  Distanza dalla Media a 30m (PERDENTI): {l_dist:+.1f} pt\n")

if __name__ == "__main__": main()
