import json

def list_jan_trades():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_jan2025.jsonl"
    with open(trades_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            t = json.loads(line)
            print(f"Date: {t.get('date')} | Dir: {t.get('direction')} | PnL: {t.get('pnl_usd')} | Setup: {t.get('setup_type')} | Exit Reason: {t.get('exit_reason')}")

if __name__ == '__main__':
    list_jan_trades()
