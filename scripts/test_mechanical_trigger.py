"""
Test offline del trigger meccanico sul 04/02.
Verifica se evaluate_candidate() trova gli stessi trade aperti dalla V7/V8b
(almeno SHORT 21555 e LONG 21633/21781, idealmente LONG 21867 del 10/02).
"""

import sys
import json
import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, '.')

from src.agents.daily_map import generate_daily_map, DailyMap, _build_default_map, compute_bias_from_data
from src.agents.mechanical_trigger import evaluate_candidate, is_in_no_trade_zone
from src import Bar, SessionContext, CandidateBar

DATA_DIR = Path("C:/Users/Mauro/Documents/databento-data")

ET = timezone(timedelta(hours=-5))

# Trade che vogliamo trovare (dai log V7/V8b)
TARGET_TRADES_04 = [
    ('short', 21555.00, 21598.00, 21465.00, '15:20 UTC'),
    ('long', 21634.00, 21610.94, 21694.00, '15:30 UTC (V1 03/02)'),
    ('long', 21763.25, 21719.25, 21835.25, '15:45 UTC (V7 04/02)'),
    ('long', 21781.75, 21742.50, 21835.50, '15:30 UTC (V8b 04/02)'),
]
TARGET_TRADES_10 = [
    ('long', 21867.50, 21826.00, 21931.25, '18:30 UTC (V8b 10/02)'),
]


def build_m5_bars_from_csv(date_str, target_minutes):
    """Carica tick data e aggrega in M5 bars. Ritorna lista di Bar."""
    csv_path = DATA_DIR / f"glbx-mdp3-{date_str.replace('-', '')}.trades.csv"
    if not csv_path.exists():
        return []
    
    # Aggrega in M5
    buckets = {}
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts_str = row.get('ts_event') or row.get('timestamp') or row.get('ts')
            px = float(row.get('price') or row.get('px'))
            sz = float(row.get('size') or row.get('sz') or 0)
            if not ts_str: continue
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            # 5-minute bucket
            bucket = ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)
            if bucket not in buckets:
                buckets[bucket] = {
                    'open': px, 'high': px, 'low': px, 'close': px, 'volume': sz,
                    'delta': 0, 'big_trades': []
                }
            else:
                b = buckets[bucket]
                b['high'] = max(b['high'], px)
                b['low'] = min(b['low'], px)
                b['close'] = px
                b['volume'] += sz
    
    # Converti in oggetti Bar
    bars = []
    for ts, b in sorted(buckets.items()):
        bar = Bar(
            timestamp=ts, open=b['open'], high=b['high'], low=b['low'], close=b['close'],
            volume=int(b['volume']), buy_volume=int(b['volume']/2), sell_volume=int(b['volume']/2),
            delta=0, delta_pct=0.0, cvd=0, vwap=b['close'], big_trades=[]
        )
        bars.append(bar)
    return bars


def fake_session_context(bar, ib_high=21640, ib_low=21580, ib_range=60):
    """Costruisce un SessionContext minimalista per il test."""
    return SessionContext(
        date=bar.timestamp.strftime('%Y-%m-%d'),
        ib_high=ib_high, ib_low=ib_low, ib_range=ib_range, ib_complete=True,
        vp=None, prev_day_vp=None, atr_5day=80
    )


def fake_candidate(bar, ctx, wall_price=0, wall_size=0, wall_count=0):
    """Costruisce un CandidateBar minimalista."""
    return CandidateBar(
        bar=bar, session_ctx=ctx,
        wall_level=wall_price, wall_side='buy' if wall_price < bar.close else 'sell',
        wall_trade_count=wall_count, wall_max_size=wall_size,
        proximity_to='poc', proximity_level=bar.close,
        bars_in_session=20, is_second_test=False,
        setup_category='momentum',
        recent_bars=[bar] * 6
    )


