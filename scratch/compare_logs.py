import json
import pandas as pd
from pathlib import Path

def load_trades(filepath):
    trades = []
    if not Path(filepath).exists():
        return trades
    with open(filepath, 'r') as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
                trades.append(data)
            except Exception:
                pass
    return trades

gemini_file = "agent_memory/trades_log_gemini_feb_week1.jsonl"
deepseek_file = "agent_memory/trades_log.jsonl"

gemini_trades = load_trades(gemini_file)
deepseek_trades = load_trades(deepseek_file)

print(f"Gemini Trades: {len(gemini_trades)}")
print(f"DeepSeek Trades: {len(deepseek_trades)}")

def summarize(trades, name):
    print(f"\n--- {name} SUMMARY ---")
    if not trades:
        print("No trades")
        return
    
    pnl = sum([t.get('trade_pnl_usd', 0) or 0 for t in trades])
    wins = sum([1 for t in trades if (t.get('trade_pnl_usd', 0) or 0) > 0])
    win_rate = wins / len(trades) * 100
    
    print(f"Total PnL: ${pnl:.2f}")
    print(f"Win Rate: {win_rate:.1f}% ({wins}/{len(trades)})")
    
    print("\nTrades Details:")
    for t in trades:
        dt = t.get('bar_time_utc', '')[:16]
        direction = t.get('trade_direction', '')
        pnl_usd = t.get('trade_pnl_usd', 0)
        setup = t.get('fabio_setup', '')
        reason = t.get('fabio_reasoning', '')
        andrea_veto = t.get('andrea_confirmation', None)
        print(f"[{dt}] {direction.upper()} {setup} | PnL: ${pnl_usd}")
        print(f"  Fabio: {reason}")
        print(f"  Andrea Veto/Confirm: {andrea_veto}")

summarize(gemini_trades, "GEMINI")
summarize(deepseek_trades, "DEEPSEEK")
