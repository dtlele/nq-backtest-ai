"""
Analisi v3: verifica entry bar e day boundary issues
"""
import pandas as pd

df = pd.read_csv(
    r'C:\Users\Mauro\Documents\nq-backtest\output\whale_v3_long_only.csv'
)
df['entry_time'] = pd.to_datetime(df['entry_time'], utc=True)
df['exit_time']  = pd.to_datetime(df['exit_time'],  utc=True)

print("Campione entry_time:")
print(df['entry_time'].head(10).to_string())
print()

df['entry_date'] = df['entry_time'].dt.date
print("Trade per data (prime 10 date):")
print(df.groupby('entry_date').size().head(10).to_string())
print()

# Cerca entries dopo 15:00 EST (potenziali day-boundary issues)
df['entry_hour'] = df['entry_time'].dt.hour  # UTC, EST = UTC-4/5
df['entry_min']  = df['entry_time'].dt.minute
# EST = UTC-5 in inverno, UTC-4 in estate
# 15:15 EST = 20:15 UTC inverno, 19:15 UTC estate
# Cerchiamo entrate con ora UTC >= 19 (potenzialmente dopo 15:00 EST)
late_entries = df[df['entry_hour'] >= 19]
print(f"Entrate con ora UTC >= 19 (possibile day boundary): {len(late_entries)}")
print(late_entries[['entry_time', 'exit_time', 'exit_reason', 'net_pnl']].head(20).to_string())
