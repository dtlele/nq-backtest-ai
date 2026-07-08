import json
import sys
from pathlib import Path
import pytz
import pandas as pd

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest")
from scripts.time_session_optimizer_v2 import CACHE_DIR, get_bars_for_date, compute_5day_atr

ET = pytz.timezone("America/New_York")

def simulate_sweep_analysis(bars, entry_idx, direction, struct_sl_price, fixed_sl_pts, tp_pts):
    entry_price = bars[entry_idx].close
    outcome_struct = None
    outcome_fixed = None
    mae = 0.0 
    
    for i in range(entry_idx + 1, len(bars)):
        bar = bars[i]
        t_et = bar.timestamp.astimezone(ET)
        
        if direction == "long":
            current_mae = entry_price - bar.low
            if current_mae > mae: mae = current_mae
                
            if outcome_struct is None and bar.low <= struct_sl_price:
                outcome_struct = "loss"
            if outcome_fixed is None and bar.low <= entry_price - fixed_sl_pts:
                outcome_fixed = "loss"
                
            if bar.high >= entry_price + tp_pts + 0.25:
                if outcome_struct is None: outcome_struct = "win"
                if outcome_fixed is None: outcome_fixed = "win"
                break
        else:
            current_mae = bar.high - entry_price
            if current_mae > mae: mae = current_mae
                
            if outcome_struct is None and bar.high >= struct_sl_price:
                outcome_struct = "loss"
            if outcome_fixed is None and bar.high >= entry_price + fixed_sl_pts:
                outcome_fixed = "loss"
                
            if bar.low <= entry_price - tp_pts - 0.25:
                if outcome_struct is None: outcome_struct = "win"
                if outcome_fixed is None: outcome_fixed = "win"
                break
                
        if t_et.hour >= 16:
            if outcome_struct is None: outcome_struct = "eod"
            if outcome_fixed is None: outcome_fixed = "eod"
            break
            
    if outcome_struct is None: outcome_struct = "eod"
    if outcome_fixed is None: outcome_fixed = "eod"
    
    is_sweep = (outcome_struct == "loss" and outcome_fixed == "win")
    
    sweep_depth = 0.0
    if is_sweep:
        if direction == "long":
            sweep_depth = struct_sl_price - (entry_price - mae)
        else:
            sweep_depth = (entry_price + mae) - struct_sl_price
            
    return outcome_struct, outcome_fixed, is_sweep, sweep_depth

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
        
        atr = compute_5day_atr(date_str)
        setup_info = low_vol_setups.get(pattern) if atr < 200.0 else high_vol_setups.get(pattern)
        if not setup_info: continue
            
        direction = setup_info["direction"]
        tp = setup_info["tp"]
        fixed_sl = setup_info["sl"]
        
        raw_seq = raw_lookup.get((date_str, time_str))
        if not raw_seq or not raw_seq.get("steps"): continue
            
        first_step_price = raw_seq["steps"][0]["price"]
        
        if direction == "long":
            struct_sl_price = first_step_price - 2.5
        else:
            struct_sl_price = first_step_price + 2.5
            
        bars = get_bars_for_date(date_str)
        if not bars: continue
            
        idx_T = -1
        for i, b in enumerate(bars):
            t_et = b.timestamp.astimezone(ET)
            if t_et.strftime("%H:%M") == time_str:
                idx_T = i
                break
                
        if idx_T == -1: continue
            
        out_struct, out_fixed, is_sweep, sweep_depth = simulate_sweep_analysis(
            bars, idx_T, direction, struct_sl_price, fixed_sl, tp
        )
        
        results.append({
            "pattern": pattern,
            "out_struct": out_struct,
            "out_fixed": out_fixed,
            "is_sweep": is_sweep,
            "sweep_depth": sweep_depth
        })

    df = pd.DataFrame(results)
    
    print("\n=======================================================")
    print("ANALISI CACCIA AGLI STOP (Liquidity Sweeps)")
    print("=======================================================\n")
    
    for pat in ["trend_long", "absorb_long", "trend_short", "absorb_short"]:
        sub = df[df["pattern"] == pat]
        if sub.empty: continue
            
        total_trades = len(sub)
        sweeps = sub[sub["is_sweep"] == True]
        num_sweeps = len(sweeps)
        sweep_pct = (num_sweeps / total_trades) * 100 if total_trades > 0 else 0
        
        avg_depth = sweeps["sweep_depth"].mean() if num_sweeps > 0 else 0
        max_depth = sweeps["sweep_depth"].max() if num_sweeps > 0 else 0
        
        print(f"--- SETUP: {pat.upper()} (Campione: {total_trades}) ---")
        print(f"  Volte in cui il NQ ha spazzato lo SL Strutturale ed e' ripartito in Gain: {num_sweeps} ({sweep_pct:.1f}%)")
        if num_sweeps > 0:
            print(f"  Profondita' MEDIA della caccia allo stop: {avg_depth:.1f} punti oltre l'istituzionale")
            print(f"  Profondita' MAX della caccia allo stop:   {max_depth:.1f} punti oltre l'istituzionale")
        print()

if __name__ == "__main__":
    main()
