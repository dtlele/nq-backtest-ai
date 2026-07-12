import json
import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest-clean")

# Riutilizziamo le funzioni del simulatore principale
from scripts.run_unified_backtest_with_filters import (
    get_bars_for_date, compute_5day_atr,
    check_contrary_big_trades, cached_dates
)

raw_lookup = {}

def run_simulation_sweep(seqs_combined, raw_lookup, target_sl, target_tp):
    trades_executed = []
    last_exit_datetime = None
    
    base_contracts = 3
    point_value = 2.0
    commission = 0.50
    
    # Filtriamo solo per il pattern trend_short
    for s in seqs_combined:
        pattern = s["seq_pattern"]
        if pattern != "trend_short":
            continue
            
        date_str = s["date"]
        time_str = s["end_time"]
        entry_price = s["entry_price"]
        direction = "short"
        
        # 1. Volume & Time Filters
        vol = s['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)):
            continue
            
        time_parts = time_str.split(':')
        h, m = int(time_parts[0]), int(time_parts[1])
        t_val = h * 60 + m
        is_morning = (9 * 60 + 30 <= t_val < 11 * 60)
        is_afternoon = (14 * 60 + 30 <= t_val < 15 * 60 + 30)
        
        if not (is_morning or is_afternoon):
            continue
            
        # 2. CVD Climax Filter (Th=2000)
        raw_seq = raw_lookup.get((date_str, time_str))
        if not raw_seq or not raw_seq.get("steps"):
            continue
        last_step = raw_seq["steps"][-1]
        session_cvd = last_step.get("session_cvd", 0)
        if abs(session_cvd) >= 2000:
            continue
            
        # 3. Value Area Exclusion Filter (Block Short inside VA)
        vs_val = last_step.get("price_vs_val", "unknown")
        vs_vah = last_step.get("price_vs_vah", "unknown")
        is_inside_va = (vs_val == "above" and vs_vah == "below")
        if is_inside_va:
            continue
            
        # 4. Contrary Big Trade Filter (Th=250)
        step1_time = raw_seq["steps"][0]["time_et"]
        if check_contrary_big_trades(date_str, step1_time, time_str, direction, threshold=250):
            continue
            
        # Concurrency check
        entry_dt = pd.to_datetime(date_str + ' ' + time_str, format='%Y%m%d %H:%M')
        import pytz
        ET = pytz.timezone("America/New_York")
        entry_dt = ET.localize(entry_dt)
        if last_exit_datetime is not None and entry_dt < last_exit_datetime:
            continue
            
        bars = get_bars_for_date(date_str)
        if not bars:
            continue
            
        entry_idx = -1
        for i, b in enumerate(bars):
            t_et = b.timestamp.astimezone(ET)
            if t_et.strftime("%H:%M") == time_str:
                entry_idx = i
                break
                
        if entry_idx == -1:
            continue
            
        outcome = None
        pnl_pts = 0.0
        exit_time_str = None
        
        # Eseguiamo il trade usando SL e TP passati al sweep
        for i in range(entry_idx + 1, len(bars)):
            bar = bars[i]
            t_et = bar.timestamp.astimezone(ET)
            
            if t_et.hour >= 16:
                outcome = "eod"
                exit_price = bar.close
                pnl_pts = entry_price - exit_price
                exit_time_str = t_et.strftime("%H:%M")
                break
                
            high = bar.high
            low = bar.low
            
            if high >= entry_price + target_sl:
                pnl_pts = -target_sl
                outcome = "loss"
                exit_time_str = t_et.strftime("%H:%M")
                break
            elif low <= entry_price - target_tp - 0.25:
                pnl_pts = target_tp
                outcome = "win"
                exit_time_str = t_et.strftime("%H:%M")
                break
                    
        if outcome is None:
            last_bar = bars[-1]
            t_et = last_bar.timestamp.astimezone(ET)
            outcome = "eod"
            exit_price = last_bar.close
            pnl_pts = entry_price - exit_price
            exit_time_str = t_et.strftime("%H:%M")
            
        pnl_pts = pnl_pts - 1.5  # slippage
        pnl_usd = ((pnl_pts * 2.0) - commission) * base_contracts
        
        trades_executed.append({
            "pnl_usd": pnl_usd,
            "is_win": outcome == "win"
        })
        
        exit_dt = pd.to_datetime(date_str + ' ' + exit_time_str, format='%Y%m%d %H:%M')
        exit_dt = ET.localize(exit_dt)
        if exit_dt < entry_dt:
            exit_dt = exit_dt + pd.Timedelta(days=1)
        last_exit_datetime = exit_dt
        
    return trades_executed

def main():
    print("Inizializzazione date e dati...")
    # Popoliamo cached_dates caricando da run_unified_backtest_with_filters
    import scripts.run_unified_backtest_with_filters as rub
    rub.cached_dates = sorted([f.stem for f in Path(rub.CACHE_DIR).glob("*.csv")])
    
    # Carichiamo le sequenze 2025
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined_2025.json", encoding="utf-8") as f:
        seqs_combined_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2025.json", encoding="utf-8") as f:
        seqs_raw_2025 = json.load(f)
        
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        seqs_combined_2026 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2026.json", encoding="utf-8") as f:
        seqs_raw_2026 = json.load(f)
        
    for s in seqs_raw_2025 + seqs_raw_2026:
        raw_lookup[(s["date"], s["end_time"])] = s
        
    seqs_combined = seqs_combined_2025 + seqs_combined_2026
    seqs_combined = [s for s in seqs_combined if "20250101" <= s["date"] <= "20251130"]
    seqs_combined = sorted(seqs_combined, key=lambda x: (x["date"], x["end_time"]))
    
    # Sweep range
    sl_options = [30, 35, 40, 45, 48, 50, 55, 60, 70]
    tp_options = [80, 90, 100, 110, 113, 120, 130]
    
    print("\nEseguo la scansione dei parametri (Sensitivity Analysis) per il setup TREND_SHORT...")
    results = []
    
    for sl in sl_options:
        for tp in tp_options:
            trades = run_simulation_sweep(seqs_combined, raw_lookup, sl, tp)
            if not trades:
                continue
            
            df = pd.DataFrame(trades)
            net_pnl = df["pnl_usd"].sum()
            total_trades = len(df)
            wins = sum(df["is_win"])
            wr = (wins / total_trades) * 100 if total_trades > 0 else 0
            
            gross_prof = sum(p for p in df["pnl_usd"] if p > 0)
            gross_loss = abs(sum(p for p in df["pnl_usd"] if p < 0))
            pf = gross_prof / gross_loss if gross_loss > 0 else float('inf')
            
            results.append({
                "SL": sl,
                "TP": tp,
                "Trades": total_trades,
                "WinRate": f"{wr:.1f}%",
                "PnL": net_pnl,
                "PF": pf
            })
            
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(by="PF", ascending=False)
    
    print("\nTop 20 Configurazioni per il setup Trend SHORT (Triple A Trap):")
    print(df_results.head(20).to_string(index=False))
    
    df_results.to_csv("output/trend_short_sensitivity.csv", index=False)
    print("\nRisultati completi scritti in output/trend_short_sensitivity.csv")

if __name__ == "__main__":
    main()

