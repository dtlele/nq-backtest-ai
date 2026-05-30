import json

trades = {}
with open('agent_memory/trades_log.jsonl', 'r') as f:
    for line in f:
        try:
            t = json.loads(line)
            # Deduplicate by using date + entry_time as key, keeping the latest version
            key = f"{t.get('date')}_{t.get('entry_time')}"
            trades[key] = t
        except: pass

wins = 0
losses = 0
scratches = 0
total_pnl = 0

print(f"{'Data':<12} | {'Ora':<5} | {'Dir':<5} | {'Lotti':<5} | {'Risk Iniziale (Stop Inziale)':<35} | {'Esito':<8} | {'PnL Reale':<10}")
print("-" * 100)

for key in sorted(trades.keys()):
    t = trades[key]
    
    date = t.get('date', '')
    if date < '2025-11-21': continue 
    
    time_str = t.get('entry_time', '')
    if len(time_str) >= 16: time_str = time_str[11:16]
    
    direction = t.get('direction', '').upper()
    entry = t.get('entry', 0)
    stop = t.get('stop', 0)
    contracts = t.get('contracts', 0)
    pnl_usd = t.get('pnl_usd', 0)
    
    if pnl_usd < 0:
        stop_dist_pts = abs(entry - stop)
        risk_usd = stop_dist_pts * 2 * contracts
        risk_str = f"{stop_dist_pts:.2f} pt -> ${risk_usd:.2f}"
    else:
        risk_str = "Trailing Stop Hit"
    
    total_pnl += pnl_usd
    
    if pnl_usd > 10:
        wins += 1
        exit_str = "WIN"
    elif pnl_usd < -10:
        losses += 1
        exit_str = "LOSS"
    else:
        scratches += 1
        exit_str = "SCRATCH"
        
    print(f"{date:<12} | {time_str:<5} | {direction:<5} | {contracts:<5} | {risk_str:<35} | {exit_str:<8} | ${pnl_usd:<9.2f}")

print("-" * 100)
total_trades = wins + losses + scratches
win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0

print(f"\nTotale Operazioni: {total_trades}")
print(f"Wins: {wins} | Losses: {losses} | Scratches: {scratches}")
print(f"Win Rate: {win_rate:.1f}%")
print(f"PnL Netto: ${total_pnl:.2f}")
