"""
Analisi dettagliata: cosa intende esattamente il reasoning con IBH/IBL/VAH/VAL
Estrae il contesto testuale attorno alle menzioni nei trade WIN vs LOSS
"""
import json, re
from collections import defaultdict

ET_IMPORT = True
try:
    import pytz
    ET = pytz.timezone("America/New_York")
    from datetime import datetime, timezone
except:
    ET_IMPORT = False

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

# Pattern da cercare (case insensitive)
PATTERNS = {
    "IB_HIGH":      r'\b(IB[H_\s]?[Hh]igh|IBH|Initial Balance High|IB high|ib_high)\b',
    "IB_LOW":       r'\b(IB[L_\s]?[Ll]ow|IBL|Initial Balance Low|IB low|ib_low)\b',
    "VA_HIGH":      r'\b(VA[H_\s]?[Hh]igh|VAH|Value Area High|va_high|value area high)\b',
    "VA_LOW":       r'\b(VA[L_\s]?[Ll]ow|VAL|Value Area Low|va_low|value area low)\b',
    "POC":          r'\b(POC|Point of Control|point of control)\b',
    "BREAKOUT_IB":  r'(break\w*\s+(?:above|below|out|through)\s+(?:the\s+)?(?:IB|Initial Balance|IBH|IBL))',
    "BREAKOUT_VA":  r'(break\w*\s+(?:above|below|out|through)\s+(?:the\s+)?(?:VA|Value Area|VAH|VAL))',
    "ABOVE_IBH":    r'(above\s+(?:the\s+)?(?:IBH|IB\s*[Hh]igh|Initial Balance High))',
    "BELOW_IBL":    r'(below\s+(?:the\s+)?(?:IBL|IB\s*[Ll]ow|Initial Balance Low))',
    "ABOVE_VAH":    r'(above\s+(?:the\s+)?(?:VAH|VA\s*[Hh]igh|Value Area High))',
    "BELOW_VAL":    r'(below\s+(?:the\s+)?(?:VAL|VA\s*[Ll]ow|Value Area Low))',
}

# Contatori: per ogni pattern, quante volte appare in WIN vs LOSS
pattern_stats = {p: {"win": 0, "loss": 0, "win_pnl": 0.0, "loss_pnl": 0.0} for p in PATTERNS}

# Esempi di frasi estratte per ogni pattern
pattern_examples = {p: {"win": [], "loss": []} for p in PATTERNS}
MAX_EXAMPLES = 3

total_wins = 0
total_losses = 0

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
                if outcome == "win": total_wins += 1
                else: total_losses += 1

                # Combina tutti i campi testuali
                text = " ".join([
                    str(t.get("fabio_reasoning", "") or ""),
                    str(t.get("andrea_reasoning", "") or ""),
                ])

                for pat_name, pat_regex in PATTERNS.items():
                    matches = re.findall(pat_regex, text, re.IGNORECASE)
                    if matches:
                        pattern_stats[pat_name][outcome] += 1
                        pattern_stats[pat_name][f"{outcome}_pnl"] += pnl

                        # Salva esempi di frasi
                        if len(pattern_examples[pat_name][outcome]) < MAX_EXAMPLES:
                            # Estrai contesto (50 chars prima e dopo)
                            m = re.search(pat_regex, text, re.IGNORECASE)
                            if m:
                                start = max(0, m.start()-60)
                                end   = min(len(text), m.end()+80)
                                snippet = "..." + text[start:end].replace("\n"," ").strip() + "..."
                                pattern_examples[pat_name][outcome].append(snippet)
    except FileNotFoundError:
        pass

print(f"[INFO] {total_wins} WIN / {total_losses} LOSS analizzati\n")

print("=" * 80)
print("ANALISI: IBH/IBL vs VAH/VAL vs POC nei reasoning")
print(f"{'Pattern':<20} {'W cnt':>6} {'L cnt':>6} {'WR%':>6} {'P&L WIN':>10} {'P&L LOSS':>10}")
print("=" * 80)

