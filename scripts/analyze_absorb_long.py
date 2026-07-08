import json
import sys
from pathlib import Path
import pytz
import pandas as pd
import numpy as np

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest")

# Import logic from the v2 optimizer
from scripts.time_session_optimizer_v2 import (
    CACHE_DIR, get_bars_for_date, cached_dates, 
    precompute_raw_trades, SESSION_NAMES, DAYS_OF_WEEK
)

def main():
    global cached_dates
    # Quickly setup cache dates
    import scripts.time_session_optimizer_v2 as tso
    tso.cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined_2025.json", encoding="utf-8") as f:
        seqs_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2025.json", encoding="utf-8") as f:
        raw_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        seqs_2026 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2026.json", encoding="utf-8") as f:
        raw_2026 = json.load(f)

    raw_lookup = {}
    for s in raw_2025 + raw_2026:
        raw_lookup[(s["date"], s["end_time"])] = s

    seqs_combined = sorted(seqs_2025 + seqs_2026, key=lambda x: (x["date"], x["end_time"]))

    trades_baseline = precompute_raw_trades(seqs_combined, raw_lookup, filtered_mode=False)
    
    absorb_long = [t for t in trades_baseline if t["pattern"] == "absorb_long"]
    df = pd.DataFrame(absorb_long)
    
    print("=========================================================")
    print("   ANALISI PROFONDA ABSORB_LONG (BASELINE)               ")
    print("=========================================================\n")
    
    # Matrice Giorno x Sessione (PF)
    print(">>> Profit Factor (Matrice Giorno x Sessione) <<<")
    matrix_pf = pd.DataFrame(index=DAYS_OF_WEEK, columns=SESSION_NAMES)
    matrix_n = pd.DataFrame(index=DAYS_OF_WEEK, columns=SESSION_NAMES)
    matrix_pnl = pd.DataFrame(index=DAYS_OF_WEEK, columns=SESSION_NAMES)
    
    for day in DAYS_OF_WEEK:
        for sess in SESSION_NAMES:
            sub = df[(df["day_of_week"] == day) & (df["session"] == sess)]
            if len(sub) == 0:
                matrix_pf.loc[day, sess] = "-"
                matrix_n.loc[day, sess] = 0
                matrix_pnl.loc[day, sess] = 0
                continue
            
            gw = sum(p for p in sub["pnl_usd"] if p > 0)
            gl = abs(sum(p for p in sub["pnl_usd"] if p < 0))
            pf = gw/gl if gl > 0 else float('inf')
            
            matrix_pf.loc[day, sess] = f"{pf:.2f}"
            matrix_n.loc[day, sess] = len(sub)
            matrix_pnl.loc[day, sess] = f"${sub['pnl_usd'].sum():.0f}"
            
    print("\n[PROFIT FACTOR]")
    print(matrix_pf)
    print("\n[NUMERO DI TRADE]")
    print(matrix_n)
    print("\n[NET PNL]")
    print(matrix_pnl)
    
    # Impatto 10:00 AM solo per i giorni buoni
    print("\n\n>>> Impatto delle 10:00 AM (Esclusione 09:55 - 10:05) <<<")
    
    # Test escludendo vs includendo
    for day in ["Tuesday", "Wednesday"]:
        sub = df[(df["day_of_week"] == day) & (df["session"].isin(["open", "mid"]))]
        
        # Inclusi
        gw1 = sum(p for p in sub["pnl_usd"] if p > 0)
        gl1 = abs(sum(p for p in sub["pnl_usd"] if p < 0))
        pf1 = gw1/gl1 if gl1 > 0 else float('inf')
        
        # Esclusi
        sub_excl = []
        for _, t in sub.iterrows():
            h, m = map(int, t["time_str"].split(':'))
            tv = h * 60 + m
            if not (9*60+55 <= tv <= 10*60+5):
                sub_excl.append(t)
        
        gw2 = sum(t["pnl_usd"] for t in sub_excl if t["pnl_usd"] > 0)
        gl2 = abs(sum(t["pnl_usd"] for t in sub_excl if t["pnl_usd"] < 0))
        pf2 = gw2/gl2 if gl2 > 0 else float('inf')
        
        print(f"\n{day} (Open+Mid):")
        print(f"  Tenendo le 10:00: N={len(sub)}, PF={pf1:.2f}, PnL=${sub['pnl_usd'].sum():.0f}")
        print(f"  Escludendo le 10:00: N={len(sub_excl)}, PF={pf2:.2f}, PnL=${sum(t['pnl_usd'] for t in sub_excl):.0f}")

if __name__ == "__main__":
    main()
