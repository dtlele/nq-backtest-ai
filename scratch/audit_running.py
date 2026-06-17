import json

trades = []
with open(r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        try:
            trades.append(json.loads(line))
        except:
            pass

total = len(trades)
wins = [t for t in trades if t.get("pnl_usd", 0) > 0]
losses = [t for t in trades if t.get("pnl_usd", 0) < 0]
scratch = [t for t in trades if t.get("pnl_usd", 0) == 0]
total_pnl = sum(t.get("pnl_usd", 0) for t in trades)

# Shorts vs Longs
longs = [t for t in trades if t.get("direction") == "long"]
shorts = [t for t in trades if t.get("direction") == "short"]
long_wins = [t for t in longs if t.get("pnl_usd", 0) > 0]
short_wins = [t for t in shorts if t.get("pnl_usd", 0) > 0]
long_pnl = sum(t.get("pnl_usd", 0) for t in longs)
short_pnl = sum(t.get("pnl_usd", 0) for t in shorts)

print(f"=== AUDIT RUNNING - {total} TRADES ===")
print(f"Wins: {len(wins)} | Losses: {len(losses)} | Scratch: {len(scratch)}")
wr = len(wins)/total*100 if total > 0 else 0
print(f"Win Rate: {wr:.1f}%")
print(f"Total PnL: USD {total_pnl:+.2f}")
gross_win = sum(t.get("pnl_usd", 0) for t in wins)
gross_loss = abs(sum(t.get("pnl_usd", 0) for t in losses))
pf = gross_win / gross_loss if gross_loss > 0 else 999
print(f"Profit Factor: {pf:.2f}  (Gross Win: {gross_win:.2f} / Gross Loss: {gross_loss:.2f})")
print()
print(f"--- LONGS ({len(longs)} trades) ---")
print(f"  Wins: {len(long_wins)} | WR: {len(long_wins)/len(longs)*100:.1f}% | PnL: USD {long_pnl:+.2f}")
print(f"--- SHORTS ({len(shorts)} trades) ---")
if shorts:
    print(f"  Wins: {len(short_wins)} | WR: {len(short_wins)/len(shorts)*100:.1f}% | PnL: USD {short_pnl:+.2f}")
else:
    print("  No shorts taken.")

# By exit reason
print()
print("--- BY EXIT REASON ---")
exit_reasons = {}
for t in trades:
    r = t.get("exit_reason", "?")
    if r not in exit_reasons:
        exit_reasons[r] = {"n": 0, "pnl": 0}
    exit_reasons[r]["n"] += 1
    exit_reasons[r]["pnl"] += t.get("pnl_usd", 0)
for r, v in sorted(exit_reasons.items(), key=lambda x: -x[1]["pnl"]):
    print(f"  {r}: N={v['n']} | PnL={v['pnl']:+.2f}")

# Most recent trades
print()
print("--- LAST 10 TRADES ---")
for t in trades[-10:]:
    pnl = t.get("pnl_usd", 0)
    print(f"  {t.get('date')} | {t.get('direction','?'):5} | PnL: {pnl:+7.2f} | {t.get('exit_reason','?'):15} | setup: {t.get('setup_type','?')}")

# Date range
dates = sorted(set(t.get("date", "") for t in trades))
print()
print(f"--- DATE RANGE ---")
print(f"  From: {dates[0] if dates else 'N/A'}")
print(f"  To:   {dates[-1] if dates else 'N/A'}")
print(f"  Trading days: {len(dates)}")
