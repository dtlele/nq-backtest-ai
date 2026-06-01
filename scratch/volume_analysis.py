"""
Analisi volume alla rottura: WIN vs LOSS
Estrae il volume della candela di ingresso dal reasoning e dal reasoning_log
"""
import json, re
from collections import defaultdict

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

REASONING_LOG = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl"

def extract_volume_from_text(text):
    """Estrae il volume della candela dal testo del reasoning"""
    if not text:
        return None
    # Pattern tipo: "volume of 1234", "volume: 1234", "volume (1234)", "1234 contracts"
    patterns = [
        r'volume\s*(?:of|:|\(|=)?\s*(\d{3,6})',
        r'(\d{3,6})\s*contracts?\b',
        r'bar\s+volume[:\s]+(\d{3,6})',
        r'vol[:\s=]+(\d{3,6})',
        r'total\s+volume[:\s]+(\d{3,6})',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            v = int(m.group(1))
            if 100 <= v <= 200000:  # range ragionevole per NQ
                return v
    return None

def extract_big_trade_size(text):
    """Estrae la dimensione del Big Trade principale"""
    if not text:
        return None
    # Pattern: "484 BUY", "367 SELL", "Big Trade: 384 contracts BUY"
    patterns = [
        r'(\d{2,4})\s+(?:BUY|buy|Buy)',
        r'(\d{2,4})\s+(?:SELL|sell|Sell)',
        r'Big\s+Trade[:\s]+(\d{2,4})',
        r'(\d{2,4})\s+contracts?\s+(?:BUY|SELL)',
    ]
    sizes = []
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            v = int(m.group(1))
            if 10 <= v <= 5000:
                sizes.append(v)
    return max(sizes) if sizes else None

def extract_delta(text):
    """Estrae il delta dal reasoning"""
    if not text:
        return None
    m = re.search(r'delta[:\s]+([+-]?\d+)', text, re.IGNORECASE)
    if m:
        v = int(m.group(1))
        if -50000 <= v <= 50000:
            return v
    return None

# Carica trades e abbina con reasoning_log per avere bar_volume
print("Caricamento reasoning_log per dati volume precisi...")
reasoning_by_time = {}
try:
    with open(REASONING_LOG, "r", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                r = json.loads(line)
            except:
                continue
            # Usa entry_time o bar_time come chiave
            key = r.get("bar_time_utc") or r.get("entry_time") or r.get("timestamp")
            vol = r.get("bar_volume")
            delta = r.get("bar_delta")
            if key and (vol or delta):
                reasoning_by_time[key] = {
                    "bar_volume": vol,
                    "bar_delta": delta,
                }
except FileNotFoundError:
    pass
print(f"  reasoning_log entries con volume: {len(reasoning_by_time)}")

# Analisi principale
win_volumes = []
loss_volumes = []
win_big_trades = []
loss_big_trades = []
win_deltas = []
loss_deltas = []

win_pnls_by_vol = []   # (volume, pnl)
loss_pnls_by_vol = []

skipped_no_vol = 0

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
                outcome = "win" if pnl > 0 else "loss"

                text = str(t.get("fabio_reasoning","") or "") + " " + str(t.get("andrea_reasoning","") or "")

                # Prova prima dal reasoning_log (dati precisi)
                entry_key = t.get("entry_time","")
                bar_data = reasoning_by_time.get(entry_key, {})
                vol   = bar_data.get("bar_volume") or extract_volume_from_text(text)
                delta = bar_data.get("bar_delta")  or extract_delta(text)
                big_t = extract_big_trade_size(text)

                if vol:
                    if outcome == "win":
                        win_volumes.append(vol)
                        win_pnls_by_vol.append((vol, pnl))
                    else:
                        loss_volumes.append(vol)
                        loss_pnls_by_vol.append((vol, pnl))
                else:
                    skipped_no_vol += 1

                if big_t:
                    if outcome == "win": win_big_trades.append(big_t)
                    else: loss_big_trades.append(big_t)

                if delta is not None:
                    if outcome == "win": win_deltas.append(abs(delta))
                    else: loss_deltas.append(abs(delta))

    except FileNotFoundError:
        pass

def avg(lst): return sum(lst)/len(lst) if lst else 0
def median(lst):
    if not lst: return 0
    s = sorted(lst)
    n = len(s)
    return s[n//2]

print(f"\nTrade con volume estratto: WIN={len(win_volumes)}, LOSS={len(loss_volumes)}")
print(f"Trade senza volume: {skipped_no_vol}")

print()
print("=" * 65)
print("ANALISI VOLUME ALLA CANDELA DI INGRESSO")
print("=" * 65)
print(f"  {'Metrica':<25} {'WIN':>12} {'LOSS':>12}")
print(f"  {'-'*25} {'-'*12} {'-'*12}")
print(f"  {'N trade con volume':<25} {len(win_volumes):>12} {len(loss_volumes):>12}")
if win_volumes and loss_volumes:
    print(f"  {'Media volume':<25} {avg(win_volumes):>12.0f} {avg(loss_volumes):>12.0f}")
    print(f"  {'Mediana volume':<25} {median(win_volumes):>12.0f} {median(loss_volumes):>12.0f}")
    print(f"  {'Volume minimo':<25} {min(win_volumes):>12.0f} {min(loss_volumes):>12.0f}")
    print(f"  {'Volume massimo':<25} {max(win_volumes):>12.0f} {max(loss_volumes):>12.0f}")

    ratio = avg(win_volumes)/avg(loss_volumes) if avg(loss_volumes) else 0
    print(f"\n  Rapporto media WIN/LOSS: {ratio:.2f}x")
    if ratio > 1.1:
        print("  >>> I WIN hanno volume MAGGIORE alla rottura (+)")
    elif ratio < 0.9:
        print("  >>> I WIN hanno volume MINORE alla rottura (-)")
    else:
        print("  >>> Volume simile tra WIN e LOSS")

print()
print("=" * 65)
print("ANALISI BIG TRADE SIZE (contratti istituzionali)")
print("=" * 65)
print(f"  {'Metrica':<25} {'WIN':>12} {'LOSS':>12}")
print(f"  {'-'*25} {'-'*12} {'-'*12}")
if win_big_trades and loss_big_trades:
    print(f"  {'N con Big Trade':<25} {len(win_big_trades):>12} {len(loss_big_trades):>12}")
    print(f"  {'Media Big Trade':<25} {avg(win_big_trades):>12.0f} {avg(loss_big_trades):>12.0f}")
    print(f"  {'Mediana Big Trade':<25} {median(win_big_trades):>12.0f} {median(loss_big_trades):>12.0f}")
    ratio_bt = avg(win_big_trades)/avg(loss_big_trades) if avg(loss_big_trades) else 0
    print(f"\n  Rapporto media WIN/LOSS: {ratio_bt:.2f}x")
    if ratio_bt > 1.15:
        print("  >>> I WIN hanno Big Trade PIU' GRANDI (+)")
    elif ratio_bt < 0.85:
        print("  >>> I WIN hanno Big Trade PIU' PICCOLI")
    else:
        print("  >>> Big Trade size simile tra WIN e LOSS")

print()
print("=" * 65)
print("ANALISI DELTA ASSOLUTO")
print("=" * 65)
if win_deltas and loss_deltas:
    print(f"  {'Metrica':<25} {'WIN':>12} {'LOSS':>12}")
    print(f"  {'-'*25} {'-'*12} {'-'*12}")
    print(f"  {'N con delta':<25} {len(win_deltas):>12} {len(loss_deltas):>12}")
    print(f"  {'Media |delta|':<25} {avg(win_deltas):>12.0f} {avg(loss_deltas):>12.0f}")
    print(f"  {'Mediana |delta|':<25} {median(win_deltas):>12.0f} {median(loss_deltas):>12.0f}")
    ratio_d = avg(win_deltas)/avg(loss_deltas) if avg(loss_deltas) else 0
    print(f"\n  Rapporto media WIN/LOSS: {ratio_d:.2f}x")

print()
print("=" * 65)
print("BUCKET VOLUME: WR% per fascia di volume")
print("=" * 65)

# Unisci tutti i trade con volume
all_trades_vol = [(v, pnl, "win") for v, pnl in win_pnls_by_vol] + \
                 [(v, pnl, "loss") for v, pnl in loss_pnls_by_vol]

buckets = [
    ("Molto basso (<500)",   0,    500),
    ("Basso (500-1000)",     500,  1000),
    ("Medio (1000-2000)",    1000, 2000),
    ("Alto (2000-4000)",     2000, 4000),
    ("Molto alto (>4000)",   4000, 999999),
]

print(f"  {'Bucket volume':<25} {'W':>5} {'L':>5} {'WR%':>6} {'P&L netto':>12}")
print(f"  {'-'*25} {'-'*5} {'-'*5} {'-'*6} {'-'*12}")
for label, lo, hi in buckets:
    subset = [(v, pnl, o) for v, pnl, o in all_trades_vol if lo <= v < hi]
    w = sum(1 for _, _, o in subset if o=="win")
    l = sum(1 for _, _, o in subset if o=="loss")
    tot = w+l
    if tot == 0: continue
    wr = w/tot*100
    net = sum(pnl for _, pnl, _ in subset)
    marker = " <<< SWEET SPOT" if wr >= 55 and tot >= 5 else ""
    print(f"  {label:<25} {w:>5} {l:>5} {wr:>5.0f}% {net:>+12.0f}{marker}")
