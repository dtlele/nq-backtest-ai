"""
Pattern mining sui trade vincenti — tutte le sessioni storiche
Analizza: orario ET, setup, R:R, delta, volume, direzione, confidence
"""
import json, re, sys
from datetime import datetime, timezone
from collections import defaultdict
import pytz

ET = pytz.timezone("America/New_York")

# ── File da analizzare ──────────────────────────────────────────────
TRADES_FILES = [
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_ds_feb_no_money_mgmt.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_ds_feb_restrictive.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_ds_feb_wide_stops.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_jan2025.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_june.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_ds_feb_dynamic_mgmt_part1_no_apm.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_gemini_feb_week1.jsonl",
    r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log_pre_fix.jsonl",
]

REASONING_FILE = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl"

# ── Helper: estrai numeri dal reasoning ────────────────────────────
def extract_from_reasoning(text):
    if not text:
        return {}
    info = {}
    # Delta
    m = re.search(r'delta[:\s]+([+-]?\d+)', text, re.I)
    if m: info["delta"] = int(m.group(1))
    # Volume
    m = re.search(r'volume[:\s]+(\d+)', text, re.I)
    if m: info["volume"] = int(m.group(1))
    # Big Trades (contratti)
    m = re.search(r'(\d+)\s+(?:BUY|buy)', text)
    if m: info["big_buy"] = int(m.group(1))
    m = re.search(r'(\d+)\s+(?:SELL|sell)', text)
    if m: info["big_sell"] = int(m.group(1))
    # Setup keywords
    keywords = []
    for kw in ["absorption", "initiative", "imbalance", "breakout", "wick", "trapped", 
                "reversal", "exhaustion", "momentum", "IBL", "IBH", "POC", "VWAP",
                "value area", "delta flip", "Big Trade", "stop run"]:
        if kw.lower() in text.lower():
            keywords.append(kw)
    if keywords:
        info["keywords"] = keywords
    return info

# ── Carica tutti i trade vincenti ─────────────────────────────────
all_wins = []
all_losses = []
total_loaded = 0

