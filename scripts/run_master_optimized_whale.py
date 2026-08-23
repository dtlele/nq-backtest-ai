"""
Master Script Esecutivo della Strategia Whale Print OTTIMIZZATA per FundedNext 50k CFD.
Integra tutte le scoperte quantitative dell'ottimizzazione:
1. Filtro Size Whale: 80 - 150 contratti
2. Filtro Orario RTH Gold: 09:45 - 12:00 EST & 13:30 - 15:15 EST
3. Location: On Wick (Stoppino candela)
4. Management: Stop Loss Dinamico ATR 2.0x (~22 pti), Take Profit 1:3.0 R:R (~66 pti)
5. Position Sizing: 2 Contratti Micro MNQ ($4.00/punto), Risk max ~$82.80 a trade.
6. Frizione: $14.00 a trade (Commissioni $4 round-turn + $10 slippage medio).
"""

import os
import glob
import pandas as pd
import numpy as np
from datetime import time

def process_databento_file_optimized(filepath: str, min_size: int = 80, max_size: int = 150):
    df = pd.read_csv(filepath, usecols=['ts_event', 'price', 'size', 'side'])
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    df.sort_values('ts_event', inplace=True)
    
    if df['ts_event'].dt.tz is None:
        df['ts_event'] = df['ts_event'].dt.tz_localize('UTC')
    df['ts_eastern'] = df['ts_event'].dt.tz_convert('US/Eastern')
    
    # Finestre Gold RTH: 09:45 - 12:00 EST e 13:30 - 15:15 EST
    t = df['ts_eastern'].dt.time
    gold_mask = ((t >= time(9, 45)) & (t < time(12, 0))) | ((t >= time(13, 30)) & (t < time(15, 15)))
    df_rth = df[gold_mask].copy()
    
    if df_rth.empty:
        return pd.DataFrame()

    df_rth['minute'] = df_rth['ts_eastern'].dt.floor('1min')
    
    bars = df_rth.groupby('minute').agg(
        open=('price', 'first'),
        high=('price', 'max'),
        low=('price', 'min'),
        close=('price', 'last'),
        volume=('size', 'sum')
    )
    
    idx_max_size = df_rth.groupby('minute')['size'].idxmax()
    max_prints = df_rth.loc[idx_max_size, ['minute', 'price', 'size', 'side']].set_index('minute')
    max_prints.columns = ['max_print_price', 'max_print_size', 'max_print_side']
    
    combined = bars.join(max_prints)
    
    size_filter = (combined['max_print_size'] >= min_size) & (combined['max_print_size'] <= max_size)
    
    body_high = combined[['open', 'close']].max(axis=1)
    body_low = combined[['open', 'close']].min(axis=1)
    is_wick = (combined['max_print_price'] >= body_high) | (combined['max_print_price'] <= body_low)
    
    combined['signal'] = 0
    valid_signals = size_filter & is_wick
    
    combined.loc[valid_signals & (combined['max_print_side'] == 'B'), 'signal'] = 1
    combined.loc[valid_signals & (combined['max_print_side'] == 'A'), 'signal'] = -1
    
    return combined

