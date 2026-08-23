"""
Whale Print Strategy (dall'analisi quantitativa di Matt Conte)
Strategia basata sull'ordine massimo di ogni minuto sui dati Tick/MBO di Databento per NQ.

Regole/Filtri definiti nel video:
1. Size del print massimo per minuto: compresa tra 70 e 190 contratti (esclude <50 inutile e >200 exhaustion/block/stops).
2. Sessione: Solo RTH (Regular Trading Hours: 09:30 - 16:00 EST).
3. Location: Il print deve avvenire nell'ombra/stoppino della candela (Wick), non a metà corpo (Body).
4. Direzione: Seguire la direzione del print (Buy -> Long, Sell -> Short).
5. Orizzonte temporale/Holding period: Mantiene la posizione per 15-20 minuti (default 15 min).
"""

import os
import glob
import pandas as pd
import numpy as np
from datetime import time

def process_databento_file_for_whales(filepath: str, min_size: int = 70, max_size: int = 190):
    """
    Legge un file CSV di Databento e calcola per ciascun minuto RTH l'ordine (print) massimo.
    """
    df = pd.read_csv(filepath, usecols=['ts_event', 'price', 'size', 'side'])
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    df.sort_values('ts_event', inplace=True)
    
    # Filtro RTH (09:30 - 16:00 EST / US Eastern Time)
    # Convertiamo il timestamp in US/Eastern
    if df['ts_event'].dt.tz is None:
        df['ts_event'] = df['ts_event'].dt.tz_localize('UTC')
    df['ts_eastern'] = df['ts_event'].dt.tz_convert('US/Eastern')
    
    rth_mask = (df['ts_eastern'].dt.time >= time(9, 30)) & (df['ts_eastern'].dt.time < time(16, 0))
    df_rth = df[rth_mask].copy()
    
    if df_rth.empty:
        return pd.DataFrame()

    # Raggruppiamo per 1 minuto
    df_rth['minute'] = df_rth['ts_eastern'].dt.floor('1min')
    
    # 1. Costruiamo barre 1-minuto (OHLC)
    bars = df_rth.groupby('minute').agg(
        open=('price', 'first'),
        high=('price', 'max'),
        low=('price', 'min'),
        close=('price', 'last'),
        volume=('size', 'sum')
    )
    
    # 2. Troviamo il print massimo per ciascun minuto
    idx_max_size = df_rth.groupby('minute')['size'].idxmax()
    max_prints = df_rth.loc[idx_max_size, ['minute', 'price', 'size', 'side']].set_index('minute')
    max_prints.columns = ['max_print_price', 'max_print_size', 'max_print_side']
    
    # Uniamo barra OHLC con le info del print massimo
    combined = bars.join(max_prints)
    
    # 3. Applichiamo i filtri della strategia Matt Conte
    # Filtro 1: Size tra 70 e 190 contratti
    size_filter = (combined['max_print_size'] >= min_size) & (combined['max_print_size'] <= max_size)
    
    # Filtro 2: Location on Wick (l'ordine è avvenuto nello stoppino, cioè vicinissimo a High o Low)
    body_high = combined[['open', 'close']].max(axis=1)
    body_low = combined[['open', 'close']].min(axis=1)
    
    # Is Wick: se il prezzo del print è sopra body_high o sotto body_low
    is_wick = (combined['max_print_price'] >= body_high) | (combined['max_print_price'] <= body_low)
    
    # Segnale: 1 per Long (Buy side print), -1 per Short (Ask/Sell side print)
    combined['signal'] = 0
    valid_signals = size_filter & is_wick
    
    # Nota: side = 'B' (Bid/Sell trade) o 'A' (Ask/Buy trade) o 'B'/'Ask' a seconda della codifica Databento
    # Noto da Databento: 'B' = Buy aggressive / 'A' = Ask or Sell
    combined.loc[valid_signals & (combined['max_print_side'] == 'B'), 'signal'] = 1
    combined.loc[valid_signals & (combined['max_print_side'] == 'A'), 'signal'] = -1
    
    return combined