for fpath in TRADES_FILES:
    try:
        with open(fpath, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    t = json.loads(line)
                except:
                    continue

                pnl = t.get("pnl_usd")
                if pnl is None: continue
                total_loaded += 1

                entry_raw = t.get("entry_time")
                if not entry_raw: continue
                try:
                    entry_dt = datetime.fromisoformat(entry_raw.replace("Z", "+00:00"))
                except:
                    continue

                entry_et = entry_dt.astimezone(ET)
                h, m = entry_et.hour, entry_et.minute
                time_slot = f"{h:02d}:{(m//15)*15:02d}"  # bucket a 15 min

                reasoning_text = str(t.get("fabio_reasoning", "")) + " " + str(t.get("andrea_reasoning", ""))
                extra = extract_from_reasoning(reasoning_text)

                record = {
                    "date":     t.get("date","?"),
                    "entry_et": entry_et.strftime("%H:%M"),
                    "time_h":   h,
                    "time_m":   m,
                    "time_slot": time_slot,
                    "direction": t.get("direction","?"),
                    "setup":    t.get("setup_type","?"),
                    "conf":     t.get("final_confidence"),
                    "r_ratio":  t.get("r_ratio"),
                    "pnl":      pnl,
                    "exit_reason": t.get("exit_reason","?"),
                    "source":   fpath.split("\\")[-1],
                    **extra,
                }

                if pnl > 0:
                    all_wins.append(record)
                else:
                    all_losses.append(record)
    except FileNotFoundError:
        pass

print(f"[INFO] Caricati {total_loaded} trade totali: {len(all_wins)} WIN / {len(all_losses)} LOSS")
print()

# ══════════════════════════════════════════════════════════════════
# ANALISI 1: Distribuzione oraria dei WIN vs LOSS
# ══════════════════════════════════════════════════════════════════
print("=" * 70)
print("ANALISI 1: WIN RATE PER FASCIA ORARIA (ET)")
print("=" * 70)

slot_wins   = defaultdict(int)
slot_losses = defaultdict(int)
slot_pnl    = defaultdict(float)

for t in all_wins:
    slot_wins[t["time_slot"]] += 1
    slot_pnl[t["time_slot"]] += t["pnl"]
for t in all_losses:
    slot_losses[t["time_slot"]] += 1
    slot_pnl[t["time_slot"]] += t["pnl"]

all_slots = sorted(set(list(slot_wins.keys()) + list(slot_losses.keys())))
print(f"  {'Slot':<8} {'W':>4} {'L':>4} {'WR%':>6} {'P&L':>10}")
print(f"  {'-'*8} {'-'*4} {'-'*4} {'-'*6} {'-'*10}")
for slot in all_slots:
    w = slot_wins[slot]
    l = slot_losses[slot]
    tot = w + l
    wr = w/tot*100 if tot else 0
    p = slot_pnl[slot]
    bar = "#" * int(wr/10)
    marker = " <<< BEST" if wr >= 60 and tot >= 3 else (" [LUNCH]" if 11 <= int(slot[:2]) < 14 else "")
    print(f"  {slot:<8} {w:>4} {l:>4} {wr:>5.0f}% {p:>+10.0f}  {bar}{marker}")

# ══════════════════════════════════════════════════════════════════
# ANALISI 2: WIN RATE PER CONFIDENCE LEVEL
# ══════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("ANALISI 2: WIN RATE PER CONFIDENCE LEVEL")
print("=" * 70)

conf_wins   = defaultdict(int)
conf_losses = defaultdict(int)
conf_pnl    = defaultdict(float)

for t in all_wins:
    c = t.get("conf")
    if c: conf_wins[c] += 1; conf_pnl[c] += t["pnl"]
for t in all_losses:
    c = t.get("conf")
    if c: conf_losses[c] += 1; conf_pnl[c] += t["pnl"]

print(f"  {'Conf':<6} {'W':>4} {'L':>4} {'WR%':>6} {'Avg WIN P&L':>12} {'P&L totale':>12}")
print(f"  {'-'*6} {'-'*4} {'-'*4} {'-'*6} {'-'*12} {'-'*12}")
for conf in sorted(set(list(conf_wins.keys()) + list(conf_losses.keys()))):
    w = conf_wins[conf]
    l = conf_losses[conf]
    tot = w + l
    wr = w/tot*100 if tot else 0
    avg_w_pnl = conf_pnl[conf]/tot if tot else 0
    marker = " <<< SWEET SPOT" if wr >= 60 and tot >= 3 else ""
    print(f"  {conf:<6} {w:>4} {l:>4} {wr:>5.0f}% {avg_w_pnl:>+12.0f} {conf_pnl[conf]:>+12.0f}{marker}")

# ══════════════════════════════════════════════════════════════════
# ANALISI 3: WIN RATE PER DIREZIONE E SETUP
# ══════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("ANALISI 3: WIN RATE PER DIREZIONE")
print("=" * 70)
dir_wins = defaultdict(int); dir_losses = defaultdict(int); dir_pnl = defaultdict(float)
for t in all_wins:   dir_wins[t["direction"]] += 1; dir_pnl[t["direction"]] += t["pnl"]
for t in all_losses: dir_losses[t["direction"]] += 1; dir_pnl[t["direction"]] += t["pnl"]
for d in sorted(set(list(dir_wins.keys())+list(dir_losses.keys()))):
    w=dir_wins[d]; l=dir_losses[d]; tot=w+l
    wr=w/tot*100 if tot else 0
    print(f"  {d.upper():<8} W:{w:>4} L:{l:>4} WR:{wr:>5.0f}% P&L:{dir_pnl[d]:>+10.0f}")

# ══════════════════════════════════════════════════════════════════
# ANALISI 4: R:R DISTRIBUTION SUI WIN
# ══════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("ANALISI 4: DISTRIBUZIONE R:R SUI TRADE (WIN vs LOSS)")
print("=" * 70)
rr_buckets = {"<1.0": [0,0], "1.0-1.5": [0,0], "1.5-2.0": [0,0], 
              "2.0-3.0": [0,0], "3.0-5.0": [0,0], ">5.0": [0,0]}
def rr_bucket(rr):
    if rr < 1.0: return "<1.0"
    elif rr < 1.5: return "1.0-1.5"
    elif rr < 2.0: return "1.5-2.0"
    elif rr < 3.0: return "2.0-3.0"
    elif rr < 5.0: return "3.0-5.0"
    else: return ">5.0"
for t in all_wins:
    if t.get("r_ratio"): rr_buckets[rr_bucket(t["r_ratio"])][0] += 1
for t in all_losses:
    if t.get("r_ratio"): rr_buckets[rr_bucket(t["r_ratio"])][1] += 1
print(f"  {'R:R':<10} {'WIN':>5} {'LOSS':>5} {'WR%':>6}")
print(f"  {'-'*10} {'-'*5} {'-'*5} {'-'*6}")
for bucket, (w, l) in rr_buckets.items():
    tot = w+l
    wr = w/tot*100 if tot else 0
    marker = " <<< BEST" if wr >= 60 and tot >= 3 else ""
    print(f"  {bucket:<10} {w:>5} {l:>5} {wr:>5.0f}%{marker}")

# ══════════════════════════════════════════════════════════════════
# ANALISI 5: KEYWORDS NEI REASONING DEI WIN vs LOSS
# ══════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("ANALISI 5: KEYWORDS NEL REASONING (WIN vs LOSS)")
print("=" * 70)
kw_wins = defaultdict(int); kw_losses = defaultdict(int)
for t in all_wins:
    for kw in t.get("keywords", []): kw_wins[kw] += 1
for t in all_losses:
    for kw in t.get("keywords", []): kw_losses[kw] += 1
all_kws = set(list(kw_wins.keys())+list(kw_losses.keys()))
print(f"  {'Keyword':<20} {'In WIN':>7} {'In LOSS':>8} {'Win%':>6}")
print(f"  {'-'*20} {'-'*7} {'-'*8} {'-'*6}")
for kw in sorted(all_kws, key=lambda k: kw_wins[k]/(kw_wins[k]+kw_losses[k]+0.001), reverse=True):
    w=kw_wins[kw]; l=kw_losses[kw]; tot=w+l
    wr=w/tot*100 if tot else 0
    marker = " <<< SEGNALE FORTE" if wr >= 65 and tot >= 5 else ""
    print(f"  {kw:<20} {w:>7} {l:>8} {wr:>5.0f}%{marker}")

# ══════════════════════════════════════════════════════════════════
# ANALISI 6: TOP 10 WIN per P&L — contesto specifico
# ══════════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("ANALISI 6: TOP 10 WIN per P&L (dettaglio completo)")
print("=" * 70)
top_wins = sorted(all_wins, key=lambda t: t["pnl"], reverse=True)[:10]
for i, t in enumerate(top_wins, 1):
    kws = ", ".join(t.get("keywords", [])[:4])
    delta = t.get("delta","?")
    vol   = t.get("volume","?")
    print(f"  #{i} {t['date']} {t['entry_et']} ET | {str(t['direction']).upper():<6} | P&L:${t['pnl']:>7.0f} | conf={t['conf']} | R:R={t['r_ratio']} | delta={delta} | vol={vol}")
    if kws: print(f"       Keywords: {kws}")

print()
print("=" * 70)
print("RIEPILOGO FINALE")
print("=" * 70)
total_pnl_w = sum(t["pnl"] for t in all_wins)
total_pnl_l = sum(t["pnl"] for t in all_losses)
wr_global = len(all_wins)/(len(all_wins)+len(all_losses))*100 if (all_wins or all_losses) else 0
print(f"  Trade WIN: {len(all_wins)} | Trade LOSS: {len(all_losses)} | WR: {wr_global:.0f}%")
print(f"  P&L WIN totale: ${total_pnl_w:+.0f} | P&L LOSS totale: ${total_pnl_l:+.0f}")
print(f"  P&L NETTO: ${total_pnl_w+total_pnl_l:+.0f}")
