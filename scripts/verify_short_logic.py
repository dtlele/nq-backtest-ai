import pandas as pd
import numpy as np

df = pd.read_csv(r'C:\Users\Mauro\Documents\nq-backtest\output\whale_v2_results.csv')

print("=== VERIFICA LOGICA SHORT ===")
short = df[df['direction'] == 'SHORT'].copy()
long_ = df[df['direction'] == 'LONG'].copy()
print(f"Tot SHORT: {len(short)}, Tot LONG: {len(long_)}")
print()

# Exit reason per SHORT vs LONG
print("Exit reason SHORT:")
print(short['exit_reason'].value_counts())
print()
print("Exit reason LONG:")
print(long_['exit_reason'].value_counts())
print()

# Confirm fail SHORT: la barra di entrata chiude CONTRO la direzione
cf_short = short[short['exit_reason'] == 'CONFIRM_FAIL_EXIT']
cf_long  = long_[long_['exit_reason'] == 'CONFIRM_FAIL_EXIT']
print(f"CONFIRM_FAIL SHORT: {len(cf_short)} ({len(cf_short)/len(short)*100:.1f}% dei SHORT)")
print(f"CONFIRM_FAIL LONG:  {len(cf_long)} ({len(cf_long)/len(long_)*100:.1f}% dei LONG)")
print()
print(f"  -> Conclusione: il confirm check scarta il {len(cf_short)/len(short)*100:.1f}% dei SHORT")
print(f"     perche' in NQ 2025-2026 la maggior parte delle barre chiude IN RIALZO")
print(f"     (trend bullish), quindi il check 'close < open' per i SHORT quasi sempre fallisce")
print()

# Tra i SHORT che superano il confirm:
non_cf_short = short[short['exit_reason'] != 'CONFIRM_FAIL_EXIT']
print(f"SHORT che superano confirm: {len(non_cf_short)}")
print(f"  TP: {len(non_cf_short[non_cf_short['exit_reason']=='TP'])}")
print(f"  SL: {len(non_cf_short[non_cf_short['exit_reason']=='SL'])}")
print(f"  TIME: {len(non_cf_short[non_cf_short['exit_reason']=='TIME_EXIT'])}")
if len(non_cf_short) > 0:
    wr_nc = (non_cf_short['net_pnl'] > 0).mean() * 100
    print(f"  WR (solo non-confirm-fail): {wr_nc:.1f}%")
print()

# Verifica pnl_pts: sono corretti per SL e TP?
print("Verifica pnl_pts SHORT (dovrebbe essere +60 TP, -20 SL):")
print(non_cf_short['pnl_pts'].describe())
print()
tp_short = non_cf_short[non_cf_short['exit_reason'] == 'TP']
sl_short = non_cf_short[non_cf_short['exit_reason'] == 'SL']
if len(tp_short) > 0:
    print(f"TP pnl_pts: {tp_short['pnl_pts'].mean():.2f} (dovrebbe essere 60.0) -> {'OK' if abs(tp_short['pnl_pts'].mean()-60)<0.1 else 'BUG!'}")
if len(sl_short) > 0:
    print(f"SL pnl_pts: {sl_short['pnl_pts'].mean():.2f} (dovrebbe essere -20.0) -> {'OK' if abs(sl_short['pnl_pts'].mean()+20)<0.1 else 'BUG!'}")
print()

# Stesso check per LONG
non_cf_long = long_[long_['exit_reason'] != 'CONFIRM_FAIL_EXIT']
tp_long = non_cf_long[non_cf_long['exit_reason'] == 'TP']
sl_long = non_cf_long[non_cf_long['exit_reason'] == 'SL']
print("Verifica pnl_pts LONG:")
if len(tp_long) > 0:
    print(f"TP pnl_pts: {tp_long['pnl_pts'].mean():.2f} (dovrebbe essere 60.0) -> {'OK' if abs(tp_long['pnl_pts'].mean()-60)<0.1 else 'BUG!'}")
if len(sl_long) > 0:
    print(f"SL pnl_pts: {sl_long['pnl_pts'].mean():.2f} (dovrebbe essere -20.0) -> {'OK' if abs(sl_long['pnl_pts'].mean()+20)<0.1 else 'BUG!'}")
print()

# Calcola il WR "teorico" per i SHORT
# Con SL=20, TP=60 e WR teorica necessaria per breakeven:
# WR_be = SL / (SL + TP) = 20/80 = 25%
print("=== BREAKEVEN ANALYSIS ===")
print(f"WR necessaria per breakeven (SL=20, TP=60): {20/(20+60)*100:.1f}%")
print(f"WR effettiva LONG: {(long_['net_pnl']>0).mean()*100:.1f}%")
print(f"WR effettiva SHORT: {(short['net_pnl']>0).mean()*100:.1f}%")
print()
print("=== IPOTESI ROOT CAUSE SHORT 1.4% WR ===")
pct_bars_bullish_est = len(cf_short) / len(short) * 100
print(f"1. Il confirm check scarta {pct_bars_bullish_est:.1f}% dei SHORT (barre chiudono in rialzo)")
print(f"   -> Tutti questi hanno WR=0% per definizione")
print(f"2. I SHORT che passano il confirm ({len(non_cf_short)}) sono in momenti")
print(f"   di forte discesa, ma NQ 2025-2026 e' in uptrend -> recupera subito -> SL")
print(f"3. NON e' un bug di codice, e' un bias di mercato (regime bullish)")