def run_master_optimized_backtest(data_dir: str, max_files: int = None, mnq_contracts: int = 2):
    pattern = os.path.join(data_dir, "glbx-mdp3-*.trades.csv")
    files = sorted(glob.glob(pattern))
    if max_files:
        files = files[:max_files]
        
    print(f"Esecuzione Backtest Master Strategia Whale Print Ottimizzata per Prop Firm su {len(files)} file...")
    
    all_bars = []
    for idx, f in enumerate(files, 1):
        bars = process_databento_file_optimized(f)
        if not bars.empty:
            all_bars.append(bars)
            
    df = pd.concat(all_bars)
    df.sort_index(inplace=True)
    del all_bars

    
    # Calcolo ATR 14
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    df['atr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean()
    df['atr'].fillna(15.0, inplace=True)
    
    signals = df[df['signal'] != 0]
    
    POINT_VALUE_MNQ = 2.0 * mnq_contracts # 2 Micro = $4.00/punto
    COST_PER_TRADE = 1.40 * mnq_contracts # Comm + slippage proporzionati ai micro ($2.80 per 2 micro)
    
    trades = []
    
    for ts, row in signals.iterrows():
        idx = df.index.get_loc(ts)
        if idx + 1 >= len(df):
            continue
            
        entry_time = df.index[idx + 1]
        entry_price = df['open'].iloc[idx + 1]
        sig_dir = row['signal']
        atr_val = df['atr'].iloc[idx]
        
        sl_pts = max(15.0, 2.0 * atr_val)
        tp_pts = sl_pts * 3.0
        
        sl_price = entry_price - sl_pts if sig_dir == 1 else entry_price + sl_pts
        tp_price = entry_price + tp_pts if sig_dir == 1 else entry_price - tp_pts
        
        pnl_pts = 0.0
        exit_time = None
        exit_reason = 'EOD'
        
        for future_idx in range(idx + 1, min(idx + 30, len(df))):
            bar_high = df['high'].iloc[future_idx]
            bar_low = df['low'].iloc[future_idx]
            curr_ts = df.index[future_idx]
            
            if sig_dir == 1:
                if bar_low <= sl_price:
                    pnl_pts = -sl_pts
                    exit_time = curr_ts
                    exit_reason = 'SL'
                    break
                elif bar_high >= tp_price:
                    pnl_pts = tp_pts
                    exit_time = curr_ts
                    exit_reason = 'TP'
                    break
            else:
                if bar_high >= sl_price:
                    pnl_pts = -sl_pts
                    exit_time = curr_ts
                    exit_reason = 'SL'
                    break
                elif bar_low <= tp_price:
                    pnl_pts = tp_pts
                    exit_time = curr_ts
                    exit_reason = 'TP'
                    break
                    
        if exit_time is None:
            future_idx = min(idx + 15, len(df) - 1)
            exit_time = df.index[future_idx]
            exit_price = df['close'].iloc[future_idx]
            pnl_pts = (exit_price - entry_price) if sig_dir == 1 else (entry_price - exit_price)
            exit_reason = 'TIME_EXIT'
            
        gross_pnl_usd = pnl_pts * POINT_VALUE_MNQ
        net_pnl_usd = gross_pnl_usd - COST_PER_TRADE
        
        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': 'LONG' if sig_dir == 1 else 'SHORT',
            'print_size': row['max_print_size'],
            'entry_price': entry_price,
            'exit_reason': exit_reason,
            'pnl_pts': pnl_pts,
            'gross_pnl_usd': gross_pnl_usd,
            'net_pnl_usd': net_pnl_usd
        })
        
    trades_df = pd.DataFrame(trades)
    
    out_dir = r"C:\Users\Mauro\Documents\nq-backtest\output"
    out_csv = os.path.join(out_dir, "whale_master_optimized_results.csv")
    trades_df.to_csv(out_csv, index=False)
    
    win_rate = (trades_df['net_pnl_usd'] > 0).mean() * 100
    net_pnl = trades_df['net_pnl_usd'].sum()
    gross_win = trades_df[trades_df['net_pnl_usd'] > 0]['net_pnl_usd'].sum()
    gross_loss = abs(trades_df[trades_df['net_pnl_usd'] < 0]['net_pnl_usd'].sum())
    profit_factor = gross_win / gross_loss if gross_loss > 0 else np.inf
    
    trades_df['equity'] = trades_df['net_pnl_usd'].cumsum()
    trades_df['peak'] = trades_df['equity'].cummax()
    trades_df['drawdown'] = trades_df['peak'] - trades_df['equity']
    max_dd = trades_df['drawdown'].max()
    
    print("\n========================================================")
    print("      WHALE PRINT MASTER OPTIMIZED STRATEGY RESULTS     ")
    print("========================================================")
    print(f"Sizing:               {mnq_contracts} Micro Contratti MNQ (${POINT_VALUE_MNQ}/pt)")
    print(f"Total Trades:         {len(trades_df)}")
    print(f"Win Rate:             {win_rate:.2f}%")
    print(f"Profit Factor Netto:  {profit_factor:.2f}")
    print(f"Net PnL Totale ($):   ${net_pnl:,.2f}")
    print(f"Max Drawdown ($):     ${max_dd:,.2f}")
    print(f"Risultati salvati in: {out_csv}")
    print("========================================================")

if __name__ == "__main__":
    DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
    run_master_optimized_backtest(DATA_DIR, max_files=None, mnq_contracts=2)
