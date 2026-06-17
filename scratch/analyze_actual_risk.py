import json
import os

def analyze_risk_percentage():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    
    initial_equity = 50000.0
    current_equity = initial_equity
    
    print("=== RISK SIZING AUDIT (MAY-NOV 2025 ACTIVE RUN) ===")
    print(f"{'Date':<10} | {'Stop Pts':<8} | {'Contracts':<9} | {'Target Risk %':<13} | {'Actual Risk $':<13} | {'Actual Risk %':<13} | {'PnL':<8}")
    print("-" * 90)
    
    total_trades = 0
    over_risked_trades = 0
    actual_risk_pcts = []
    
    with open(trades_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                t = json.loads(line)
                date_str = t.get('date', '')
                if not (date_str >= '2025-05-01' and date_str <= '2025-11-30'):
                    continue
                    
                total_trades += 1
                entry = t.get('entry', 0.0)
                stop = t.get('stop', 0.0)
                contracts = t.get('contracts', 1)
                pnl = t.get('pnl_usd', 0.0)
                
                stop_distance = abs(entry - stop)
                
                # 1 contract of MNQ risks $2 per point
                actual_risk_usd = stop_distance * 2.0 * contracts
                actual_risk_pct = (actual_risk_usd / current_equity) * 100.0
                actual_risk_pcts.append(actual_risk_pct)
                
                if actual_risk_pct > 0.11: # If risk is significantly higher than 0.10%
                    over_risked_trades += 1
                    
                print(f"{date_str:<10} | {stop_distance:>8.2f} | {contracts:>9} | 0.10%         | ${actual_risk_usd:>11.2f} | {actual_risk_pct:>11.3f}% | {pnl:>+8.2f}")
                
                # Update compounding equity
                current_equity += pnl
            except Exception as e:
                pass
                
    avg_actual_risk = sum(actual_risk_pcts) / len(actual_risk_pcts) if actual_risk_pcts else 0
    print("-" * 90)
    print(f"Total trades: {total_trades}")
    print(f"Trades risking > 0.10% (due to 1-contract floor or wide stops): {over_risked_trades} ({over_risked_trades/total_trades*100:.1f}%)")
    print(f"Average actual risk percentage: {avg_actual_risk:.3f}%")
    print(f"Max actual risk percentage: {max(actual_risk_pcts) if actual_risk_pcts else 0:.3f}%")
    print(f"Min actual risk percentage: {min(actual_risk_pcts) if actual_risk_pcts else 0:.3f}%")
    print(f"Ending Equity: ${current_equity:.2f}")

if __name__ == '__main__':
    analyze_risk_percentage()
