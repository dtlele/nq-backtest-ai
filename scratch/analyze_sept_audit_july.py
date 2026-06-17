import json

def analyze_sept_audit_july():
    path = 'agent_memory/trades_log_backup_sept_audit.jsonl'
    july_trades = []
    
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                t = json.loads(line)
                date = t.get('date', '')
                if '2025-07' in date:
                    july_trades.append(t)
                    
    print(f"Total July Trades in sept_audit: {len(july_trades)}")
    pnl = sum(t.get('pnl_usd', 0) for t in july_trades)
    wins = [t for t in july_trades if t.get('pnl_usd', 0) > 0]
    losses = [t for t in july_trades if t.get('pnl_usd', 0) < 0]
    print(f"PnL: ${pnl:.2f} | Wins: {len(wins)} | Losses: {len(losses)}")
    
    # Print breakdown of losses
    print("\nLosses detail:")
    for t in losses:
        print(f"  {t.get('date')} {t.get('entry_time_utc')} | {t.get('direction')} | Entry: {t.get('entry_price')} -> Exit: {t.get('exit_price')} | PnL: ${t.get('pnl_usd'):.2f} | Reason: {t.get('exit_reason')}")
        
    print("\nWins detail:")
    for t in wins:
        print(f"  {t.get('date')} {t.get('entry_time_utc')} | {t.get('direction')} | Entry: {t.get('entry_price')} -> Exit: {t.get('exit_price')} | PnL: ${t.get('pnl_usd'):.2f} | Reason: {t.get('exit_reason')}")

if __name__ == '__main__':
    analyze_sept_audit_july()
