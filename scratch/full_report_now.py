import json
from pathlib import Path
from collections import defaultdict

# Analisi completa del trades_log attuale
trades = []
with open(r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            trades.append(json.loads(line))
        except:
            pass

total = len(trades)
wins = [t for t in trades if t.get("pnl_usd", 0) > 0]
losses = [t for t in trades if t.get("pnl_usd", 0) < 0]
total_pnl = sum(t.get("pnl_usd", 0) for t in trades)
gross_win = sum(t.get("pnl_usd", 0) for t in wins)
gross_loss = abs(sum(t.get("pnl_usd", 0) for t in losses))
pf = gross_win / gross_loss if gross_loss > 0 else 9999

# Per mese
monthly = defaultdict(lambda: {"n": 0, "wins": 0, "pnl": 0.0})
for t in trades:
    date = t.get("date", "")
    month = date[:7] if date else "?"
    monthly[month]["n"] += 1
    monthly[month]["pnl"] += t.get("pnl_usd", 0)
    if t.get("pnl_usd", 0) > 0:
        monthly[month]["wins"] += 1

# Setup types
setups = defaultdict(lambda: {"n": 0, "wins": 0, "pnl": 0.0})
for t in trades:
    s = t.get("setup_type", "?")
    setups[s]["n"] += 1
    setups[s]["pnl"] += t.get("pnl_usd", 0)
    if t.get("pnl_usd", 0) > 0:
        setups[s]["wins"] += 1

# APM early exits aggregated
early_exits = [t for t in trades if t.get("exit_reason", "").startswith("early_")]
target_hits = [t for t in trades if t.get("exit_reason") == "target"]
stop_hits   = [t for t in trades if t.get("exit_reason") == "stop"]
trail_hits  = [t for t in trades if t.get("exit_reason") == "trailing_stop"]
eod_hits    = [t for t in trades if t.get("exit_reason") == "eod"]

early_pnl = sum(t.get("pnl_usd", 0) for t in early_exits)
early_wins = [t for t in early_exits if t.get("pnl_usd", 0) > 0]

print("=" * 60)
print(f"  BACKTEST REPORT — {total} TRADES TOTAL (LLM + Codice)")
print("=" * 60)
print(f"  Win Rate :  {len(wins)}/{total} = {len(wins)/total*100:.1f}%")
print(f"  P&L Netto:  USD {total_pnl:+,.2f}")
print(f"  Gross Win:  USD {gross_win:,.2f}")
print(f"  Gross Loss: USD {gross_loss:,.2f}")
print(f"  Profit Factor: {pf:.2f}")
print()

print("--- EXIT BREAKDOWN ---")
print(f"  Target    : {len(target_hits):3d} trades  PnL: {sum(t.get('pnl_usd',0) for t in target_hits):+,.2f}")
print(f"  Stop      : {len(stop_hits):3d} trades  PnL: {sum(t.get('pnl_usd',0) for t in stop_hits):+,.2f}")
print(f"  TrailStop : {len(trail_hits):3d} trades  PnL: {sum(t.get('pnl_usd',0) for t in trail_hits):+,.2f}")
print(f"  EOD       : {len(eod_hits):3d} trades  PnL: {sum(t.get('pnl_usd',0) for t in eod_hits):+,.2f}")
print(f"  Early APM : {len(early_exits):3d} trades  PnL: {early_pnl:+,.2f}  (wins: {len(early_wins)})")
print()

print("--- SETUP BREAKDOWN ---")
for s, v in sorted(setups.items(), key=lambda x: -x[1]["pnl"]):
    n = v["n"]
    wr = v["wins"]/n*100 if n > 0 else 0
    print(f"  {s:30s}: N={n:3d}  WR={wr:4.0f}%  PnL={v['pnl']:+,.2f}")
print()

print("--- MONTHLY BREAKDOWN ---")
pnl_cumul = 0
for month in sorted(monthly.keys()):
    v = monthly[month]
    n = v["n"]
    wr = v["wins"]/n*100 if n > 0 else 0
    pnl_cumul += v["pnl"]
    print(f"  {month}: N={n:3d}  WR={wr:4.0f}%  PnL={v['pnl']:+8.2f}  Cumul={pnl_cumul:+8.2f}")
print()

dates = sorted(set(t.get("date", "") for t in trades if t.get("date")))
print(f"--- RANGE ---")
print(f"  Da:       {dates[0] if dates else 'N/A'}")
print(f"  A:        {dates[-1] if dates else 'N/A'}")
print(f"  Gg operativi: {len(dates)}")
print(f"  Trade/giorno: {total/len(dates):.1f}")

# Drawdown
cumul = []
running = 0
for t in trades:
    running += t.get("pnl_usd", 0)
    cumul.append(running)

peak = 0
max_dd = 0
for c in cumul:
    if c > peak:
        peak = c
    dd = peak - c
    if dd > max_dd:
        max_dd = dd
print(f"  Max Drawdown: USD -{max_dd:,.2f}")
