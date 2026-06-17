import json

def main():
    trades = []
    with open('agent_memory/trades_log.jsonl', 'r') as f:
        for line in f:
            if not line.strip():
                continue
            t = json.loads(line)
            if t.get('date', '').startswith('2025-07'):
                trades.append(t)
    
    trades.sort(key=lambda x: x.get('entry_time', ''))
    
    print(f"Total July trades (sorted): {len(trades)}")
    for i, t in enumerate(trades):
        print(f"{i+1}. {t.get('date')} {t.get('entry_time')} | {t.get('direction')} | Entry: {t.get('entry')} | Exit: {t.get('exit_price')} | PnL: {t.get('pnl_usd')} | Reason: {t.get('exit_reason')}")
    print("Sum of PnL:", sum(t.get('pnl_usd', 0) for t in trades))

if __name__ == '__main__':
    main()
