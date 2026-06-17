import json, datetime, pytz
from collections import defaultdict

path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl.bak_pre_exec_veto"
ET = pytz.timezone('America/New_York')

trades_by_day = defaultdict(list)
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            t = json.loads(line)
            trades_by_day[t.get('date', '')].append(t)
        except:
            pass

def get_et(t):
    try:
        return datetime.datetime.fromisoformat(
            t['entry_time'].replace('Z', '+00:00')
        ).astimezone(ET)
    except:
        return datetime.datetime.min.replace(tzinfo=pytz.UTC)

first_pnls, sub_pnls = [], []
fomo_n, fomo_loss, fomo_pnl = 0, 0, 0.0

print("GIORNI CON 2+ TRADE E SPREAD ENTRATA >15pt:")
print("-" * 70)
for date in sorted(trades_by_day.keys()):
    ts = sorted(trades_by_day[date], key=get_et)
    if len(ts) < 2:
        first_pnls.append(ts[0].get('pnl_usd', 0))
        continue
    entries = []
    for t in ts:
        e = t.get('entry_price') or t.get('entry') or 0
        entries.append(float(e) if e else 0.0)
    pnls = [t.get('pnl_usd', 0) for t in ts]

    if not any(entries):
        continue

    first = entries[0]
    spread = max(entries) - first

    if spread > 15:
        sub_sum = sum(pnls[1:])
        print(f"{date} | {len(ts)} trade | spread={spread:.0f}pt")
        for i, (e, p, t) in enumerate(zip(entries, pnls, ts)):
            dist = e - first
            er = t.get('exit_reason', '?')
            print(f"  [{i+1}] entry={e:.1f} (+{dist:.0f}pt dal 1st) pnl={p:+.2f} exit={er}")
        print(f"  => 1st trade: {pnls[0]:+.2f} | successivi: {sum(pnls[1:]):+.2f}")
        print()

    first_pnls.append(pnls[0])
    for i, (e, p) in enumerate(zip(entries[1:], pnls[1:]), 1):
        sub_pnls.append(p)
        dist = e - first
        if dist > 15:
            fomo_n += 1
            fomo_pnl += p
            if p < 0:
                fomo_loss += 1

print("=" * 70)
print(f"Primo trade/giorno    : N={len(first_pnls)} | Totale={sum(first_pnls):+.2f} | Avg={sum(first_pnls)/len(first_pnls):.2f}")
if sub_pnls:
    print(f"Trade successivi      : N={len(sub_pnls)} | Totale={sum(sub_pnls):+.2f} | Avg={sum(sub_pnls)/len(sub_pnls):.2f}")
if fomo_n:
    print(f"FOMO (>15pt dal 1st) : N={fomo_n} | Losses={fomo_loss} ({fomo_loss/fomo_n*100:.0f}%) | PnL={fomo_pnl:+.2f}")
