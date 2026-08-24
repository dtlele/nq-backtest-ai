import sys
import pandas as pd
import numpy as np

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

df = pd.read_csv(r"C:\Users\Mauro\Documents\nq-backtest\output\whale_v9_apex_50k_gex.csv")
df['entry_ts'] = pd.to_datetime(df['entry_ts'], utc=True)
df['ts_eastern'] = df['entry_ts'].dt.tz_convert('US/Eastern')
df['year_month'] = df['ts_eastern'].dt.strftime('%Y-%m')
df['year_week'] = df['ts_eastern'].dt.strftime('%Y-W%U')
df['day_name'] = df['ts_eastern'].dt.day_name()
df['hour'] = df['ts_eastern'].dt.hour

print("=====================================================================================================")
print(" 1. STATISTICHE MENSILI DETTAGLIATE (GENNAIO 2025 - AGOSTO 2026)")
print("=====================================================================================================")
print(f"{'Mese':<8} {'Trade':<6} {'Win':<5} {'Loss':<5} {'WR %':<8} {'Profit Factor':<15} {'Net PnL ($)':<14} {'Max DD ($)':<10}")
print("-" * 100)

monthly = []
for ym, grp in df.groupby('year_month'):
    tot = len(grp)
    wins = int((grp['net_pnl'] > 0).sum())
    losses = tot - wins
    wr = wins / tot * 100.0
    net = grp['net_pnl'].sum()
    gw = grp[grp['net_pnl'] > 0]['net_pnl'].sum()
    gl = abs(grp[grp['net_pnl'] < 0]['net_pnl'].sum())
    pf = gw / gl if gl > 0 else 99.0
    
    eq = grp['net_pnl'].cumsum()
    pk = eq.cummax()
    mdd = (pk - eq).max()
    
    pf_str = f"{pf:.2f}" if pf < 90 else "Inf"
    print(f"{ym:<8} {tot:<6} {wins:<5} {losses:<5} {wr:<7.1f}% {pf_str:<15} +${net:<12,.2f} ${mdd:<9,.2f}")

print("=" * 100)

print("\n=====================================================================================================")
print(" 2. STATISTICHE SETTIMANALI (AGGREGATE SU 69 SETTIMANE OPERATIVE)")
print("=====================================================================================================")
weekly_pnl = df.groupby('year_week')['net_pnl'].sum()
tot_weeks = len(weekly_pnl)
win_weeks = (weekly_pnl > 0).sum()
loss_weeks = (weekly_pnl < 0).sum()
avg_weekly_pnl = weekly_pnl.mean()
best_week = weekly_pnl.max()
worst_week = weekly_pnl.min()

print(f"- Totale Settimane con Trade:   {tot_weeks}")
print(f"- Settimane in Profitto (Win):  {win_weeks} ({win_weeks/tot_weeks*100:.1f}%)")
print(f"- Settimane in Perdita (Loss):  {loss_weeks} ({loss_weeks/tot_weeks*100:.1f}%)")
print(f"- Media Guadagno a Settimana:   +${avg_weekly_pnl:,.2f}")
print(f"- Miglior Settimana:            +${best_week:,.2f}")
print(f"- Peggior Settimana:            ${worst_week:,.2f}")
print("=====================================================================================================")

print("\n=====================================================================================================")
print(" 3. STATISTICHE PER GIORNO DELLA SETTIMANA")
print("=====================================================================================================")
print(f"{'Giorno':<12} {'Trade':<7} {'WR %':<8} {'Profit Factor':<15} {'Net PnL ($)':<14} {'Avg PnL/Trade':<12}")
print("-" * 100)
days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
for d in days_order:
    grp = df[df['day_name'] == d]
    if grp.empty: continue
    tot = len(grp)
    wins = (grp['net_pnl'] > 0).sum()
    wr = wins / tot * 100.0
    net = grp['net_pnl'].sum()
    gw = grp[grp['net_pnl'] > 0]['net_pnl'].sum()
    gl = abs(grp[grp['net_pnl'] < 0]['net_pnl'].sum())
    pf = gw / gl if gl > 0 else 99.0
    pf_str = f"{pf:.2f}" if pf < 90 else "Inf"
    print(f"{d:<12} {tot:<7} {wr:<7.1f}% {pf_str:<15} +${net:<12,.2f} +${net/tot:<10,.2f}")
print("=====================================================================================================")

print("\n=====================================================================================================")
print(" 4. STATISTICHE PER FASCIA ORARIA (EST)")
print("=====================================================================================================")
print(f"{'Fascia Oraria (EST)':<22} {'Trade':<7} {'WR %':<8} {'Profit Factor':<15} {'Net PnL ($)':<14} {'Avg PnL/Trade':<12}")
print("-" * 100)
for h, grp in df.groupby('hour'):
    tot = len(grp)
    wins = (grp['net_pnl'] > 0).sum()
    wr = wins / tot * 100.0
    net = grp['net_pnl'].sum()
    gw = grp[grp['net_pnl'] > 0]['net_pnl'].sum()
    gl = abs(grp[grp['net_pnl'] < 0]['net_pnl'].sum())
    pf = gw / gl if gl > 0 else 99.0
    pf_str = f"{pf:.2f}" if pf < 90 else "Inf"
    print(f"{h:02d}:00 - {h:02d}:59 EST        {tot:<7} {wr:<7.1f}% {pf_str:<15} +${net:<12,.2f} +${net/tot:<10,.2f}")
print("=====================================================================================================")