for pat_name, stats in pattern_stats.items():
    w = stats["win"]
    l = stats["loss"]
    tot = w + l
    if tot == 0: continue
    wr = w/tot*100
    marker = " <<< FORTE" if wr >= 60 and tot >= 4 else (" [OK]" if wr >= 50 and tot >= 4 else "")
    print(f"{pat_name:<20} {w:>6} {l:>6} {wr:>5.0f}% {stats['win_pnl']:>+10.0f} {stats['loss_pnl']:>+10.0f}{marker}")

print()
print("=" * 80)
print("ESEMPI TESTUALI DAI REASONING")
print("=" * 80)

for pat_name in PATTERNS:
    w_ex = pattern_examples[pat_name]["win"]
    l_ex = pattern_examples[pat_name]["loss"]
    if not w_ex and not l_ex: continue

    print(f"\n--- {pat_name} ---")
    if w_ex:
        print("  WIN examples:")
        for ex in w_ex[:2]:
            print(f"    \"{ex[:150]}\"")
    if l_ex:
        print("  LOSS examples:")
        for ex in l_ex[:2]:
            print(f"    \"{ex[:150]}\"")

print()
print("=" * 80)
print("COMBINAZIONI PIU' FORTI (IBH/IBL + VAH/VAL insieme)")
print("=" * 80)

# Analisi combinazioni: IBH + VA, IBL + VA, ecc.
combos = {
    "IB_HIGH + VA_HIGH": (r'IBH|IB\s*[Hh]igh|Initial Balance High', r'VAH|VA\s*[Hh]igh|Value Area High'),
    "IB_LOW + VA_LOW":   (r'IBL|IB\s*[Ll]ow|Initial Balance Low',   r'VAL|VA\s*[Ll]ow|Value Area Low'),
    "IBH solo (no VAH)": "solo_IBH",
    "VAH solo (no IBH)": "solo_VAH",
    "IBL solo (no VAL)": "solo_IBL",
    "VAL solo (no IBL)": "solo_VAL",
}

combo_stats = {k: {"win":0,"loss":0,"wpnl":0.,"lpnl":0.} for k in combos}

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
                text = str(t.get("fabio_reasoning","")) + " " + str(t.get("andrea_reasoning",""))

                has_ibh = bool(re.search(r'IBH|IB\s*[Hh]igh|Initial Balance High', text, re.I))
                has_ibl = bool(re.search(r'IBL|IB\s*[Ll]ow|Initial Balance Low', text, re.I))
                has_vah = bool(re.search(r'VAH|VA\s*[Hh]igh|Value Area High', text, re.I))
                has_val = bool(re.search(r'VAL|VA\s*[Ll]ow|Value Area Low', text, re.I))

                def upd(k):
                    combo_stats[k][outcome] += 1
                    combo_stats[k]["wpnl" if outcome=="win" else "lpnl"] += pnl

                if has_ibh and has_vah: upd("IB_HIGH + VA_HIGH")
                if has_ibl and has_val: upd("IB_LOW + VA_LOW")
                if has_ibh and not has_vah: upd("IBH solo (no VAH)")
                if has_vah and not has_ibh: upd("VAH solo (no IBH)")
                if has_ibl and not has_val: upd("IBL solo (no VAL)")
                if has_val and not has_ibl: upd("VAL solo (no IBL)")
    except FileNotFoundError:
        pass

print(f"{'Combo':<25} {'W':>5} {'L':>5} {'WR%':>6} {'P&L netto':>12}")
print("-" * 60)
for k, s in combo_stats.items():
    w=s["win"]; l=s["loss"]; tot=w+l
    if tot==0: continue
    wr=w/tot*100
    net=s["wpnl"]+s["lpnl"]
    marker = " <<< MIGLIORE" if wr>=60 and tot>=3 else ""
    print(f"  {k:<23} {w:>5} {l:>5} {wr:>5.0f}% {net:>+12.0f}{marker}")
