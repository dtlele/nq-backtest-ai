import pandas as pd
import numpy as np

# Load the MFE analysis results
df = pd.read_csv("C:/Users/Mauro/Documents/nq-backtest/output/mfe_analysis_results_2025.csv")

print("=" * 60)
print("ANALISI PROFONDA SUGLI 85 TRADE 'STRETTI'")
print("=" * 60)

# 1. Analisi MAE (Max Adverse Excursion)
# Vediamo quanto vanno contro prima di partire
wins_7r = df[df['mfe_r'] >= 7.0]
losses = df[df['outcome'] == 'loss']
wins_2r = df[(df['mfe_r'] >= 2.0) & (df['mfe_r'] < 7.0)]

print("\n--- 1. PROFILO DEL MAE (Sofferenza massima prima del profitto) ---")
print(f"Media MAE sui super-runner (>= 7R): {wins_7r['mae_r'].mean():.2f}R")
print(f"Max MAE sui super-runner (>= 7R):   {wins_7r['mae_r'].max():.2f}R")
print(f"Media MAE sui medi (2R - 7R):       {wins_2r['mae_r'].mean():.2f}R")
print(f"Media MAE sulle perdite piene:      {losses['mae_r'].mean():.2f}R")

# Quanti runner potevamo prendere se avessimo tagliato i trade che vanno contro > 0.5R?
for limit in [0.3, 0.5, 0.7]:
    runners_kept = len(wins_7r[wins_7r['mae_r'] <= limit])
    losses_avoided = len(losses[losses['mae_r'] > limit])
    print(f"Se tagliamo a -{limit}R: Salviamo {losses_avoided}/{len(losses)} losses, Manteniamo {runners_kept}/{len(wins_7r)} super-runner")


print("\n--- 2. ORARI MIGLIORI E PEGGIORI ---")
# Estraiamo l'ora
df['hour'] = df['time'].str[:2].astype(int)
df['session'] = pd.cut(df['hour'], bins=[0, 11, 13, 24], labels=['Mattina (09-11)', 'Pranzo (12-13)', 'Pomeriggio (14-16)'])

grouped = df.groupby('session')
for name, group in grouped:
    if len(group) == 0: continue
    run_7r = len(group[group['mfe_r'] >= 7.0])
    run_2r = len(group[group['mfe_r'] >= 2.0])
    win_rate_2r = run_2r / len(group) * 100
    print(f"{name}: {len(group)} trade totali | >=2R: {run_2r} ({win_rate_2r:.1f}%) | >=7R: {run_7r}")

print("\n--- 3. CORRELAZIONE DELTA E SUCCESSO ---")
# C1_delta = la barra precedente. C2_delta = la barra di setup
# Assorbimento Delta limite era 26
wins_5r = df[df['mfe_r'] >= 5.0]
print(f"Media Delta C1 nei Runner (>=5R): {wins_5r['c1_delta'].mean():.1f}")
print(f"Media Delta C2 nei Runner (>=5R): {wins_5r['c2_delta'].mean():.1f}")
print(f"Media Delta C1 nei Loss:          {losses['c1_delta'].mean():.1f}")
print(f"Media Delta C2 nei Loss:          {losses['c2_delta'].mean():.1f}")

# Long vs Short
long_runners = len(wins_5r[wins_5r['direction'] == 'LONG'])
short_runners = len(wins_5r[wins_5r['direction'] == 'SHORT'])
print(f"\nRunner >= 5R per Direzione: Long={long_runners}, Short={short_runners}")

print("\n--- 4. MFE DEI PERDENTI (Falsi Breakout) ---")
print(f"Dei {len(losses)} trade andati a stop loss, quanti sono partiti bene prima di crollare?")
for r in [1, 2, 3]:
    falsi = len(losses[losses['mfe_r'] >= r])
    print(f"Andati ad almeno +{r}R per poi chiudere a stop: {falsi} ({falsi/len(losses)*100:.1f}%)")
