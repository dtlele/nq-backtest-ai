import json
import sys
from pathlib import Path
import pytz
import pandas as pd
import numpy as np

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest-clean")
from scripts.time_session_optimizer_v2 import CACHE_DIR, get_bars_for_date, compute_5day_atr

ET = pytz.timezone("America/New_York")

def simulate_trade(bars, entry_idx, direction, sl, tp, base_contracts=3):
    entry_price = bars[entry_idx].close
    outcome = None
    pnl_pts = 0.0
    
    for i in range(entry_idx + 1, len(bars)):
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

def main():
    import scripts.time_session_optimizer_v2 as tso
    tso.cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    for d in tso.cached_dates:
        get_bars_for_date(d)
        
    print("Memoria OHLC caricata.")

    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined_2025.json", encoding="utf-8") as f:
        seqs_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        seqs_2026 = json.load(f)
        
    seqs_combined = seqs_2025 + seqs_2026

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
        sl = setup_info["sl"]
        tp = setup_info["tp"]
        
        bars = get_bars_for_date(date_str)
        if not bars: continue
            
        idx_T = -1
        for i, b in enumerate(bars):
            t_et = b.timestamp.astimezone(ET)
            if t_et.strftime("%H:%M") == time_str:
                idx_T = i
                break
                
        if idx_T == -1 or idx_T + 1 >= len(bars): continue
            
        bar_T = bars[idx_T]
        bar_T1 = bars[idx_T + 1] # La "Candela Dopo"
        
        t1_is_green = bar_T1.close >= bar_T1.open
        t1_direction = "long" if t1_is_green else "short"
        t1_range = bar_T1.high - bar_T1.low
        t1_body = abs(bar_T1.close - bar_T1.open)
        
        # Confirms strategy?
        t1_confirms = (direction == "long" and t1_is_green) or (direction == "short" and not t1_is_green)
        
        # Scenari
        pnl_base = simulate_trade(bars, idx_T, direction, sl, tp)
        pnl_t1_delay = simulate_trade(bars, idx_T + 1, direction, sl, tp)
        pnl_t1_confirm = pnl_t1_delay if t1_confirms else 0.0 # Se non conferma, non entriamo (PnL 0)
        
        results.append({
            "pattern": pattern,
            "direction": direction,
            "t1_confirms": t1_confirms,
            "t1_range": t1_range,
            "t1_body": t1_body,
            "pnl_base": pnl_base,
            "pnl_t1_delay": pnl_t1_delay,
            "pnl_t1_confirm": pnl_t1_confirm,
            "executed_confirm": 1 if t1_confirms else 0
        })

    df = pd.DataFrame(results)
    
    print("\n=======================================================")
    print("ANALISI DELLA 'CANDELA DOPO' (T+1)")
    print("=======================================================\n")
    
    for pat in ["trend_long", "absorb_long", "trend_short", "absorb_short"]:
        sub = df[df["pattern"] == pat]
        if sub.empty: continue
            
        print(f"--- SETUP: {pat.upper()} (Campione: {len(sub)} sequenze) ---")
        
        # Statistiche candela T+1
        conf_rate = sub['t1_confirms'].mean() * 100
        avg_range = sub['t1_range'].mean()
        avg_body = sub['t1_body'].mean()
        
        print(f"  [Candela T+1] Conferma la direzione: {conf_rate:.1f}% delle volte")
        print(f"  [Candela T+1] Range medio: {avg_range:.2f} pt | Body medio: {avg_body:.2f} pt")
        
        # Scenario 1: Baseline (Entrata Immediata a T)
        gw_base = sum(p for p in sub["pnl_base"] if p > 0)
        gl_base = abs(sum(p for p in sub["pnl_base"] if p < 0))
        pf_base = gw_base/gl_base if gl_base > 0 else float('inf')
        
        # Scenario 2: Entrata a T+1 incondizionata
        gw_dly = sum(p for p in sub["pnl_t1_delay"] if p > 0)
        gl_dly = abs(sum(p for p in sub["pnl_t1_delay"] if p < 0))
        pf_dly = gw_dly/gl_dly if gl_dly > 0 else float('inf')
        
        # Scenario 3: Entrata a T+1 SOLO SE CONFERMA
        sub_exec = sub[sub["t1_confirms"] == True]
        gw_conf = sum(p for p in sub_exec["pnl_t1_confirm"] if p > 0)
        gl_conf = abs(sum(p for p in sub_exec["pnl_t1_confirm"] if p < 0))
        pf_conf = gw_conf/gl_conf if gl_conf > 0 else float('inf')
        
        print(f"\n  RISULTATI STRATEGIE DI INGRESSO:")
        print(f"  1. Entrata a T (Baseline):     N={len(sub):<3} | PF = {pf_base:.2f} | PnL = ${sub['pnl_base'].sum():.0f}")
        print(f"  2. Ritardo fisso a T+1:        N={len(sub):<3} | PF = {pf_dly:.2f} | PnL = ${sub['pnl_t1_delay'].sum():.0f}")
        print(f"  3. Entrata T+1 SOLO CONFERMA:  N={len(sub_exec):<3} | PF = {pf_conf:.2f} | PnL = ${sub['pnl_t1_confirm'].sum():.0f}")
        print()

if __name__ == "__main__":
    main()

