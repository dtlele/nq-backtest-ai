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

print(f"Totale Trades: {len(trades)}")
print(f"{'Data':<12} | {'Time':<8} | {'Type':<5} | {'Result':<6} | {'PnL ($)':<8} | {'Conf Fabio':<10} | {'Setup':<15}")
print("-" * 80)

wins = []
losses = []

for t in trades:
    date = t.get('date', '')
    time = t.get('entry_time', '')[11:16]
    direction = t.get('direction', '').upper()
    pnl = float(t.get('pnl_usd', 0))
    conf = t.get('final_confidence', 0)
    setup = t.get('setup_type', '')
    
    result_str = "WIN" if pnl > 10 else ("LOSS" if pnl < -10 else "SCRATCH")
    if pnl > 0:
        wins.append(conf)
    elif pnl < 0:
        losses.append(conf)
        
    print(f"{date:<12} | {time:<8} | {direction:<5} | {result_str:<6} | {pnl:>8.2f} | {conf:<10} | {setup:<15}")

print("-" * 80)
if wins:
    print(f"Avg WIN Confidence:  {sum(wins)/len(wins):.1f} (Min: {min(wins)}, Max: {max(wins)})")
if losses:
    print(f"Avg LOSS Confidence: {sum(losses)/len(losses):.1f} (Min: {min(losses)}, Max: {max(losses)})")
