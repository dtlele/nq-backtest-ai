import json
from pathlib import Path

log_path = Path(r"C:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl")

trades = []
if log_path.exists():
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    trades.append(json.loads(line))
                except:
                    pass

print(f"=== TRADES NELLA RUN ATTUALE (Totale: {len(trades)}) ===")
for i, t in enumerate(trades, 1):
    print(f"\n--- Trade {i} ---")
    print(f"Data: {t.get('date')} | Ora: {t.get('entry_time')[11:16]} | Dir: {t.get('direction').upper()} | PnL: ${float(t.get('pnl_usd', 0)):.2f}")
    print(f"Setup: {t.get('setup_type')} | Fabio Conf: {t.get('final_confidence')}")
    print(f"Fabio Reasoning:\n{t.get('fabio_reasoning')}")
    print(f"Andrea Reasoning:\n{t.get('andrea_reasoning')}")
