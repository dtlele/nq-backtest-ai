import json
import os

def simulate_risk_cap():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    
    initial_equity = 50000.0
    
    for max_stop_pts in [25, 30, 35, 40, 50, 999]:
        current_equity = initial_equity
        trades_taken = 0
        trades_skipped = 0
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
                    pnl = t.get('pnl_usd', 0.0)
                    
                    stop_distance = abs(entry - stop)
                    
                    if stop_distance > max_stop_pts:
                        trades_skipped += 1
                        continue
                        
                    trades_taken += 1
                    net_pnl += pnl
                    if pnl > 0:
                        wins += 1
                    else:
                        losses += 1
                        
                except Exception as e:
                    pass
                    
        wr = wins / trades_taken * 100 if trades_taken else 0
        print(f"Max Stop Cap: {max_stop_pts:<3} pts | Taken: {trades_taken:<3} | Skipped: {trades_skipped:<3} | WR: {wr:>5.1f}% | Net PnL: {net_pnl:>+8.2f} | Final Equity: ${initial_equity + net_pnl:,.2f}")

if __name__ == '__main__':
    simulate_risk_cap()
