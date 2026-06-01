import json
from datetime import datetime, timezone
import pytz

TRADES_LOG = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
ET = pytz.timezone("America/New_York")

# Prima: mostra struttura dei record per capire i campi disponibili
print("=== STRUTTURA DEL LOG ===")
with open(TRADES_LOG, "r", encoding="utf-8-sig") as f:
    for i, line in enumerate(f):
        line = line.strip()
        if not line:
            continue
        try:
            sample = json.loads(line)
            print(f"Keys: {list(sample.keys())}")
            # Mostra tutte le date presenti
            for k in ["entry_time", "bar_time_utc", "timestamp", "date", "time"]:
                if k in sample:
                    print(f"  {k}: {sample[k]}")
            print(f"  decision: {sample.get('decision','N/A')}")
            print(f"  outcome: {sample.get('outcome','N/A')}")
            print(f"  pnl: {sample.get('pnl', sample.get('profit_loss','N/A'))}")
            print()
            if i >= 4:
                break
        except Exception as e:
            print(f"  Errore parsing riga {i}: {e}")
            continue
