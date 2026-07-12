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

NY_TZ = pytz.timezone("America/New_York")
DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
CATALOG_PATH = r"C:\Users\Mauro\Documents\nq-backtest-clean\output\fst_masterclass_zones_pattern_2025_full.csv"
OUT_PATH = r"C:\Users\Mauro\Documents\nq-backtest-clean\output\mfe_fst_masterclass_zones_2025_full.csv"

def run_mfe_analysis():
    if not os.path.exists(CATALOG_PATH):
        print("Catalogo non trovato!")
        return
        
    df_trades = pd.read_csv(CATALOG_PATH)
    
    # Raggruppa i trade per data
    trades_by_date = {}
    for _, row in df_trades.iterrows():
        d_str = str(row['date'])
        if d_str not in trades_by_date:
            trades_by_date[d_str] = []
        trades_by_date[d_str].append(row.to_dict())
        
    print(f"Totale giorni da processare: {len(trades_by_date)}")
    
    results = []
    
    t0 = time.time()
    for date_str in sorted(trades_by_date.keys()):
        day_trades = trades_by_date[date_str]
        
        # Trova file databento
        pattern = os.path.join(DATA_DIR, f"*{date_str}*.trades.csv")
        matching = glob.glob(pattern)
        if not matching:
            print(f"[{date_str}] File tick non trovato, salto {len(day_trades)} trade(s).")
            continue
            
        filepath = matching[0]
        # Carica intera giornata
        df = load_day(filepath, as_df=True)
        if df is None or len(df) == 0:
            continue
            
        # Filtra solo esecuzioni (data_loader lo fa gia' con action='T')
        # Ma per assicurarci di avere prezzi sani:
        df = df[df['price'] > 10000] # NQ e' sopra 15k, toglie i calendar spread
        
        ts_events = df['ts_event'].values
        prices = df['price'].values
        
        for trade in day_trades:
            # Calcolo target EOD
            # ts_event del trade in CSV e' UTC nanosecond timestamp? Wait. 
            # In run_3bar_pattern_backtest ho salvato 'timestamp_ns'
            entry_ns = trade['timestamp_ns']
            # Convert to np.datetime64 per comparison
            entry_dt64 = np.datetime64(entry_ns, 'ns')
            
            # EOD = 16:00 NY
            dt_ny = pd.Timestamp(entry_ns, unit='ns').tz_localize('UTC').tz_convert(NY_TZ)
            eod_ny = dt_ny.replace(hour=16, minute=0, second=0)
            eod_ns = int(eod_ny.tz_convert('UTC').timestamp() * 1e9)
            eod_dt64 = np.datetime64(eod_ns, 'ns')
            
            # Slice the numpy arrays (much faster than pandas)
            mask = (ts_events >= entry_dt64) & (ts_events <= eod_dt64)
            prices_slice = prices[mask]
            
            if len(prices_slice) == 0:
                continue
                
            entry_price = trade['entry']
            stop_price = trade['stop']
            direction = trade['direction']
            
            max_p = np.max(prices_slice)
            min_p = np.min(prices_slice)
            
            if direction == 'LONG':
                risk = entry_price - stop_price
                mfe_pts = max_p - entry_price
                mae_pts = entry_price - min_p
                
                # Cerca l'indice del primo tick sotto lo stop
                stop_mask = prices_slice <= stop_price
                if np.any(stop_mask):
                    stop_idx = np.argmax(stop_mask) # Primo indice True
                    max_before_stop = np.max(prices_slice[:stop_idx]) if stop_idx > 0 else entry_price
                    mfe_before_stop_pts = max_before_stop - entry_price
                else:
                    mfe_before_stop_pts = mfe_pts
                    
                mfe_r = mfe_before_stop_pts / risk if risk > 0 else 0
                mae_r = mae_pts / risk if risk > 0 else 0
                
            else: # SHORT
                risk = stop_price - entry_price
                mfe_pts = entry_price - min_p
                mae_pts = max_p - entry_price
                
                stop_mask = prices_slice >= stop_price
                if np.any(stop_mask):
                    stop_idx = np.argmax(stop_mask)
                    min_before_stop = np.min(prices_slice[:stop_idx]) if stop_idx > 0 else entry_price
                    mfe_before_stop_pts = entry_price - min_before_stop
                else:
                    mfe_before_stop_pts = mfe_pts
                    
                mfe_r = mfe_before_stop_pts / risk if risk > 0 else 0
                mae_r = mae_pts / risk if risk > 0 else 0
                
            trade['mfe_r'] = mfe_r
            trade['mae_r'] = mae_r
            trade['mfe_pts'] = mfe_pts
            trade['mae_pts'] = mae_pts
            
            # Simulated Outcomes for specific Trailing Targets in Ticks (1 pt = 4 ticks)
            # 20 ticks = 5.0 pts, 40 ticks = 10.0 pts, 80 ticks = 20.0 pts
            trade['hit_20t'] = int(mfe_before_stop_pts >= 5.0)
            trade['hit_40t'] = int(mfe_before_stop_pts >= 10.0)
            trade['hit_80t'] = int(mfe_before_stop_pts >= 20.0)
            trade['hit_120t'] = int(mfe_before_stop_pts >= 30.0)
            
            results.append(trade)
            
        print(f"[{date_str}] Processati {len(day_trades)} trade. (Tempo finora: {time.time()-t0:.1f}s)")
        
    df_out = pd.DataFrame(results)
    df_out.to_csv(OUT_PATH, index=False)
    print("=" * 50)
    print(f"Analisi MFE Completata su {len(results)} trades in {time.time()-t0:.1f} sec!")
    print(f"Salvato in: {OUT_PATH}")
    
    # Stampiamo due statistiche al volo
    win_20t = df_out['hit_20t'].mean() * 100
    win_40t = df_out['hit_40t'].mean() * 100
    win_80t = df_out['hit_80t'].mean() * 100
    win_120t = df_out['hit_120t'].mean() * 100
    print(f"Win Rate @ 20 Ticks (+5 pts): {win_20t:.1f}%")
    print(f"Win Rate @ 40 Ticks (+10 pts): {win_40t:.1f}%")
    print(f"Win Rate @ 80 Ticks (+20 pts): {win_80t:.1f}%")
    print(f"Win Rate @ 120 Ticks (+30 pts): {win_120t:.1f}%")
    print("=" * 50)

if __name__ == "__main__":
    run_mfe_analysis()

