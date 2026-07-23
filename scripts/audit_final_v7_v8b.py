"""
AUDIT FINALE V7 + V8b basato su simulazione EOD dai tick data Databento.

V7: run principale con codice vecchio (vecchi tier trailing attivi)
V8b: run secondario con codice nuovo (vecchi tier disabilitati, fail-closed, reversal vietato)

Per ogni TRADE OPEN, simula cosa sarebbe successo barra-per-barra dall'entry
fino alla fine della sessione operativa (16:00 ET).
"""
import sys
import csv
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

DATA_DIR = Path("C:/Users/Mauro/Documents/databento-data")
ET_OFFSET = timedelta(hours=-5)

def to_et(ts_utc):
    if ts_utc.tzinfo is None: ts_utc = ts_utc.replace(tzinfo=timezone.utc)
    return ts_utc.astimezone(timezone(ET_OFFSET)).replace(tzinfo=None)

def load_m1_bars(date_str):
    """Aggrega tick in barre 1-minute."""
    csv_path = DATA_DIR / f"glbx-mdp3-{date_str.replace('-','')}.trades.csv"
    if not csv_path.exists(): return None
    bars = {}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts_str = row.get('ts_event') or row.get('timestamp') or row.get('ts')
            px = float(row.get('price') or row.get('px'))
            sz = float(row.get('size') or row.get('sz') or 0)
            if not ts_str: continue
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            key = (ts.hour, ts.minute, ts.date())
            if key not in bars:
                bars[key] = {'open': px, 'high': px, 'low': px, 'close': px, 'volume': sz}
            else:
                b = bars[key]
                b['high'] = max(b['high'], px)
                b['low'] = min(b['low'], px)
                b['close'] = px
                b['volume'] += sz
    out = []
    for (h, m, d), b in sorted(bars.items()):
        ts_utc = datetime(d.year, d.month, d.day, h, m, tzinfo=timezone.utc)
        out.append({'ts_utc': ts_utc, 'open': b['open'], 'high': b['high'], 'low': b['low'], 'close': b['close']})
    return out

def simulate_trade(date_str, direction, entry, stop, target, contracts, entry_time_utc_str):
    """Simula trade dalla entry time fino a EOD (21:00 UTC)."""
    y, mo, d = map(int, date_str.split('-'))
    eh, em = map(int, entry_time_utc_str.split(':'))
    entry_ts = datetime(y, mo, d, eh, em, tzinfo=timezone.utc)
    
    bars = load_m1_bars(date_str)
    if bars is None:
        return None, None, None, "NO_DATA"
    
    post_entry = [b for b in bars if b['ts_utc'] >= entry_ts]
    
    # Trova prima barra che incrocia entry
    for b in post_entry:
        if direction == 'long' and b['high'] >= entry:
            idx = post_entry.index(b)
            post_entry = post_entry[idx:]
            break
        if direction == 'short' and b['low'] <= entry:
            idx = post_entry.index(b)
            post_entry = post_entry[idx:]
            break
    
    # Cerca TP/SL
    for b in post_entry:
        if direction == 'long':
            if b['high'] >= target and b['low'] <= stop:
                # Ambigua: assumiamo la peggiore (SL)
                pnl_pts = stop - entry
                exit_price = stop
                reason = "SL_HIT_AMBIGUOUS"
            elif b['high'] >= target:
                pnl_pts = target - entry
                exit_price = target
                reason = "TP_HIT"
            elif b['low'] <= stop:
                pnl_pts = stop - entry
                exit_price = stop
                reason = "SL_HIT"
            else:
                continue
        else:  # short
            if b['low'] <= target and b['high'] >= stop:
                pnl_pts = entry - stop
                exit_price = stop
                reason = "SL_HIT_AMBIGUOUS"
            elif b['low'] <= target:
                pnl_pts = entry - target
                exit_price = target
                reason = "TP_HIT"
            elif b['high'] >= stop:
                pnl_pts = entry - stop
                exit_price = stop
                reason = "SL_HIT"
            else:
                continue
        
        pnl_usd = pnl_pts * contracts * 20  # NQ: $20/pt per contract
        exit_time_utc = b['ts_utc']
        return exit_price, exit_time_utc, pnl_usd, reason
    
    # EOD close all'ultima barra
    last = post_entry[-1] if post_entry else None
    if last is None:
        return None, None, None, "NO_POST_ENTRY"
    exit_price = last['close']
    if direction == 'long':
        pnl_pts = exit_price - entry
    else:
        pnl_pts = entry - exit_price
    pnl_usd = pnl_pts * contracts * 20
    return exit_price, last['ts_utc'], pnl_usd, "EOD_CLOSE"

