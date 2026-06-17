import json

def parse_active_trades():
    trades = []
    try:
        with open('agent_memory/trades_log.jsonl', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    trades.append(json.loads(line))
    except Exception as e:
        print(f"Error: {e}")
        return
        
    print(f"Total trades in active log: {len(trades)}")
    
    # Group by month
    by_month = {}
    for t in trades:
        date = t.get('date', '')
        month = date[:7]
        if month not in by_month:
            by_month[month] = []
        by_month[month].append(t)
        
    for month, month_trades in sorted(by_month.items()):
        pnl = sum(t.get('pnl_usd', 0) for t in month_trades)
        wins = len([t for t in month_trades if t.get('pnl_usd', 0) > 0])
        losses = len([t for t in month_trades if t.get('pnl_usd', 0) < 0])
        print(f"\nMonth: {month} | Trades: {len(month_trades)} | Wins: {wins} | Losses: {losses} | PnL: ${pnl:.2f}")
        for t in month_trades:
            print(f"  {t.get('date')} {t.get('entry_time_utc')} | {t.get('direction')} | Entry: {t.get('entry_price')} -> Exit: {t.get('exit_price')} | PnL: ${t.get('pnl_usd', 0):.2f} | Reason: {t.get('exit_reason')}")

if __name__ == '__main__':
    parse_active_trades()
