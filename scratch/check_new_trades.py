import json

def main():
    trades = []
    with open('agent_memory/trades_log.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            t = json.loads(line)
            if t.get('date', '').startswith('2025-07'):
                trades.append(t)
    
    trades.sort(key=lambda x: x.get('entry_time', ''))
    
    new_trades = [t for t in trades if t.get('date', '') >= '2025-07-17']
    print(f"Total new trades since July 17th: {len(new_trades)}")
    for i, t in enumerate(new_trades):
        print(f"{i+1}. {t.get('date')} {t.get('entry_time')} | {t.get('direction')} | Entry: {t.get('entry')} | Exit: {t.get('exit_price')} | PnL: {t.get('pnl_usd')} | Reason: {t.get('exit_reason')}")
        andrea_sl_override = "No Override"
        # Compare with Fabio's original stop
        # In consensus.py we print: "Overriding stop with Andrea's Structural SL"
        # But we don't store fabio's stop in the trade log unless we compare t['stop'] with fabio_reasoning stop or see if they differ.
        print(f"   Stop: {t.get('stop')} | Target: {t.get('target')}")

if __name__ == '__main__':
    main()