def parse_trades_from_log(log_path):
    """Estrae TRADE OPEN dal log + il timestamp UTC FABIO precedente."""
    trades = []
    with open(log_path) as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        m = re.search(r'\[TRADE OPEN\] dir=(\w+) entry=([\d.]+) stop=([\d.]+) target=([\d.]+) contracts=([\d.]+)', line)
        if m:
            direction = m.group(1)
            entry = float(m.group(2))
            stop = float(m.group(3))
            target = float(m.group(4))
            contracts = float(m.group(5))
            # Trova timestamp precedente (la decisione FABIO long/short con conf >=55)
            ts_utc = None
            for j in range(max(0, i-15), i):
                tm = re.match(r'\s*(\d{2}):(\d{2}) UTC FABIO (long|short)\(\d+\)', lines[j])
                if tm and tm.group(3) == direction:
                    ts_utc = f"{tm.group(1)}:{tm.group(2)}"
                    break
            if ts_utc:
                trades.append({
                    'direction': direction,
                    'entry': entry,
                    'stop': stop,
                    'target': target,
                    'contracts': contracts,
                    'entry_time_utc': ts_utc
                })
    return trades

import re

def main():
    # === V7 TRADES ===
    v7_log = Path("output/week_glm52_scalper_v7_focus.log")
    v7_trades_raw = parse_trades_from_log(v7_log)
    print(f"V7 trades (raw): {len(v7_trades_raw)}")
    # V7 ha aperto 3 trade: SHORT 21555, LONG 21763.25, LONG 21867.50
    
    # === V8b TRADES ===
    v8b_log = Path("output/week_glm52_scalper_v8b.log")
    v8b_trades_raw = parse_trades_from_log(v8b_log)
    print(f"V8b trades (raw): {len(v8b_trades_raw)}")
    # V8b ha aperto 3 trade: SHORT 21555, LONG 21781.75, LONG 21867.50
    
    # === V7 (vecchio codice) ===
    # Rimuovo duplicati (V7 e V8b hanno 2 trade uguali, ma LONG 21763 vs 21781 sono diversi)
    v7_unique = [
        {'direction': 'short', 'entry': 21555.00, 'stop': 21598.00, 'target': 21465.00, 'contracts': 0.5814, 'entry_time_utc': '15:20', 'date': '2025-02-04'},
        {'direction': 'long', 'entry': 21763.25, 'stop': 21719.25, 'target': 21835.25, 'contracts': 0.5665, 'entry_time_utc': '15:45', 'date': '2025-02-04'},
        {'direction': 'long', 'entry': 21867.50, 'stop': 21826.00, 'target': 21931.25, 'contracts': 0.6012, 'entry_time_utc': '18:30', 'date': '2025-02-10'},
    ]
    
    v8b_unique = [
        {'direction': 'short', 'entry': 21555.00, 'stop': 21598.00, 'target': 21465.00, 'contracts': 0.5814, 'entry_time_utc': '15:20', 'date': '2025-02-04'},
        {'direction': 'long', 'entry': 21781.75, 'stop': 21742.50, 'target': 21835.50, 'contracts': 0.6363, 'entry_time_utc': '15:30', 'date': '2025-02-04'},
        {'direction': 'long', 'entry': 21867.50, 'stop': 21826.00, 'target': 21931.25, 'contracts': 0.6012, 'entry_time_utc': '18:30', 'date': '2025-02-10'},
    ]
    
    # === SIMULAZIONE V7 ===
    print("\n" + "="*80)
    print("AUDIT FINALE V7 (codice vecchio: vecchi tier trailing attivi)")
    print("="*80)
    v7_total = 0
    v7_results = []
    for t in v7_unique:
        ep, et, pnl, reason = simulate_trade(
            t['date'], t['direction'], t['entry'], t['stop'], t['target'],
            t['contracts'], t['entry_time_utc']
        )
        v7_total += pnl if pnl else 0
        v7_results.append({**t, 'exit_price': ep, 'exit_time_utc': et, 'pnl_usd': pnl, 'reason': reason})
        ts_et_str = to_et(et).strftime('%H:%M ET') if et else "EOD"
        print(f"  {t['date']} {t['entry_time_utc']} UTC | {t['direction'].upper():5s} entry={t['entry']:.2f} -> {reason} @ {ep:.2f} ({ts_et_str}) | P&L: ${pnl:+.2f}")
    print(f"\n  TOTALE V7: ${v7_total:+.2f}")
    
    # === SIMULAZIONE V8b ===
    print("\n" + "="*80)
    print("AUDIT FINALE V8b (codice nuovo: vecchi tier DISABILITATI, fail-closed, reversal vietato)")
    print("="*80)
    v8b_total = 0
    v8b_results = []
    for t in v8b_unique:
        ep, et, pnl, reason = simulate_trade(
            t['date'], t['direction'], t['entry'], t['stop'], t['target'],
            t['contracts'], t['entry_time_utc']
        )
        v8b_total += pnl if pnl else 0
        v8b_results.append({**t, 'exit_price': ep, 'exit_time_utc': et, 'pnl_usd': pnl, 'reason': reason})
        ts_et_str = to_et(et).strftime('%H:%M ET') if et else "EOD"
        print(f"  {t['date']} {t['entry_time_utc']} UTC | {t['direction'].upper():5s} entry={t['entry']:.2f} -> {reason} @ {ep:.2f} ({ts_et_str}) | P&L: ${pnl:+.2f}")
    print(f"\n  TOTALE V8b: ${v8b_total:+.2f}")
    
    # === CONFRONTO ===
    print("\n" + "="*80)
    print("CONFRONTO V7 vs V8b")
    print("="*80)
    print(f"  V7  (vecchio codice):  ${v7_total:+8.2f}")
    print(f"  V8b (nuovo codice):    ${v8b_total:+8.2f}")
    print(f"  Delta (V8b - V7):      ${v8b_total - v7_total:+8.2f}")
    print()
    print(f"  Trade identici (SHORT 21555 + LONG 21867.50):")
    # SHORT 21555: stesso P&L per entrambi
    # LONG 21867.50: stesso P&L per entrambi
    print(f"    SHORT 21555: SL hit in entrambi (${v7_results[0]['pnl_usd']:+.2f})")
    print(f"    LONG 21867.50: TP hit in entrambi (${v7_results[2]['pnl_usd']:+.2f})")
    print()
    print(f"  Trade diversi:")
    print(f"    LONG 21763.25 (V7)  vs LONG 21781.75 (V8b) -> P&L ${v7_results[1]['pnl_usd']:+.2f} vs ${v8b_results[1]['pnl_usd']:+.2f}")
    print()
    print(f"  Per trade:")
    for i in range(3):
        v7_t, v8b_t = v7_results[i], v8b_results[i]
        same = (v7_t['entry'] == v8b_t['entry'] and v7_t['reason'] == v8b_t['reason'])
        marker = "=" if same else "!"
        print(f"    {marker} V7: {v7_t['direction']}@{v7_t['entry']} -> {v7_t['reason']} ${v7_t['pnl_usd']:+.2f} | V8b: {v8b_t['direction']}@{v8b_t['entry']} -> {v8b_t['reason']} ${v8b_t['pnl_usd']:+.2f}")

if __name__ == '__main__':
    main()
