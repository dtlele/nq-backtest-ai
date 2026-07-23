"""
Simula l'esito EOD di un trade rimasto aperto alla fine della sessione operativa.
Legge i tick data grezzi dal CSV Databento e ripercorre minuto per minuto dall'entry.

Uso:
  python scripts/simulate_open_trade_eod.py 2025-02-10 long 21867.50 21826.00 21931.25 0.6012
"""
import sys
import csv
from pathlib import Path
from datetime import datetime, timezone, timedelta

DATA_DIR = Path("C:/Users/Mauro/Documents/databento-data")
ET_OFFSET = timedelta(hours=-5)  # EST

def to_et(ts_utc):
    return ts_utc.astimezone(timezone(ET_OFFSET)).replace(tzinfo=None)

def load_m1_bars(date_str):
    """Carica barre 1-minute dal CSV Databento. Aggrega i tick in M1."""
    csv_path = DATA_DIR / f"glbx-mdp3-{date_str.replace('-','')}.trades.csv"
    if not csv_path.exists():
        return None
    bars = {}  # (h, m) -> {open, high, low, close, volume}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts_str = row.get('ts_event') or row.get('timestamp') or row.get('ts')
            px = float(row.get('price') or row.get('px'))
            sz = float(row.get('size') or row.get('sz') or 0)
            if not ts_str: continue
            # ts in formato "2025-02-10T14:30:00.000Z" o simile
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            # Tronca al minuto
            minute_key = (ts.hour, ts.minute, ts.date())
            if minute_key not in bars:
                bars[minute_key] = {'open': px, 'high': px, 'low': px, 'close': px, 'volume': sz}
            else:
                b = bars[minute_key]
                b['high'] = max(b['high'], px)
                b['low'] = min(b['low'], px)
                b['close'] = px
                b['volume'] += sz
    # Converti in lista ordinata con timestamp
    out = []
    for (h, m, d), b in sorted(bars.items()):
        ts_utc = datetime(d.year, d.month, d.day, h, m, tzinfo=timezone.utc)
        out.append({'ts_utc': ts_utc, 'open': b['open'], 'high': b['high'], 'low': b['low'], 'close': b['close']})
    return out

