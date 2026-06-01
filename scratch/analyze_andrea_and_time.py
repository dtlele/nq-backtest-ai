import json
from datetime import datetime, timezone
import pytz

TRADES_LOG = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
ET = pytz.timezone("America/New_York")

START = datetime(2025, 4, 3, tzinfo=timezone.utc)
END   = datetime(2025, 4, 16, tzinfo=timezone.utc)

LUNCH_START = (11, 0)
LUNCH_END   = (14, 30)

trades = []
with open(TRADES_LOG, "r", encoding="utf-8-sig") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            t = json.loads(line)
        except:
            continue

        entry_raw = t.get("entry_time")
        if not entry_raw:
            continue
        try:
            entry_dt = datetime.fromisoformat(entry_raw.replace("Z", "+00:00"))
        except:
            continue

        if not (START <= entry_dt < END):
            continue

        # Outcome da exit_reason o pnl_usd
        pnl = t.get("pnl_usd")
        if pnl is None:
            continue
        outcome = "win" if pnl > 0 else "loss"

        # Andrea confidence: cerca nel andrea_reasoning
        andrea_conf = None
        andrea_r = t.get("andrea_reasoning", "")
        # Prova a estrarre "confidence": XX dal reasoning
        import re
        m = re.search(r'"confidence"\s*:\s*(\d+)', andrea_r or "")
        if m:
            andrea_conf = int(m.group(1))
        # oppure cerca "score": XX
        if andrea_conf is None:
            m = re.search(r'"score"\s*:\s*(\d+)', andrea_r or "")
            if m:
                andrea_conf = int(m.group(1))

        entry_et = entry_dt.astimezone(ET)
        h, m_min = entry_et.hour, entry_et.minute

        def is_lunch(h, m):
            after = (h > LUNCH_START[0]) or (h == LUNCH_START[0] and m >= LUNCH_START[1])
            before = (h < LUNCH_END[0]) or (h == LUNCH_END[0] and m < LUNCH_END[1])
            return after and before

        trades.append({
            "date":        t.get("date"),
            "entry_utc":   entry_dt,
            "entry_et":    entry_et.strftime("%H:%M"),
            "direction":   t.get("direction","?"),
            "setup":       t.get("setup_type","?"),
            "fabio_conf":  t.get("final_confidence"),
            "andrea_conf": andrea_conf,
            "outcome":     outcome,
            "pnl":         pnl,
            "r_ratio":     t.get("r_ratio"),
            "is_lunch":    is_lunch(h, m_min),
            "exit_reason": t.get("exit_reason","?"),
        })

print(f"Trovati {len(trades)} trade nel range Apr 03-15 2025\n")

if not trades:
    print("  Log non contiene trade Apr 03-15. Forse questa run non ha ancora scritto nel trades_log.")
    exit()

# ── DETTAGLIO COMPLETO ──────────────────────────────────────────────
print("=" * 80)
print("DETTAGLIO TUTTI I TRADE")
print("=" * 80)
print(f"{'Data':<12} {'ET':<7} {'Dir':<6} {'Setup':<20} {'Fab':<5} {'And':<5} {'R:R':<5} {'Esito':<6} {'P&L':>8}")
print("-" * 80)
for t in sorted(trades, key=lambda x: x["entry_utc"]):
    lunch_tag = " [LUNCH]" if t["is_lunch"] else ""
    and_str = str(t["andrea_conf"]) if t["andrea_conf"] is not None else "N/A"
    rr_str  = f"{t['r_ratio']:.1f}" if t["r_ratio"] else "?"
    print(f"{t['date']:<12} {t['entry_et']:<7} {str(t['direction']).upper():<6} {str(t['setup'])[:19]:<20} {str(t['fabio_conf']):<5} {and_str:<5} {rr_str:<5} {t['outcome'].upper():<6} ${t['pnl']:>7.2f}{lunch_tag}")

# ── ANALISI 1: ANDREA VETO ──────────────────────────────────────────
print()
print("=" * 80)
print("ANALISI 1: ANDREA VETO — soglia 40 vs 60")
print("=" * 80)

has_andrea = [t for t in trades if t["andrea_conf"] is not None]
if not has_andrea:
    print("  ⚠️  andrea_confidence NON trovata nei reasoning log.")
    print("  Il campo andrea_reasoning non contiene un JSON con 'confidence'.")
    print("  Mostro andrea_reasoning di esempio:")
    with open(TRADES_LOG, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            t = json.loads(line)
            if t.get("date","") >= "2025-04-03" and t.get("date","") <= "2025-04-15":
                ar = t.get("andrea_reasoning","")
                if ar:
                    print(f"  Esempio: {ar[:300]}")
                    break
else:
    def stat(lst):
        w = sum(1 for t in lst if t["outcome"]=="win")
        l = sum(1 for t in lst if t["outcome"]=="loss")
        pnl = sum(t["pnl"] for t in lst)
        wr = w/len(lst)*100 if lst else 0
        return len(lst), w, l, wr, pnl

    k40 = [t for t in trades if t["andrea_conf"] >= 40]
    k60 = [t for t in trades if t["andrea_conf"] >= 60]
    vetoed = [t for t in trades if 40 <= t["andrea_conf"] < 60]

    n40,w40,l40,wr40,pnl40 = stat(k40)
    n60,w60,l60,wr60,pnl60 = stat(k60)

    print(f"  Soglia 40: {n40} trade | W:{w40} L:{l40} | WR:{wr40:.0f}% | P&L: ${pnl40:+.2f}")
    print(f"  Soglia 60: {n60} trade | W:{w60} L:{l60} | WR:{wr60:.0f}% | P&L: ${pnl60:+.2f}")
    print(f"  Differenza P&L: ${pnl60-pnl40:+.2f} | Trade eliminati: {len(vetoed)}")
    if vetoed:
        print(f"\n  Trade che andrebbero VETATI alzando a 60 (andrea 40-59):")
        for t in vetoed:
            print(f"    {t['date']} {t['entry_et']} ET | {t['direction'].upper()} | andrea={t['andrea_conf']} | {t['outcome'].upper()} | ${t['pnl']:+.2f}")

# ── ANALISI 2: LUNCH FILTER ─────────────────────────────────────────
print()
print("=" * 80)
print("ANALISI 2: FILTRO LUNCH (11:00–14:30 ET)")
print("=" * 80)

lunch = [t for t in trades if t["is_lunch"]]
no_lunch = [t for t in trades if not t["is_lunch"]]

nl, wl, ll, wrl, pnll = stat(lunch)
nn, wn, ln, wrn, pnln = stat(no_lunch)

print(f"  IN LUNCH  (11:00-14:30 ET): {nl} trade | W:{wl} L:{ll} | WR:{wrl:.0f}% | P&L: ${pnll:+.2f}")
print(f"  FUORI lunch:               {nn} trade | W:{wn} L:{ln} | WR:{wrn:.0f}% | P&L: ${pnln:+.2f}")
print(f"  Guadagno eliminando lunch: ${pnln - (pnll+pnln):+.2f} → totale senza lunch: ${pnln:+.2f}")

if lunch:
    print(f"\n  Trade in finestra LUNCH:")
    for t in sorted(lunch, key=lambda x: x["entry_utc"]):
        print(f"    {t['date']} {t['entry_et']} ET | {str(t['direction']).upper():<5} | conf={t['fabio_conf']} | {t['outcome'].upper()} | ${t['pnl']:+.2f}")
