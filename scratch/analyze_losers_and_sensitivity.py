import json
import glob
import pandas as pd
from pathlib import Path
import os

DATA_DIR = Path('C:/Users/Mauro/Documents/databento-data')

# 1. Load all unique morning trades (26 trades)
week_trades = []
for p in glob.glob('agent_memory/week*/trades_log.jsonl') + glob.glob('agent_memory_backup/trades_log.jsonl'):
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        week_trades.append(json.loads(line))
                    except: pass

by_entry = {}
for t in week_trades:
    etime = t.get('entry_time')
    if not etime: continue
    et = pd.to_datetime(etime).tz_convert('America/New_York')
    if et.hour == 10:
        if etime not in by_entry:
            by_entry[etime] = t

trades = list(by_entry.values())
trades.sort(key=lambda x: x['entry_time'])

print(f"Totale Trade Mattutini Unici Trovati: {len(trades)}")

# 2. Tick level MFE/MAE calculation
results = []
for t in trades:
    date_str = t['date'].replace('-', '')
    csv_file = DATA_DIR / f"glbx-mdp3-{date_str}.trades.csv"
    
    entry = t['entry']
    stop = t['stop']
    direction = t['direction']
    risk = abs(entry - stop)
    if risk == 0: continue
    
    mfe_r = 0.0
    mae_r = 0.0
    
    if csv_file.exists():
        df = pd.read_csv(csv_file, usecols=['ts_event', 'price', 'symbol'])
        df = df[~df['symbol'].str.contains('-', na=False)]
        front = df['symbol'].value_counts().idxmax()
        df = df[df['symbol'] == front]
        df['ts_event'] = pd.to_datetime(df['ts_event'])
        df = df[df['ts_event'] >= pd.to_datetime(t['entry_time'])]
        
        max_fav = entry
        max_adv = entry
        
        for price in df['price']:
            if direction == 'long':
                if price > max_fav: max_fav = price
                if price < max_adv: max_adv = price
                if price <= stop: break
            else:
                if price < max_fav or max_fav == entry: max_fav = price
                if price > max_adv: max_adv = price
                if price >= stop: break
                
        mfe_r = abs(max_fav - entry) / risk
        mae_r = abs(max_adv - entry) / risk
        
    results.append({
        'entry_time': t['entry_time'],
        'date': t['date'],
        'direction': direction,
        'entry': entry,
        'stop': stop,
        'risk_pts': risk,
        'mfe_r': mfe_r,
        'mae_r': mae_r
    })

# 3. Analyze Losers under 3.5R strategy
losers_35r = [r for r in results if r['mfe_r'] < 3.5]
winners_35r = [r for r in results if r['mfe_r'] >= 3.5]

print(f"\n--- ANALISI TRADE PERDENTI SOTTO 3.5R ({len(losers_35r)} Trade) ---")
mfe_under_05 = [r for r in losers_35r if r['mfe_r'] < 0.5]
mfe_05_to_10 = [r for r in losers_35r if 0.5 <= r['mfe_r'] < 1.0]
mfe_10_to_20 = [r for r in losers_35r if 1.0 <= r['mfe_r'] < 2.0]
mfe_20_to_35 = [r for r in losers_35r if 2.0 <= r['mfe_r'] < 3.5]

print(f"1. MFE < +0.5R (Fallimento Immediato/Fakeout): {len(mfe_under_05)} / {len(losers_35r)} ({len(mfe_under_05)/len(losers_35r)*100:.1f}%)")
print(f"2. 0.5R <= MFE < 1.0R (Piccolo Spunto): {len(mfe_05_to_10)} / {len(losers_35r)}")
print(f"3. 1.0R <= MFE < 2.0R (Ex Partial Runners): {len(mfe_10_to_20)} / {len(losers_35r)}")
print(f"4. 2.0R <= MFE < 3.5R (Quasi a Target): {len(mfe_20_to_35)} / {len(losers_35r)}")

print(f"\n--- DISTRIBUZIONE MFE DEI WINNERS (>= 3.5R) ({len(winners_35r)} Trade) ---")
for r in winners_35r:
    print(f"Date: {r['date']} {r['direction'].upper()} @ {r['entry']} | MFE: {r['mfe_r']:.2f}R")

# 4. Target Sensitivity Sweep
print("\n--- SENSITIVITY ANALYSIS SUI TARGET (2.5R, 3.0R, 3.5R, 4.0R, 4.5R) ---")
targets = [2.5, 3.0, 3.5, 4.0, 4.5]

sensitivity_data = []
for tgt in targets:
    wins = [r for r in results if r['mfe_r'] >= tgt]
    losses = [r for r in results if r['mfe_r'] < tgt]
    
    pnl_r = (len(wins) * tgt) - (len(losses) * 1.0)
    pnl_usd = pnl_r * 50.0 # $50 risk base
    wr = (len(wins) / len(results)) * 100.0
    pf = (len(wins) * tgt) / max(1, len(losses) * 1.0)
    
    sensitivity_data.append({
        'Target': f"{tgt:.1f}R",
        'Wins': len(wins),
        'Losses': len(losses),
        'WinRate': f"{wr:.1f}%",
        'PnL_R': f"{pnl_r:+.2f}R",
        'PnL_USD': f"${pnl_usd:+,.2f}",
        'ProfitFactor': f"{pf:.2f}"
    })

df_sens = pd.DataFrame(sensitivity_data)
print(df_sens.to_string(index=False))

# Write sensitivity report to markdown
os.makedirs('output', exist_ok=True)
with open('output/sensitivity_analysis_report.md', 'w', encoding='utf-8') as f:
    f.write("# 📊 DETAILED DATA ANALYSIS: LOSERS & TARGET SENSITIVITY\n\n")
    f.write("## 1️⃣ Analisi MFE dei 14 Loss Trade (3.5R Baseline)\n")
    f.write(f"- **MFE < +0.5R (Stop Immediato)**: {len(mfe_under_05)} trade ({len(mfe_under_05)/len(losers_35r)*100:.1f}%)\n")
    f.write(f"- **0.5R <= MFE < 1.0R**: {len(mfe_05_to_10)} trade\n")
    f.write(f"- **1.0R <= MFE < 2.0R**: {len(mfe_10_to_20)} trade\n")
    f.write(f"- **2.0R <= MFE < 3.5R**: {len(mfe_20_to_35)} trade\n\n")
    f.write("## 2️⃣ Sensitivity Analysis dei Target (2.5R -> 4.5R)\n\n")
    f.write(df_sens.to_markdown(index=False))
    f.write("\n")

print("\nReport salvato in output/sensitivity_analysis_report.md")