def simulate_trade(date_str, direction, entry, stop, target, contracts):
    print(f"=== Simulazione trade {direction.upper()} ===")
    print(f"  Date: {date_str}")
    print(f"  Entry: {entry} | Stop: {stop} | Target: {target} | Contracts: {contracts}")
    print()
    
    bars = load_m1_bars(date_str)
    if bars is None:
        print(f"ERRORE: dati non trovati per {date_str}")
        return
    
    # Converti entry in UTC: 18:30 UTC = 13:30 ET del 10/02
    # L'entry è avvenuta a una certa ora ET. Troviamo la prima barra con close >= entry (per long)
    # o close <= entry (per short).
    entry_hour_utc = 18  # 18:30 UTC
    entry_min_utc = 30
    
    print(f"  Barre totali caricate: {len(bars)}")
    print(f"  Trade aperto durante l'elaborazione. Cerco barre post-entry...")
    print()
    
    # Filtra barre >= entry time
    # Parse date_str YYYY-MM-DD per estrarre anno/mese/giorno
    y, mo, d = map(int, date_str.split('-'))
    entry_ts = datetime(y, mo, d, entry_hour_utc, entry_min_utc, tzinfo=timezone.utc)
    post_entry = [b for b in bars if b['ts_utc'] >= entry_ts]
    print(f"  Barre post-entry (da {entry_ts.strftime('%H:%M')} UTC): {len(post_entry)}")
    
    if not post_entry:
        print("ERRORE: nessuna barra post-entry")
        return
    
    # Per long: controlla se high >= target (TP) o low <= stop (SL)
    # Per short: controlla se low <= target (TP) o high >= stop (SL)
    # La prima barra che colpisce vince.

    print()
    print(f"  {'Time UTC':<10} {'Time ET':<10} {'O':>10} {'H':>10} {'L':>10} {'C':>10} {'Status':<10}")
    print(f"  {'-'*70}")

    # Determina la prima barra che incrocia l'entry price (così' filtriamo barre irrelevanti)
    entry_crossed = None
    for b in post_entry:
        if direction == 'long' and b['high'] >= entry:
            entry_crossed = b
            break
        if direction == 'short' and b['low'] <= entry:
            entry_crossed = b
            break
    if entry_crossed:
        # Filtra da questa barra in poi
        idx = post_entry.index(entry_crossed)
        post_entry = post_entry[idx:]

    for b in post_entry:
        ts_et = to_et(b['ts_utc'])
        status = ""
        
        if direction == 'long':
            # Controlla TP e SL — la barra che colpisce per prima vince (worst case: SL prima del TP)
            # In realta' dipende dall'ordine, assumiamo high >= target prima di low <= stop (piu' ottimistico)
            if b['high'] >= target and b['low'] <= stop:
                status = "AMBIGUOUS (high&low)"
            elif b['high'] >= target:
                status = "TP HIT"
            elif b['low'] <= stop:
                status = "SL HIT"
        else:  # short
            if b['low'] <= target and b['high'] >= stop:
                status = "AMBIGUOUS (high&low)"
            elif b['low'] <= target:
                status = "TP HIT"
            elif b['high'] >= stop:
                status = "SL HIT"
        
        print(f"  {b['ts_utc'].strftime('%H:%M'):<10} {ts_et.strftime('%H:%M'):<10} "
              f"{b['open']:>10.2f} {b['high']:>10.2f} {b['low']:>10.2f} {b['close']:>10.2f} {status}")
        
        if status and 'HIT' in status:
            # Calcola P&L
            if 'TP' in status:
                exit_price = target
                pnl_pts = (target - entry) if direction == 'long' else (entry - target)
            elif 'SL' in status:
                exit_price = stop
                pnl_pts = (stop - entry) if direction == 'long' else (entry - stop)
            else:
                # ambiguous, scegli il peggiore
                if direction == 'long':
                    exit_price = stop  # pessimistic
                    pnl_pts = (stop - entry)
                else:
                    exit_price = stop
                    pnl_pts = (entry - stop)
            
            pnl_usd = pnl_pts * contracts * 20  # NQ: 1pt = $20 per contract
            ts_et_str = ts_et.strftime('%H:%M ET')
            print()
            print(f"  >>> ESITO: {status} a {ts_et_str}")
            print(f"  >>> Exit: {exit_price} | P&L: {pnl_pts:+.1f}pt = ${pnl_usd:+.2f}")
            return
    
    # Nessun hit, EOD close all'ultima barra
    last_bar = post_entry[-1]
    exit_price = last_bar['close']
    pnl_pts = (exit_price - entry) if direction == 'long' else (entry - exit_price)
    pnl_usd = pnl_pts * contracts * 20
    ts_et_str = to_et(last_bar['ts_utc']).strftime('%H:%M ET')
    print()
    print(f"  >>> ESITO: nessun TP/SL hit, EOD close")
    print(f"  >>> EOD close: {exit_price} a {ts_et_str}")
    print(f"  >>> P&L: {pnl_pts:+.1f}pt = ${pnl_usd:+.2f}")

def main():
    if len(sys.argv) < 7:
        print("Uso: python simulate_open_trade_eod.py YYYY-MM-DD long|short entry stop target contracts")
        print("Esempio: python simulate_open_trade_eod.py 2025-02-10 long 21867.50 21826.00 21931.25 0.6012")
        sys.exit(1)
    
    date_str = sys.argv[1]
    direction = sys.argv[2]
    entry = float(sys.argv[3])
    stop = float(sys.argv[4])
    target = float(sys.argv[5])
    contracts = float(sys.argv[6])
    
    simulate_trade(date_str, direction, entry, stop, target, contracts)

if __name__ == '__main__':
    main()
