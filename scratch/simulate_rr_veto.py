import json

def simulate_rr_veto():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    
    initial_equity = 50000.0
    
    for min_rr_threshold in [0.0, 1.0, 1.5, 2.0, 3.0]:
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
                    
                    if rr < min_rr_threshold:
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
        print(f"Min R:R Veto: {min_rr_threshold:<3} | Taken: {taken:<3} | Skipped: {skipped:<3} | WR: {wr:>5.1f}% | Net PnL: {net_pnl:>+8.2f} | Final Equity: ${initial_equity + net_pnl:,.2f}")

if __name__ == '__main__':
    simulate_rr_veto()