def main():
    # Test 1: 04/02 - mappa deterministica + scan tutte le M5
    print("="*80)
    print("TEST 1: 04/02 - trigger meccanico con mappa deterministica")
    print("="*80)
    
    date_str = "2025-02-04"
    bars = build_m5_bars_from_csv(date_str, None)
    print(f"Barre M5 caricate: {len(bars)}")
    
    if not bars:
        print("ERRORE: nessuna barra caricata")
        return
    
    # Filtra solo barre 14:00-21:00 UTC (10:00-17:00 ET, RTH)
    rth_bars = [b for b in bars if 14 <= b.timestamp.hour < 21]
    print(f"Barre RTH (14-21 UTC): {len(rth_bars)}")
    
    # Crea mappa deterministica
    ctx = fake_session_context(rth_bars[0])
    regime, score, reasoning = compute_bias_from_data(ctx, rth_bars[:20])
    print(f"Bias deterministico: {regime} (score={score}) - {reasoning}")
    
    daily_map = _build_default_map(
        date_str, regime, score, reasoning, llm_conf=50
    )
    # Riempi primary_levels con valori realistici per 04/02
    daily_map.primary_levels = {
        'poc': 21590.0,  # 04/02 era 21590 circa
        'vah': 21640.0,
        'val': 21540.0,
        'ib_high': 21638.0,
        'ib_low': 21560.0,
    }
    
    # Scan tutte le barre RTH
    verdicts = []
    debug_count = 0
    target_check = ['15:30', '15:45', '16:00']  # orari noti V7
    for i, bar in enumerate(rth_bars):
        # Prova con wall al prezzo IB high (pullback scenario)
        # Per long: wall = IB_high (21638), si vuole close > wall
        # Per short: wall = IB_low (21560), si vuole close < wall
        # Usa wall dalla barra: se la barra sta testando un livello, usa quello
        wall = daily_map.primary_levels.get('ib_high', 21638)
        if bar.close < bar.open:  # bearish bar, metti wall sopra
            wall = daily_map.primary_levels.get('ib_high', 21638)
        else:  # bullish bar
            wall = daily_map.primary_levels.get('ib_low', 21560)
        
        cand = fake_candidate(bar, ctx, wall_price=wall, wall_size=300, wall_count=3)
        v = evaluate_candidate(cand, rth_bars[max(0, i-5):i+1], daily_map, ctx)
        ts_str = bar.timestamp.strftime('%H:%M')
        is_target = ts_str in target_check
        if v.decision == 'open':
            verdicts.append((bar, v))
            print(f"\n>>> OPEN @ {bar.timestamp.strftime('%H:%M UTC')}")
            print(f"    direction={v.direction} score={v.confidence} setup={v.setup_type}")
            print(f"    sl={v.sl} tp={v.tp} rr={v.rr:.2f}")
            print(f"    bar: O={bar.open} H={bar.high} L={bar.low} C={bar.close} V={bar.volume}")
        elif is_target:
            print(f"\n[TARGET {ts_str}] verdict={v.decision} score={v.confidence} reasons={v.reasons[:2]}")
            print(f"   bar: O={bar.open:.2f} H={bar.high:.2f} L={bar.low:.2f} C={bar.close:.2f}")
        elif debug_count < 3 and bar.timestamp.hour == 15 and bar.timestamp.minute < 20:
            print(f"\n[DEBUG] {ts_str} C={bar.close:.2f} O={bar.open:.2f} V={bar.volume} close_gt_open={(bar.close > bar.open)}")
            print(f"  Verdict: {v.decision} score={v.confidence} reasons={v.reasons[:2]}")
            debug_count += 1
    
    print(f"\nTotale trade aperti dal trigger meccanico: {len(verdicts)}")
    
    # Test 2: confronto con target V7/V8b
    print("\n" + "="*80)
    print("TEST 2: Confronto con trade noti V7/V8b")
    print("="*80)
    
    for direction, entry, stop, target, label in TARGET_TRADES_04:
        # Trova la barra piu' vicina all'entry noto
        matching = None
        for bar, v in verdicts:
            if abs(bar.close - entry) < 5 and v.direction == direction:
                matching = (bar, v)
                break
        
        if matching:
            bar, v = matching
            print(f"\n[MATCH] {label}: {direction.upper()} @ {bar.timestamp.strftime('%H:%M UTC')}")
            print(f"  Expected: entry={entry} stop={stop} target={target}")
            print(f"  Got:      sl={v.sl} tp={v.tp}")
            print(f"  Status: entry match={'OK' if abs(bar.close - entry) < 5 else 'CLOSE'}")
        else:
            print(f"\n[NO MATCH] {label}: {direction.upper()} @ {entry} not found in {len(verdicts)} open trades")
    
    # Test 3: 10/02 - LONG 21867.50
    print("\n" + "="*80)
    print("TEST 3: 10/02 - LONG 21867.50 (V8b)")
    print("="*80)
    
    date_str_10 = "2025-02-10"
    bars_10 = build_m5_bars_from_csv(date_str_10, None)
    rth_bars_10 = [b for b in bars_10 if 14 <= b.timestamp.hour < 21]
    print(f"Barre M5 10/02: {len(rth_bars_10)}")
    
    ctx_10 = fake_session_context(rth_bars_10[0])
    regime_10, score_10, _ = compute_bias_from_data(ctx_10, rth_bars_10[:20])
    print(f"Bias 10/02: {regime_10} (score={score_10})")
    
    daily_map_10 = _build_default_map(date_str_10, regime_10, score_10, "deterministic", 50)
    daily_map_10.primary_levels = {
        'poc': 21860.0,
        'vah': 21890.0,
        'val': 21830.0,
        'ib_high': 21860.0,
        'ib_low': 21795.0,
    }
    
    verdicts_10 = []
    for i, bar in enumerate(rth_bars_10):
        cand = fake_candidate(bar, ctx_10, wall_price=21866, wall_size=165, wall_count=1)
        v = evaluate_candidate(cand, rth_bars_10[max(0, i-5):i+1], daily_map_10, ctx_10)
        if v.decision == 'open':
            verdicts_10.append((bar, v))
    
    print(f"Trade aperti 10/02: {len(verdicts_10)}")
    for bar, v in verdicts_10[:5]:
        print(f"  {bar.timestamp.strftime('%H:%M UTC')} {v.direction} entry~={bar.close} score={v.confidence}")
    
    # Cerca LONG 21867
    long_21867 = [b for b, v in verdicts_10 if v.direction == 'long' and abs(b.close - 21867.50) < 10]
    if long_21867:
        print(f"\n[MATCH] LONG 21867.50 found!")
    else:
        print(f"\n[NO MATCH] LONG 21867.50 not found by mechanical trigger")
    
    # Stampa TUTTE le barre 18:30 UTC del 10/02 con verdict
    print(f"\n[DEBUG 10/02] Barre 18:25-18:35 UTC:")
    for bar in rth_bars_10:
        ts_str = bar.timestamp.strftime('%H:%M')
        if ts_str in ['18:25', '18:30', '18:35']:
            wall = 21866
            cand = fake_candidate(bar, ctx_10, wall_price=wall, wall_size=165, wall_count=1)
            v = evaluate_candidate(cand, rth_bars_10[max(0, rth_bars_10.index(bar)-5):rth_bars_10.index(bar)+1], daily_map_10, ctx_10)
            print(f"  {ts_str} C={bar.close:.2f} O={bar.open:.2f} H={bar.high:.2f} L={bar.low:.2f} → verdict={v.decision} score={v.confidence}")
    
    print("\n" + "="*80)
    print("RIEPILOGO")
    print("="*80)
    print(f"04/02: {len(verdicts)} trade dal trigger meccanico")
    print(f"10/02: {len(verdicts_10)} trade dal trigger meccanico")
    print("\nNOTA: questi trade sono con mappa DETERMINISTICA.")
    print("La mappa LLM potrebbe aprire trade diversi o diversi livelli.")


if __name__ == '__main__':
    main()
