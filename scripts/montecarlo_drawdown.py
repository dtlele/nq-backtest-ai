import json
import sys
from pathlib import Path
import pytz
import pandas as pd
import numpy as np

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest")
from scripts.time_session_optimizer_v2 import CACHE_DIR, get_bars_for_date, precompute_raw_trades, get_session_label

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
    pnls = [t["pnl_usd"] for t in v2_trades]

    print(f"Trades trovati (V2 Caso A): {len(pnls)}")
    
    # Montecarlo
    N_SIM = 10000
    max_dds = []
    
    for _ in range(N_SIM):
        shuffled = np.random.permutation(pnls)
        cum_pnl = np.cumsum(shuffled)
        peaks = np.maximum.accumulate(cum_pnl)
        drawdowns = peaks - cum_pnl
        max_dds.append(np.max(drawdowns))

    max_dds = np.array(max_dds)
    p50 = np.percentile(max_dds, 50)
    p95 = np.percentile(max_dds, 95)
    p99 = np.percentile(max_dds, 99)
    prob_fail = np.mean(max_dds >= 2500.0) * 100

    print("\n=======================================================")
    print("MONTECARLO STRESS TEST (10.000 Simulazioni randomizzate)")
    print("=======================================================\n")
    print(f"Drawdown Mediano (50% dei casi): ${p50:.2f}")
    print(f"Drawdown 95° Percentile:         ${p95:.2f}")
    print(f"Drawdown 99° Percentile:         ${p99:.2f} (Peggiore dei casi)")
    print(f"\nRischio Prop Firm FundedNext ($2.500 Max Drawdown):")
    print(f"Probabilita' matematica di bruciare il conto: {prob_fail:.2f}%")

if __name__ == "__main__": main()
