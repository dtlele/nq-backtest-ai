import json
from collections import defaultdict

trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
reasoning_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl"

# Carica reasoning log, cerca "prefiltered" e decomponila per no_trade_reason
print("Carico reasoning log (8110 righe)...")
reasoning_rows = []
with open(reasoning_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            reasoning_rows.append(json.loads(line))
        except:
            pass

# Raggruppa i "prefiltered" per no_trade_reason
prefiltered = [r for r in reasoning_rows if r.get('decision') == 'prefiltered']
no_trade    = [r for r in reasoning_rows if r.get('decision') == 'no_trade']
traded      = [r for r in reasoning_rows if r.get('decision') == 'trade']
light_skip  = [r for r in reasoning_rows if r.get('decision') == 'light_skip']

print(f"\nDecisioni totali: {len(reasoning_rows)}")
print(f"  prefiltered : {len(prefiltered)}")
print(f"  no_trade    : {len(no_trade)}")
print(f"  light_skip  : {len(light_skip)}")
print(f"  trade       : {len(traded)}")

# Breakdown prefiltered per motivo
print("\n=== PREFILTERED — BREAKDOWN PER MOTIVO ===")
pf_reasons = defaultdict(lambda: {'n': 0, 'vols': []})
for r in prefiltered:
    reason = r.get('no_trade_reason', '?')
    pf_reasons[reason]['n'] += 1
    pf_reasons[reason]['vols'].append(r.get('bar_volume', 0))

for reason, v in sorted(pf_reasons.items(), key=lambda x: -x[1]['n']):
    avg_vol = sum(v['vols']) / len(v['vols']) if v['vols'] else 0
    print(f"  [{v['n']:4d}x] avg_vol={avg_vol:6.0f} | {reason}")

# Cerca esplicitamente "volume" nelle no_trade_reason
print("\n=== PREFILTERED con 'volume' nel motivo ===")
vol_prefiltered = [r for r in prefiltered if 'volume' in str(r.get('no_trade_reason', '')).lower()]
print(f"  Trovati: {len(vol_prefiltered)}")
for r in vol_prefiltered[:10]:
    print(f"  {r.get('date')} {r.get('bar_time_et')} | vol={r.get('bar_volume',0)} | reason={r.get('no_trade_reason','')}")

# Cerca nei no_trade
print("\n=== NO_TRADE con 'volume' nel motivo ===")
vol_no_trade = [r for r in no_trade if 'volume' in str(r.get('no_trade_reason', '')).lower()]
print(f"  Trovati: {len(vol_no_trade)}")
for r in vol_no_trade[:10]:
    print(f"  {r.get('date')} {r.get('bar_time_et')} | vol={r.get('bar_volume',0)} | reason={r.get('no_trade_reason','')}")

# Distribuzione volume dei trade ESEGUITI
print("\n=== DISTRIBUZIONE VOLUME DEI TRADE ESEGUITI ===")
buckets = defaultdict(lambda: {'n': 0, 'wins': 0, 'pnl': 0.0})

# Carica trades
trades = []
with open(trades_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            trades.append(json.loads(line))
        except:
            pass

# match reasoning -> trade per data/ora
reasoning_by_key = {}
for r in reasoning_rows:
    if r.get('decision') == 'trade':
        key = (r.get('date', ''), r.get('bar_time_et', ''))
        reasoning_by_key[key] = r

import datetime, pytz
matched = 0
for t in trades:
    date_str = t.get('date', '')
    entry_time_str = t.get('entry_time', '')
    try:
        dt = datetime.datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
        dt_et = dt.astimezone(pytz.timezone("America/New_York"))
        et_str = dt_et.strftime("%H:%M")
    except:
        continue
    
    pnl = t.get('pnl_usd', 0)
    win = pnl > 0
    
    # Cerca il matching reasoning
    r = reasoning_by_key.get((date_str, et_str))
    if not r:
        # cerca +-5 min
        h_t, m_t = dt_et.hour, dt_et.minute
        best = None
        best_diff = 999
        for (d2, t2), rv in reasoning_by_key.items():
            if d2 != date_str:
                continue
            h2, m2 = map(int, t2.split(':'))
            diff = abs((h_t*60+m_t) - (h2*60+m2))
            if diff < best_diff and diff <= 5:
                best_diff = diff
                best = rv
        r = best
    
    if r:
        matched += 1
        vol = r.get('bar_volume', 0)
        # bucket per 1000
        bucket = (vol // 1000) * 1000
        buckets[bucket]['n'] += 1
        buckets[bucket]['pnl'] += pnl
        if win:
            buckets[bucket]['wins'] += 1

print(f"  Trades matchati con reasoning: {matched}/{len(trades)}")
print(f"  {'Volume Bucket':15} | {'N':4} | {'WR%':6} | {'PnL':>10}")
print(f"  {'-'*45}")
for bucket in sorted(buckets.keys()):
    v = buckets[bucket]
    n = v['n']
    wr = v['wins']/n*100 if n > 0 else 0
    label = f"{bucket}-{bucket+999}"
    print(f"  {label:15} | {n:4d} | {wr:5.1f}% | {v['pnl']:>+10.2f}")

# Summary: sotto vs sopra 4500
print("\n=== CONFRONTO: trades vol < 4500 vs >= 4500 ===")
under_n, under_w, under_pnl = 0, 0, 0.0
over_n, over_w, over_pnl    = 0, 0, 0.0
for bucket, v in buckets.items():
    mid = bucket + 500
    if mid < 4500:
        under_n += v['n']; under_w += v['wins']; under_pnl += v['pnl']
    else:
        over_n += v['n']; over_w += v['wins']; over_pnl += v['pnl']

print(f"  Vol < 4500 : N={under_n:3d} | WR={under_w/under_n*100:.1f}% | PnL={under_pnl:+.2f}" if under_n else "  Vol < 4500 : nessun dato")
print(f"  Vol >= 4500: N={over_n:3d} | WR={over_w/over_n*100:.1f}% | PnL={over_pnl:+.2f}" if over_n else "  Vol >= 4500: nessun dato")
