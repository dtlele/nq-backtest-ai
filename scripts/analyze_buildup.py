import json
import sys
from pathlib import Path
import pytz
import pandas as pd
import numpy as np

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest")
from scripts.time_session_optimizer_v2 import CACHE_DIR, get_bars_for_date, precompute_raw_trades

ET = pytz.timezone("America/New_York")

def load_v2_rules():
    with open("scripts/time_session_rules_v2.json", "r", encoding="utf-8") as f:
        return json.load(f)["v2_case_a_coarse_sessions"]["rules"]

def filter_v2_case_a(trades):
    rules = load_v2_rules()
    filtered = []
    for t in trades:
        rule = rules.get(t["pattern"])
        if not rule: continue
        if t["day_of_week"] not in rule["days"]: continue
        if t["session"] not in rule["sessions"]: continue
        
        h, m = map(int, t["time_str"].split(':'))
        tv = h*60 + m
        if rule.get("exclude_10am", False):
            if 9*60+55 <= tv <= 10*60+5:
                continue
        filtered.append(t)
    return filtered

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
    v2_trades = filter_v2_case_a(trades_base)
    
    buildup_stats = []
    
    for t in v2_trades:
        date_str = t["date"]
        time_str = t["time_str"]
        bars = get_bars_for_date(date_str)
        if not bars: continue
            
        idx_T = -1
        for i, b in enumerate(bars):
            t_et = b.timestamp.astimezone(ET)
            if t_et.strftime("%H:%M") == time_str:
                idx_T = i
                break
                
        if idx_T < 10: continue # Need at least 10 prior bars
        
        # Estrarre le 10 candele PRIMA del trigger (escludiamo la candela di trigger per vedere cosa lo prepara)
        prior_bars = bars[idx_T-10 : idx_T]
        
        # Calcolo direzionalita'
        start_price = prior_bars[0].open
        end_price = prior_bars[-1].close
        price_change = end_price - start_price
        
        # Calcolo range totale
        high_10 = max(b.high for b in prior_bars)
        low_10 = min(b.low for b in prior_bars)
        range_10 = high_10 - low_10
        
        buildup_stats.append({
            "pattern": t["pattern"],
            "price_change": price_change,
            "range_10m": range_10
        })

    df = pd.DataFrame(buildup_stats)
    
    print("\n=======================================================")
    print("ANALISI BUILDUP (Cosa succede nei 10 min precedenti?)")
    print("=======================================================\n")
    
    for pat in ["trend_long", "absorb_long", "trend_short", "absorb_short"]:
        sub = df[df["pattern"] == pat]
        if sub.empty: continue
            
        avg_change = sub["price_change"].mean()
        avg_range = sub["range_10m"].mean()
        
        # Quante volte e' contro la direzione del setup? (Es. Absorb Long dovrebbe avere price_change < 0 prima)
        if "long" in pat and "absorb" in pat:
            contro = (sub["price_change"] < 0).mean() * 100
        elif "short" in pat and "absorb" in pat:
            contro = (sub["price_change"] > 0).mean() * 100
        elif "long" in pat and "trend" in pat:
            contro = (sub["price_change"] > 0).mean() * 100
        else:
            contro = (sub["price_change"] < 0).mean() * 100
            
        print(f"--- {pat.upper()} ---")
        print(f"  Range di escursione medio (10 min): {avg_range:.1f} punti")
        print(f"  Direzionalita' media (10 min): {avg_change:+.1f} punti")
        print(f"  Il buildup e' stato coerente con l'anomalia il {contro:.1f}% delle volte\n")

if __name__ == "__main__": main()
