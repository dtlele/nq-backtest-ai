import json

def find_jan_trades():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_jan2025.jsonl"
    with open(trades_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            t = json.loads(line)
            date = t.get('date')
            if date in ['2025-01-08', '2025-01-13', '2025-01-14']:
                print(f"Date: {date} | Direction: {t.get('direction')} | Entry: {t.get('entry')} | Exit: {t.get('exit_price')} | Reason: {t.get('exit_reason')} | PnL: {t.get('pnl_usd')} | Setup: {t.get('setup_type')}")
                print(f"  Fabio reasoning: {t.get('fabio_reasoning')[:300]}")
                print(f"  Andrea reasoning: {t.get('andrea_reasoning')}")
                print("-" * 100)

if __name__ == '__main__':
    find_jan_trades()
