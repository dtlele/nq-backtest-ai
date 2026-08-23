"""
Analisi approfondita risultati v7:
1. Distribuzione mensile dei trade
2. Quanti segnali vengono skippati da ONE_TRADE_ONLY
3. Analisi equity curve e drawdown
4. Check: i 22 SL quando capitano? In quali condizioni?
"""
import pandas as pd
import numpy as np

df = pd.read_csv(r'C:\Users\Mauro\Documents\nq-backtest\output\whale_v7_calibrated.csv')
df['entry_ts'] = pd.to_datetime(df['entry_ts'], utc=True)
df['exit_ts']  = pd.to_datetime(df['exit_ts'],  utc=True)
df['entry_ts_est'] = df['entry_ts'].dt.tz_convert('US/Eastern')
df['exit_ts_est']  = df['exit_ts'].dt.tz_convert('US/Eastern')

print(f"=== WHALE v7 - {len(df)} TRADE TOTALI ===\n")

# Distribuzione mensile
df['month'] = df['entry_ts_est'].dt.to_period('M')
monthly = df.groupby('month').agg(
    n_trades=('net_pnl', 'count'),
    net_pnl=('net_pnl', 'sum'),
    wins=('net_pnl', lambda x: (x > 0).sum()),
).assign(wr=lambda x: x['wins'] / x['n_trades'] * 100)
print("=== DISTRIBUZIONE MENSILE ===")
print(monthly[['n_trades', 'net_pnl', 'wr']].to_string())
print()

# Equity curve
df_sorted = df.sort_values('entry_ts').reset_index(drop=True)
df_sorted['equity']   = df_sorted['net_pnl'].cumsum()
df_sorted['peak']     = df_sorted['equity'].cummax()
df_sorted['drawdown'] = df_sorted['peak'] - df_sorted['equity']
max_dd    = df_sorted['drawdown'].max()
max_dd_idx = df_sorted['drawdown'].idxmax()
print(f"=== EQUITY CURVE ===")
print(f"Equity finale:  ${df_sorted['equity'].iloc[-1]:,.2f}")
print(f"Peak:           ${df_sorted['peak'].max():,.2f}")
print(f"Max Drawdown:   ${max_dd:,.2f} (al trade n. {max_dd_idx})")
print()

# Durata media trade
df_sorted['duration_min'] = (df_sorted['exit_ts'] - df_sorted['entry_ts']).dt.total_seconds() / 60
print(f"=== DURATA TRADE ===")
print(f"Durata media:   {df_sorted['duration_min'].mean():.1f} minuti")
print(f"TP: {df_sorted[df_sorted['exit_reason']=='TP']['duration_min'].mean():.1f} min in media")
print(f"SL: {df_sorted[df_sorted['exit_reason']=='SL']['duration_min'].mean():.1f} min in media")
print(f"TIME_EXIT: {df_sorted[df_sorted['exit_reason']=='TIME_EXIT']['duration_min'].mean():.1f} min in media")
print()

# Analisi SL: quando capitano?
sl_trades = df_sorted[df_sorted['exit_reason'] == 'SL']
print(f"=== ANALISI 22 SL TRADE ===")
print(f"n SL: {len(sl_trades)}")
print(f"SL side=A: {(sl_trades['wp_side']=='A').sum()}")
print(f"SL side=B: {(sl_trades['wp_side']=='B').sum()}")
print(f"SL entry_price range: {sl_trades['entry_price'].min():.2f} - {sl_trades['entry_price'].max():.2f}")
sl_trades_show = sl_trades[['entry_ts_est','wp_size','wp_side','entry_price','duration_min']].copy()
sl_trades_show['entry_ts_est'] = sl_trades_show['entry_ts_est'].dt.strftime('%Y-%m-%d %H:%M')
print(sl_trades_show.to_string())
print()

# Ora di entrata (orario EST)
df_sorted['entry_hour'] = df_sorted['entry_ts_est'].dt.hour
df_sorted['entry_minute_of_day'] = df_sorted['entry_ts_est'].dt.hour * 60 + df_sorted['entry_ts_est'].dt.minute
print("=== WIN RATE PER ORA DI ENTRATA (EST) ===")
hourly = df_sorted.groupby('entry_hour').agg(
    n=('net_pnl', 'count'),
    wr=('net_pnl', lambda x: (x > 0).mean() * 100),
    avg=('net_pnl', 'mean')
)
print(hourly.to_string())
print()

# Trade consecutivi persi
df_sorted['win'] = df_sorted['net_pnl'] > 0
streak = 0
max_loss_streak = 0
current_streak = 0
for w in df_sorted['win']:
    if not w:
        current_streak += 1
        max_loss_streak = max(max_loss_streak, current_streak)
    else:
        current_streak = 0
print(f"=== SEQUENZE ===")
print(f"Max sequenza perdente consecutiva: {max_loss_streak} SL di fila")
print(f"  -> Perdita massima sequenza: ${max_loss_streak * 87.80:.2f}")
