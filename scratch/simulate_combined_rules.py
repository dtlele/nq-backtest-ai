import json

def simulate_combined():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    
    initial_equity = 50000.0
    
    # Grid search for combined rules
    print("=== COMBINED RULES SIMULATION (R:R VETO + STOP DIST CAP) ===")
    print(f"{'Min R:R':<7} | {'Max Stop':<8} | {'Taken':<5} | {'Skipped':<7} | {'WR%':<5} | {'Net PnL':<10} | {'Final Equity':<12}")
    print("-" * 75)
    
    for min_rr in [0.0, 1.5, 2.0]:
        for max_stop in [25, 35, 50, 999]:
            current_equity = initial_equity
            taken = 0
            skipped = 0
            wins = 0
            losses = 0
            net_pnl = 0.0
            
            with open(trades_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        t = json.loads(line)
                        date_str = t.get('date', '')
                        if not (date_str >= '2025-05-01' and date_str <= '2025-11-30'):
                            continue
                            
                        entry = t.get('entry', 0.0)
                        stop = t.get('stop', 0.0)
                        target = t.get('target', 0.0)
                        pnl = t.get('pnl_usd', 0.0)
                        
                        risk = abs(entry - stop)
                        reward = abs(target - entry)
                        
                        if risk == 0:
                            continue
                            
                        rr = reward / risk
                        
                        # Apply rules
                        if rr < min_rr or risk > max_stop:
                            skipped += 1
                            continue
                            
                        taken += 1
                        net_pnl += pnl
                        if pnl > 0:
                            wins += 1
                        else:
                            losses += 1
                    except Exception as e:
                        pass
                        
            wr = wins / taken * 100 if taken else 0
            print(f"{min_rr:<7} | {max_stop:<8} | {taken:<5} | {skipped:<7} | {wr:>4.1f}% | {net_pnl:>+10.2f} | ${initial_equity + net_pnl:,.2f}")

if __name__ == '__main__':
    simulate_combined()
