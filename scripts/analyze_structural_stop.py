import json
import sys
from pathlib import Path
import pytz
import pandas as pd
import numpy as np

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest-clean")
from scripts.time_session_optimizer_v2 import CACHE_DIR, get_bars_for_date, compute_5day_atr

ET = pytz.timezone("America/New_York")

def simulate_trade_structural(bars, entry_idx, direction, struct_sl_price, tp_pts, base_contracts=3):
    entry_price = bars[entry_idx].close
    outcome = None
    pnl_pts = 0.0
    
    # Calculate SL points just for logging if needed
    sl_dist = abs(entry_price - struct_sl_price)
    
    for i in range(entry_idx + 1, len(bars)):
        bar = bars[i]
        t_et = bar.timestamp.astimezone(ET)
        
        if t_et.hour >= 16:
            outcome = "eod"
            pnl_pts = (bar.close - entry_price) if direction == "long" else (entry_price - bar.close)
            break
            
        if direction == "long":
            if bar.low <= struct_sl_price:
                pnl_pts = -(entry_price - struct_sl_price); outcome = "loss"; break
            elif bar.high >= entry_price + tp_pts + 0.25:
                pnl_pts = tp_pts; outcome = "win"; break
        else:
            if bar.high >= struct_sl_price:
                pnl_pts = -(struct_sl_price - entry_price); outcome = "loss"; break
            elif bar.low <= entry_price - tp_pts - 0.25:
                pnl_pts = tp_pts; outcome = "win"; break
                
    if outcome is None:
        pnl_pts = (bars[-1].close - entry_price) if direction == "long" else (entry_price - bars[-1].close)
        
    pnl_usd = ((pnl_pts - 1.5) * 2.0 - 0.50) * base_contracts
    return pnl_usd, outcome, sl_dist

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

    low_vol_setups = {
        "trend_long": {"direction": "long", "tp": 120.0},
        "absorb_long": {"direction": "long", "tp": 37.0},
        "trend_short": {"direction": "short", "tp": 120.0},
        "absorb_short": {"direction": "short", "tp": 114.0}
    }
    high_vol_setups = {
        "trend_long": {"direction": "long", "tp": 113.0},
        "absorb_long": {"direction": "long", "tp": 115.0},
        "trend_short": {"direction": "short", "tp": 113.0},
        "absorb_short": {"direction": "short", "tp": 35.0}
    }

    results = []

    for s in seqs_combined:
        vol = s['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)): continue
            
        date_str = s["date"]
        time_str = s["end_time"]
        pattern = s["seq_pattern"]
        
        atr = compute_5day_atr(date_str)
        setup_info = low_vol_setups.get(pattern) if atr < 200.0 else high_vol_setups.get(pattern)
        if not setup_info: continue
            
        direction = setup_info["direction"]
        tp = setup_info["tp"]
        
        raw_seq = raw_lookup.get((date_str, time_str))
        if not raw_seq or not raw_seq.get("steps"): continue
            
        # Trova il livello del PRIMO step istituzionale
        first_step_price = raw_seq["steps"][0]["price"]
        seq_low = first_step_price
        seq_high = first_step_price
        
        # SL Strutturale: Dietro il minimo/massimo istituzionale + 2.5 punti di buffer (10 tick)
        if direction == "long":
            struct_sl_price = seq_low - 2.5
        else:
            struct_sl_price = seq_high + 2.5
            
        bars = get_bars_for_date(date_str)
        if not bars: continue
            
        idx_T = -1
        for i, b in enumerate(bars):
            t_et = b.timestamp.astimezone(ET)
            if t_et.strftime("%H:%M") == time_str:
                idx_T = i
                break
                
        if idx_T == -1: continue
            
        pnl, outcome, sl_dist = simulate_trade_structural(bars, idx_T, direction, struct_sl_price, tp)
        
        # Filtro: se lo stop loss strutturale è troppo largo (> 80 punti), non trade (invalida RR)
        if sl_dist > 80:
            continue
            
        results.append({
            "pattern": pattern,
            "pnl": pnl,
            "outcome": outcome,
            "sl_dist": sl_dist
        })

    df = pd.DataFrame(results)
    
    print("\n=======================================================")
    print("ANALISI STOP LOSS STRUTTURALE (Dietro Livello Istituzionale)")
    print("=======================================================\n")
    
    for pat in ["trend_long", "absorb_long", "trend_short", "absorb_short"]:
        sub = df[df["pattern"] == pat]
        if sub.empty: continue
            
        gw = sum(p for p in sub["pnl"] if p > 0)
        gl = abs(sum(p for p in sub["pnl"] if p < 0))
        pf = gw/gl if gl > 0 else float('inf')
        wr = (sub["outcome"] == "win").mean() * 100
        avg_sl = sub["sl_dist"].mean()
        
        print(f"--- SETUP: {pat.upper()} (N={len(sub)}) ---")
        print(f"  Distanza SL media (strutturale): {avg_sl:.1f} pt")
        print(f"  Profit Factor: {pf:.2f}")
        print(f"  Win Rate:      {wr:.1f}%")
        print(f"  Net PnL:       ${sub['pnl'].sum():.0f}\n")

if __name__ == "__main__":
    main()