def run_whale_backtest(data_dir: str, max_files: int = None, holding_minutes: int = 15, point_value: float = 20.0):
    pattern = os.path.join(data_dir, "glbx-mdp3-*.trades.csv")
    files = sorted(glob.glob(pattern))
    if max_files:
        files = files[:max_files]
    
    all_bars = []
    print(f"Elaborazione di tutti i {len(files)} file per la strategia Whale Print (Matt Conte)...")
    
    total_files = len(files)
    for idx, f in enumerate(files, 1):
        if idx % 10 == 0 or idx == total_files:
            print(f"Progresso: {idx}/{total_files} file analizzati...")
        bars = process_databento_file_for_whales(f)
        if not bars.empty:
            all_bars.append(bars)
            
    if not all_bars:
        print("Nessun dato trovato.")
        return
        
    df = pd.concat(all_bars)
    df.sort_index(inplace=True)
    
    signals = df[df['signal'] != 0]
    print(f"\nTotale segnali Whale trovati su tutto il dataset (RTH, size 70-190, on Wick): {len(signals)}")
    
    trades = []
    close_prices = df['close'].values
    indices = {ts: idx for idx, ts in enumerate(df.index)}
    
    for ts, row in signals.iterrows():
        idx = indices[ts]
        # Inserimento al timestamp successivo (open barra dopo)
        if idx + 1 >= len(df):
            continue
        entry_price = df['open'].iloc[idx + 1]
        sig_dir = row['signal']
        
        # Uscita fissa dopo holding_minutes (es. 15 min)
        exit_idx = min(idx + 1 + holding_minutes, len(df) - 1)
        exit_price = close_prices[exit_idx]
        
        pnl_pts = (exit_price - entry_price) if sig_dir == 1 else (entry_price - exit_price)
        pnl_usd = pnl_pts * point_value
        
        trades.append({
            'entry_time': df.index[idx + 1],
            'exit_time': df.index[exit_idx],
            'direction': 'LONG' if sig_dir == 1 else 'SHORT',
            'print_size': row['max_print_size'],
            'print_price': row['max_print_price'],
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pts': pnl_pts,
            'pnl_usd': pnl_usd
        })
        
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        print("Nessun trade completato.")
        return
        
    # Salva report CSV
    out_dir = r"C:\Users\Mauro\Documents\nq-backtest\output"
    os.makedirs(out_dir, exist_ok=True)
    out_csv = os.path.join(out_dir, "whale_print_all_days_results.csv")
    trades_df.to_csv(out_csv, index=False)
    
    win_rate = (trades_df['pnl_usd'] > 0).mean() * 100
    total_pnl = trades_df['pnl_usd'].sum()
    avg_trade_usd = trades_df['pnl_usd'].mean()
    gross_win = trades_df[trades_df['pnl_usd'] > 0]['pnl_usd'].sum()
    gross_loss = abs(trades_df[trades_df['pnl_usd'] < 0]['pnl_usd'].sum())
    profit_factor = gross_win / gross_loss if gross_loss > 0 else np.inf
    
    print("\n========================================================")
    print("      WHALE PRINT STRATEGY FULL DATASET BACKTEST RESULTS")
    print("========================================================")
    print(f"Total Files Analyzed: {len(files)}")
    print(f"Total Trades:         {len(trades_df)}")
    print(f"Win Rate:             {win_rate:.2f}%")
    print(f"Avg PnL per Trade:    ${avg_trade_usd:.2f}")
    print(f"Total Gross Profit:   ${gross_win:,.2f}")
    print(f"Total Gross Loss:     ${gross_loss:,.2f}")
    print(f"Total Net PnL ($):    ${total_pnl:,.2f}")
    print(f"Profit Factor:        {profit_factor:.2f}")
    print(f"Risultati salvati in: {out_csv}")
    print("========================================================")

if __name__ == "__main__":
    DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
    run_whale_backtest(DATA_DIR, max_files=None, holding_minutes=15)

