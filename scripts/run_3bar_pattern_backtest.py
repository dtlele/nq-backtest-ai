import sys
import os
import glob
import time
import pandas as pd
import numpy as np
from pathlib import Path
import pytz

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.data_loader import load_day
from src.range_builder import build_range_bars

NY_TZ = pytz.timezone("America/New_York")
DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"

RANGE_POINTS = 10.0
# Pattern Parameters
SWEEP_DELTA = 25
EXHAUSTION_DELTA = 12
IGNITION_DELTA = 15

def run_fast_pattern_backtest():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "glbx-mdp3-*.trades.csv")))
    
    all_trades = []
    
    t0 = time.time()
    for f in files:
        if not os.path.exists(f):
            continue
            
        date_str = os.path.basename(f).split("-")[2].split(".")[0]
        # print(f"[{date_str}] Inizio analisi...")
        df = load_day(f)
        if df is None or len(df) == 0:
            continue
            
        bars = build_range_bars(df, RANGE_POINTS)
        if len(bars) < 3:
            continue
            
        day_trades = 0
        for i in range(2, len(bars)):
            bar_ts = bars[i].timestamp.astimezone(NY_TZ)
            is_rth = (bar_ts.hour > 9 or (bar_ts.hour == 9 and bar_ts.minute >= 30)) and (bar_ts.hour < 16)
            if not is_rth:
                continue
                
            c_sweep_3 = bars[i-2]
            c_exh_3 = bars[i-1]
            c_ign = bars[i]
            c_sweep_2 = bars[i-1]  # Per il pattern a 2 barre
            
            def count_big_trades(bar, side):
                return sum(1 for t in bar.big_trades if getattr(t, 'side', '') == side)

            # --- LONG PATTERNS ---
            ign_bt_buy = count_big_trades(c_ign, 'A')
            is_ign_long = (c_ign.delta >= IGNITION_DELTA and c_ign.close > c_ign.open and ign_bt_buy >= 1)
            
            if is_ign_long:
                # 3-Bar Pattern (U-Shape)
                sweep_bt_sell_3 = count_big_trades(c_sweep_3, 'B')
                exh_bt_sell_3 = count_big_trades(c_exh_3, 'B')
                
                if c_sweep_3.delta <= -SWEEP_DELTA and sweep_bt_sell_3 >= 3:
                    if abs(c_exh_3.delta) <= EXHAUSTION_DELTA and exh_bt_sell_3 <= 1:
                        all_trades.append({
                            'date': date_str, 'time': bar_ts.strftime('%H:%M:%S'),
                            'timestamp_ns': int(bar_ts.timestamp() * 1e9),
                            'direction': 'LONG', 'pattern': '3-Bar U-Shape',
                            'entry': c_ign.close, 'stop': c_sweep_3.low - 2.0,
                            'sweep_bt': sweep_bt_sell_3, 'ign_bt': ign_bt_buy
                        })
                        day_trades += 1
                        continue # Evita di contarlo due volte se matcha anche il 2-bar
                
                # 2-Bar Pattern (V-Shape)
                sweep_bt_sell_2 = count_big_trades(c_sweep_2, 'B')
                if c_sweep_2.delta <= -SWEEP_DELTA and sweep_bt_sell_2 >= 3:
                    all_trades.append({
                        'date': date_str, 'time': bar_ts.strftime('%H:%M:%S'),
                        'timestamp_ns': int(bar_ts.timestamp() * 1e9),
                        'direction': 'LONG', 'pattern': '2-Bar V-Shape',
                        'entry': c_ign.close, 'stop': c_sweep_2.low - 2.0,
                        'sweep_bt': sweep_bt_sell_2, 'ign_bt': ign_bt_buy
                    })
                    day_trades += 1

            # --- SHORT PATTERNS ---
            ign_bt_sell = count_big_trades(c_ign, 'B')
            is_ign_short = (c_ign.delta <= -IGNITION_DELTA and c_ign.close < c_ign.open and ign_bt_sell >= 1)
            
            if is_ign_short:
                # 3-Bar Pattern (U-Shape)
                sweep_bt_buy_3 = count_big_trades(c_sweep_3, 'A')
                exh_bt_buy_3 = count_big_trades(c_exh_3, 'A')
                
                if c_sweep_3.delta >= SWEEP_DELTA and sweep_bt_buy_3 >= 3:
                    if abs(c_exh_3.delta) <= EXHAUSTION_DELTA and exh_bt_buy_3 <= 1:
                        all_trades.append({
                            'date': date_str, 'time': bar_ts.strftime('%H:%M:%S'),
                            'timestamp_ns': int(bar_ts.timestamp() * 1e9),
                            'direction': 'SHORT', 'pattern': '3-Bar U-Shape',
                            'entry': c_ign.close, 'stop': c_sweep_3.high + 2.0,
                            'sweep_bt': sweep_bt_buy_3, 'ign_bt': ign_bt_sell
                        })
                        day_trades += 1
                        continue
                
                # 2-Bar Pattern (V-Shape)
                sweep_bt_buy_2 = count_big_trades(c_sweep_2, 'A')
                if c_sweep_2.delta >= SWEEP_DELTA and sweep_bt_buy_2 >= 3:
                    all_trades.append({
                        'date': date_str, 'time': bar_ts.strftime('%H:%M:%S'),
                        'timestamp_ns': int(bar_ts.timestamp() * 1e9),
                        'direction': 'SHORT', 'pattern': '2-Bar V-Shape',
                        'entry': c_ign.close, 'stop': c_sweep_2.high + 2.0,
                        'sweep_bt': sweep_bt_buy_2, 'ign_bt': ign_bt_sell
                    })
                    day_trades += 1
                        
        if day_trades > 0:
            print(f"[{date_str}] Trovati {day_trades} pattern perfetti.")
            
    if len(all_trades) == 0:
        print("Nessun trade trovato con questi filtri strettissimi!")
        return
    
    df_results = pd.DataFrame(all_trades)
    out_path = r"C:\Users\Mauro\Documents\nq-backtest-clean\output\pure_3bar_pattern_2025.csv"
    df_results.to_csv(out_path, index=False)
    
    print("=" * 50)
    print("BACKTEST PATTERN 3-BARRE COMPLETATO!")
    print(f"Tempo: {time.time() - t0:.1f} sec")
    print(f"Trade totali trovati (RTH intera): {len(df_results)}")
    print(f"Salvato in: {out_path}")
    print("=" * 50)

if __name__ == "__main__":
    run_fast_pattern_backtest()

