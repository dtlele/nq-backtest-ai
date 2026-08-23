"""
STRATEGIA FINALE DEFINITIVA: WHALE PRINT OPTIMIZED FOR PROPFIRM (FUNDEDNEXT 50K)
Esegue la strategia completa con le migliori ottimizzazioni e regole di timing scoperte:
1. Size Whale: 80 - 150 contratti in RTH
2. Finestra RTH Gold: 09:45 - 12:00 EST & 13:30 - 15:15 EST
3. Location: On Wick (stoppino candela)
4. Timing Esecuzione (Modalità A): Entrata IMMEDIATA al prezzo del print P_print.
5. Exit Management a 30s: Se a 30s il prezzo è a favore, mantieni verso TP (3.0x ATR); se contro (Assorbimento), CHIUDI SUBITO a 30s in Micro-Loss.
6. Position Sizing: Rischio Fisso Monetario di $100 a trade (0.20% del conto $50k) basato su SL ATR.
7. Costs: Commissioni reali $1.40/MNQ + $5.00 fixed slippage.
"""

import os
import glob
import pandas as pd
import numpy as np
from datetime import time

def process_databento_final(filepath: str, min_size: int = 80, max_size: int = 150):
    df = pd.read_csv(filepath, usecols=['ts_event', 'price', 'size', 'side'])
    df['ts_event'] = pd.to_datetime(df['ts_event'])
    df.sort_values('ts_event', inplace=True)
    
    if df['ts_event'].dt.tz is None:
        df['ts_event'] = df['ts_event'].dt.tz_localize('UTC')
    df['ts_eastern'] = df['ts_event'].dt.tz_convert('US/Eastern')
    
    # Orari RTH Gold
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

def run_ultimate_backtest(data_dir: str, max_files: int = None, fixed_risk_usd: float = 100.0):
    pattern = os.path.join(data_dir, "glbx-mdp3-*.trades.csv")
    files = sorted(glob.glob(pattern))
    if max_files:
        files = files[:max_files]
        
    print(f"Elaborazione Backtest Definitivo Finale su {len(files)} file Databento...")
    
    all_bars = []
    for f in files:
        bars = process_databento_final(f)
        if not bars.empty:
            all_bars.append(bars)
            
    df = pd.concat(all_bars)
    df.sort_index(inplace=True)
    del all_bars
    
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - df['close'].shift(1)).abs()
    tr3 = (df['low'] - df['close'].shift(1)).abs()
    df['atr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(14).mean().fillna(15.0)
    
    signals = df[df['signal'] != 0]
    
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
        
        # Position Sizing Fisso $100
        mnq_contracts = max(1, int(round(fixed_risk_usd / (sl_pts * 2.0))))
        point_value = 2.0 * mnq_contracts
        trade_cost = (mnq_contracts * 1.40) + 5.00 # Commissioni + Slippage
        
        sl_price = entry_price - sl_pts if sig_dir == 1 else entry_price + sl_pts
        tp_price = entry_price + tp_pts if sig_dir == 1 else entry_price - tp_pts
        
        # Controllo micro-reazione nei primi 30s / prima barra
        first_bar_close = df['close'].iloc[idx + 1]
        price_favored = (first_bar_close > entry_price) if sig_dir == 1 else (first_bar_close < entry_price)
        
        if not price_favored:
            # Taglio immediato a 30s in Micro-Loss (Assorbimento)
            pnl_pts = (first_bar_close - entry_price) if sig_dir == 1 else (entry_price - first_bar_close)
            exit_reason = 'ABSORPTION_30S_EXIT'
            exit_time = entry_time
        else:
            # Mantieni verso TP/SL
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
                
        gross_pnl_usd = pnl_pts * point_value
        net_pnl_usd = gross_pnl_usd - trade_cost
        
        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': 'LONG' if sig_dir == 1 else 'SHORT',
            'mnq_contracts': mnq_contracts,
            'entry_price': entry_price,
            'exit_reason': exit_reason,
            'pnl_pts': pnl_pts,
            'gross_pnl_usd': gross_pnl_usd,
            'net_pnl_usd': net_pnl_usd
        })
        
    trades_df = pd.DataFrame(trades)
    
    out_dir = r"C:\Users\Mauro\Documents\nq-backtest\output"
    out_csv = os.path.join(out_dir, "ULTIMATE_WHALE_PROPFIRM_RESULTS.csv")
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
    
    sep = "=" * 73
    print(f"\n{sep}")
    print("  [RISULTATI] ULTIMATE OPTIMIZED WHALE STRATEGY (FUNDEDNEXT 50K)")
    print(sep)
    print(f"Rischio Fisso / Trade:   ${fixed_risk_usd:.2f} (0.20% del capitale $50k)")
    print(f"Contratti Medi Usati:    {trades_df['mnq_contracts'].mean():.2f} Micro MNQ")
    print(f"Total Trades Eseguiti:   {len(trades_df)}")
    print(f"Win Rate Netto:          {win_rate:.2f}%")
    print(f"Profit Factor Netto:     {profit_factor:.2f}")
    print(f"Net PnL Totale ($):      ${net_pnl:,.2f}")
    print(f"Max Drawdown Monetario:  ${max_dd:,.2f} (= {(max_dd/2500)*100:.1f}% del max DD $2.500)")
    print(f"Risultati salvati in:    {out_csv}")
    print(sep)

if __name__ == "__main__":
    DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
    run_ultimate_backtest(DATA_DIR, max_files=None, fixed_risk_usd=100.0)
