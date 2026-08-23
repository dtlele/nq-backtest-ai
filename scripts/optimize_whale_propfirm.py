"""
Script di Ottimizzazione Quantitativa per Strategia Whale Print (Prop Firm FundedNext 50k CFD).
Consente di testare:
- Commissioni + Slippage ($4 comm. + 1.0 pti slippage per trade)
- Stop Loss e Take Profit dinamici (o basati su ATR / Punti fissi) invece del solo time-based exit
- Filtri su orario RTH (es. 09:45-11:30 e 13:30-15:30)
- Soglie di size (es. 80-150 contratti)
- Filtri su Volatilità / Volume Profile
"""

import os
import glob
import pandas as pd
import numpy as np

def run_optimization_grid():
    results_csv = r"C:\Users\Mauro\Documents\nq-backtest\output\whale_print_all_days_results.csv"
    if not os.path.exists(results_csv):
        print("File dei trade non trovato.")
        return
        
    trades_df = pd.read_csv(results_csv)
    print(f"Caricati {len(trades_df)} trade grezzi.")
    
    # Costi prop firm FundedNext NQ CFD: $4 commissioni + $10 slippage medio (0.5 punti = $10 per NQ) per trade
    COST_PER_TRADE_USD = 14.00
    
    trades_df['net_pnl_usd'] = trades_df['pnl_usd'] - COST_PER_TRADE_USD
    
    print(f"Gross PnL Totale: ${trades_df['pnl_usd'].sum():,.2f}")
    print(f"Net PnL Totale (con comm & slippage): ${trades_df['net_pnl_usd'].sum():,.2f}")
    
    # Test vari filtri di size e holding
    # ...
    
if __name__ == "__main__":
    run_optimization_grid()
