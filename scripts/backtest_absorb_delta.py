import pandas as pd
import numpy as np

def main():
    csv_path = "C:/Users/Mauro/Documents/nq-backtest-clean/output/mfe_analysis_results_2025.csv"
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"File non trovato: {csv_path}")
        return

    print("=" * 60)
    # Filtriamo solo i setup
    df_absorb = df.copy()
    print(f"Trade Absorb Totali (Baseline): {len(df_absorb)}")
    
    # Calcolo baseline metrics
    pnl_col = 'pnl_usd' if 'pnl_usd' in df_absorb.columns else 'mfe_r'  # fallback if pnl_usd not present
    # Wait, let's see if pnl_usd is in the columns. The column header shows 'risk_pts', 'mfe_r', etc.
    # PnL USD can be calculated from risk_pts and outcome, or we can just use mfe_r/outcome to count wins/losses!
    # Let's count wins/losses: if outcome == 'win' it is positive, if outcome == 'loss' it is negative.
    # Or let's see if we can calculate the profit in R:
    # A win is +tp (which is about 1.5R - 2.5R) and a loss is -1R.
    # Let's look at the columns: date,time,direction,entry,stop,risk_pts,c1_delta,c2_delta,c1_close,c2_close,reason,half_size,mfe_pts,mfe_r,mae_pts,mae_r,outcome
    # Since we don't have pnl_usd, we can just use outcome to calculate Win Rate and count trade stats!
    
    df_absorb['is_win'] = df_absorb['outcome'] == 'win'
    wr_base = df_absorb['is_win'].mean() * 100
    print(f"Baseline -> N: {len(df_absorb)} | WR: {wr_base:.1f}%")

    # Applichiamo il filtro Delta
    # Setup Long: C1_delta > 0 e C2_delta < 0
    # Setup Short: C1_delta < 0 e C2_delta > 0
    def filter_delta(row):
        direction = row['direction'].lower()
        c1 = row['c1_delta']
        c2 = row['c2_delta']
        if direction == 'long':
            return c1 > 0 and c2 < 0
        elif direction == 'short':
            return c1 < 0 and c2 > 0
        return True

    df_filtered = df_absorb[df_absorb.apply(filter_delta, axis=1)].copy()
    
    wr_filt = df_filtered['is_win'].mean() * 100
    print("\n" + "=" * 60)
    print("RISULTATI CON FILTRO DELTA ATTIVO (C1 & C2)")
    print("=" * 60)
    print(f"Filtered -> N: {len(df_filtered)} | WR: {wr_filt:.1f}%")
    
    # Breakdown per setup filtrati
    for direction in ['LONG', 'SHORT']:
        sub = df_filtered[df_filtered['direction'] == direction]
        if len(sub) == 0: continue
        wr = sub['is_win'].mean() * 100
        print(f"  {direction:15} -> N: {len(sub):3} | WR: {wr:5.1f}%")

if __name__ == "__main__":
    main()
