import json
from collections import defaultdict
from datetime import datetime

trades = {}
with open('agent_memory/trades_log.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        try:
            t = json.loads(line)
            logged_at_str = t.get('logged_at')
            if not logged_at_str:
                continue
                
            # Keep only trades from the latest run (started after 2026-05-30T11:54:00Z)
            if logged_at_str < "2026-05-30T11:54:00":
                continue
                
            key = f"{t.get('date')}_{t.get('entry_time')}"
            
            # Filter out backward stops (the bug we just patched)
            direction = t.get('direction', 'none')
            entry = t.get('entry')
            stop = t.get('stop')
            if direction == 'long' and stop is not None and entry is not None and stop >= entry:
                continue
            if direction == 'short' and stop is not None and entry is not None and stop <= entry:
                continue
                
            trades[key] = t
        except Exception:
            pass

wins = 0
losses = 0
scratches = 0
total_pnl = 0

daily_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'scratches': 0, 'pnl': 0.0})



for key in sorted(trades.keys()):
    t = trades[key]
    date = t.get('date', '')
    
    time_str = t.get('entry_time', '')
    if len(time_str) >= 16: time_str = time_str[11:16]
    
    direction = t.get('direction', '').upper()
    contracts = t.get('contracts', 0)
    pnl_usd = float(t.get('pnl_usd', 0))
    
    total_pnl += pnl_usd
    daily_stats[date]['pnl'] += pnl_usd
    
    if pnl_usd > 10:
        wins += 1
        daily_stats[date]['wins'] += 1
        exit_str = "WIN"
    elif pnl_usd < -10:
        losses += 1
        daily_stats[date]['losses'] += 1
        exit_str = "LOSS"
    else:
        scratches += 1
        daily_stats[date]['scratches'] += 1
        exit_str = "SCRATCH"
        
    # Individual trade print removed to save space

print("\n" + "=" * 65)
print("RIEPILOGO GIORNALIERO (SOLO ULTIME RUN)")
print("-" * 65)
print(f"{'Data':<12} | {'Trades':<8} | {'W/L/S':<12} | {'Win Rate':<10} | {'Daily PnL':<10}")
print("-" * 65)

for date in sorted(daily_stats.keys()):
    st = daily_stats[date]
    trades_day = st['wins'] + st['losses'] + st['scratches']
    wr = (st['wins'] / trades_day * 100) if trades_day > 0 else 0
    wls = f"{st['wins']}/{st['losses']}/{st['scratches']}"
    print(f"{date:<12} | {trades_day:<8} | {wls:<12} | {wr:>5.1f}%     | ${st['pnl']:<9.2f}")

print("\n" + "=" * 65)
print("TOTALI (Solo Run dalle 17:11 UTC in poi, senza bug allucinazioni)")
print("-" * 65)
total_trades = wins + losses + scratches
win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
print(f"Totale Operazioni: {total_trades}")
print(f"Wins: {wins} | Losses: {losses} | Scratches: {scratches}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"PnL Netto: ${total_pnl:.2f}")

print("\n" + "=" * 65)
print("RAGIONAMENTI CONCISI (Ultimi trade)")
print("-" * 65)
# Print reasonings for the last 5 trades to keep the telegram message concise
last_keys = sorted(trades.keys())[-5:]
for key in last_keys:
    t = trades[key]
    date = t.get('date', '')
    time_str = t.get('entry_time', '')
    if len(time_str) >= 16: time_str = time_str[11:16]
    direction = t.get('direction', '').upper()
    pnl_usd = float(t.get('pnl_usd', 0))
    if pnl_usd > 10: exit_str = "WIN"
    elif pnl_usd < -10: exit_str = "LOSS"
    else: exit_str = "SCRATCH"
    
    print(f"[{date} {time_str}] {direction} ({exit_str} ${pnl_usd:.2f})")
    print(f"  Entry: {t.get('entry')} | Stop: {t.get('stop')} | Target: {t.get('target')}")
    print(f"  Exit: {t.get('exit_price')} ({t.get('exit_reason')})")
    
    # Generate a clean, analytical summary instead of a truncated thought
    f_reason = t.get('fabio_reasoning', '')
    if f_reason:
        # Extract main logical points or summarize cleanly
        summary = f_reason.split('.')[0] if '.' in f_reason else f_reason
        if len(summary) > 130:
            summary = summary[:127] + "..."
        print(f"  Analisi: {summary}")
    print("-" * 30)

# Aggiunge informazioni sulla sessione di esecuzione corrente
import datetime
start_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
print(f"\nAvvio Run: {start_time}")

