import glob
import os
import sys
import time
import pickle
from datetime import timedelta
from pathlib import Path

import pandas as pd
import pytz

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.data_loader import load_day
from src.range_builder import build_range_bars
from src.volume_profile import build_profile_from_bars

NY_TZ = pytz.timezone("America/New_York")
DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"

RANGE_POINTS = 10.0
COMPOSITE_LOOKBACK_MIN = 120
PROXIMITY_PTS = 10.0 # Quanti punti di distanza per considerare di essere "nella zona"

# Regole del Pattern
SWEEP_DELTA = 50
EXHAUSTION_DELTA = 20
IGNITION_DELTA = 30
BIG_TRADE_THRESHOLD = 30

def run_fst_masterclass_strategy():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "glbx-mdp3-*.trades.csv")))
    out_path = r"C:\Users\Mauro\Documents\nq-backtest\output\fst_masterclass_zones_pattern_2025_full.csv"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    
    # Initialize CSV
    import csv
    with open(out_path, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'time', 'timestamp_ns', 'direction', 'pattern', 'entry', 'stop'])
        
    t0 = time.time()
    total_trades = 0
    
    for f_path in files:
        if not os.path.exists(f_path):
            continue
            
        date_str = os.path.basename(f_path).split("-")[2].split(".")[0]
        # Restrict to all of 2025
        if not date_str.startswith("2025"):
            continue
            
        print(f"[{date_str}] Analisi con Filtri di Contesto (Zone LVN/VAL) e Pattern a V...")
        
        # --- CACHING LOGIC ---
        cache_dir = r"C:\Users\Mauro\Documents\nq-backtest\cache_bars_40t"
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{date_str}_{RANGE_POINTS}pts.pkl")
        
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f_cache:
                bars = pickle.load(f_cache)
        else:
            df = load_day(f_path)
            if df is None or len(df) == 0:
                continue
            bars = build_range_bars(df, RANGE_POINTS, big_trade_threshold=BIG_TRADE_THRESHOLD)
            with open(cache_file, 'wb') as f_cache:
                pickle.dump(bars, f_cache)
                
        if len(bars) < 3:
            continue
            
        day_trades = 0
        rth_bars = []
        
        day_trades_list = []
        
        for i in range(2, len(bars)):
            bar_ts = bars[i].timestamp.astimezone(NY_TZ)
            is_rth = (bar_ts.hour > 9 or (bar_ts.hour == 9 and bar_ts.minute >= 30)) and (bar_ts.hour < 16)
            
            if is_rth:
                rth_bars.append(bars[i])
                
            if not is_rth or len(rth_bars) < 3:
                continue
                
            # Calcolo Contesto
            start_comp_ts = bars[i].timestamp - timedelta(minutes=COMPOSITE_LOOKBACK_MIN)
            comp_bars = [b for b in bars[:i] if b.timestamp >= start_comp_ts]
            lvn_zones = []
            if comp_bars:
                vp = build_profile_from_bars(comp_bars)
                if vp:
                    lvn_zones = vp.lvn_levels
                    
            session_val = None
            session_vah = None
            day_low = min(b.low for b in rth_bars)
            day_high = max(b.high for b in rth_bars)
            
            if len(rth_bars) > 5:
                vp_rth = build_profile_from_bars(rth_bars)
                if vp_rth:
                    session_val = vp_rth.va_low
                    session_vah = vp_rth.va_high
                    
            c_ign = bars[i]
            c_sweep_3 = bars[i-2]
            c_exh_3 = bars[i-1]
            c_sweep_2 = bars[i-1]
            
            def is_near(price, level):
                return level is not None and abs(price - level) <= PROXIMITY_PTS
                
            def count_big_trades(bar, side):
                return sum(1 for t in bar.big_trades if getattr(t, 'side', '') == side)

            in_buy_zone = False
            if is_near(c_ign.low, session_val) or is_near(c_ign.low, day_low):
                in_buy_zone = True
            for lvn in lvn_zones:
                if is_near(c_ign.low, lvn):
                    in_buy_zone = True
                    break
                    
            in_sell_zone = False
            if is_near(c_ign.high, session_vah) or is_near(c_ign.high, day_high):
                in_sell_zone = True
            for lvn in lvn_zones:
                if is_near(c_ign.high, lvn):
                    in_sell_zone = True
                    break

            if not in_buy_zone and not in_sell_zone:
                continue

            # --- LONG PATTERNS (Solo se in Buy Zone) ---
            if in_buy_zone:
                ign_bt_buy = count_big_trades(c_ign, 'A')
                is_ign_long = (c_ign.delta >= IGNITION_DELTA and c_ign.close > c_ign.open)
                
                if is_ign_long:
                    # 3-Bar U-Shape
                    sweep_bt_sell_3 = count_big_trades(c_sweep_3, 'B')
                    exh_bt_sell_3 = count_big_trades(c_exh_3, 'B')
                    
                    if c_sweep_3.delta <= -SWEEP_DELTA:
                        if abs(c_exh_3.delta) <= EXHAUSTION_DELTA and exh_bt_sell_3 <= 1:
                            if sweep_bt_sell_3 >= 1 or ign_bt_buy >= 1:
                                entry_price = c_ign.open + 1.0
                                day_trades_list.append([date_str, bar_ts.strftime('%H:%M:%S'), int(bar_ts.timestamp() * 1e9), 'LONG', '3-Bar U-Shape', entry_price, entry_price - 20.0])
                                day_trades += 1
                                continue 
                    
                    # 2-Bar V-Shape
                    sweep_bt_sell_2 = count_big_trades(c_sweep_2, 'B')
                    if c_sweep_2.delta <= -SWEEP_DELTA:
                        if sweep_bt_sell_2 >= 1 or ign_bt_buy >= 1:
                            entry_price = c_ign.open + 1.0
                            day_trades_list.append([date_str, bar_ts.strftime('%H:%M:%S'), int(bar_ts.timestamp() * 1e9), 'LONG', '2-Bar V-Shape', entry_price, entry_price - 20.0])
                            day_trades += 1

            # --- SHORT PATTERNS (Solo se in Sell Zone) ---
            if in_sell_zone:
                ign_bt_sell = count_big_trades(c_ign, 'B')
                is_ign_short = (c_ign.delta <= -IGNITION_DELTA and c_ign.close < c_ign.open)
                
                if is_ign_short:
                    # 3-Bar U-Shape
                    sweep_bt_buy_3 = count_big_trades(c_sweep_3, 'A')
                    exh_bt_buy_3 = count_big_trades(c_exh_3, 'A')
                    
                    if c_sweep_3.delta >= SWEEP_DELTA:
                        if abs(c_exh_3.delta) <= EXHAUSTION_DELTA and exh_bt_buy_3 <= 1:
                            if sweep_bt_buy_3 >= 1 or ign_bt_sell >= 1:
                                entry_price = c_ign.open - 1.0
                                day_trades_list.append([date_str, bar_ts.strftime('%H:%M:%S'), int(bar_ts.timestamp() * 1e9), 'SHORT', '3-Bar U-Shape', entry_price, entry_price + 20.0])
                                day_trades += 1
                                continue
                    
                    # 2-Bar V-Shape
                    sweep_bt_buy_2 = count_big_trades(c_sweep_2, 'A')
                    if c_sweep_2.delta >= SWEEP_DELTA:
                        if sweep_bt_buy_2 >= 1 or ign_bt_sell >= 1:
                            entry_price = c_ign.open - 1.0
                            day_trades_list.append([date_str, bar_ts.strftime('%H:%M:%S'), int(bar_ts.timestamp() * 1e9), 'SHORT', '2-Bar V-Shape', entry_price, entry_price + 20.0])
                            day_trades += 1

        if len(day_trades_list) > 0:
            with open(out_path, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(day_trades_list)
            total_trades += len(day_trades_list)
            print(f"[{date_str}] Trovati e salvati {len(day_trades_list)} trade! (Totale: {total_trades})")
            
    print(f"Elaborazione Completata. Trovati {total_trades} trades totali.")

if __name__ == "__main__":
    run_fst_masterclass_strategy()
