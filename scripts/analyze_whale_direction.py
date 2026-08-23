"""
Analisi direzionale whale print: capire quale direzione funziona davvero
e se la logica wick rejection e' migliore di follow-the-order.
"""
import pandas as pd
import numpy as np
import os, glob
from datetime import time

DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
OUT_CSV  = r"C:\Users\Mauro\Documents\nq-backtest\output\whale_v2_results.csv"

# ── Analisi risultati esistenti ──────────────────────────────────────────────
df = pd.read_csv(OUT_CSV)

print("=== WIN RATE PER DIREZIONE ===")
for d in ['LONG', 'SHORT']:
    sub = df[df['direction'] == d]
    wr = (sub['net_pnl'] > 0).mean() * 100
    avg = sub['net_pnl'].mean()
    print(f"  {d}: n={len(sub)}, WR={wr:.1f}%, avg_pnl=${avg:.2f}")

print()
print("=== WIN RATE PER EXIT REASON ===")
for r in df['exit_reason'].unique():
    sub = df[df['exit_reason'] == r]
    wr = (sub['net_pnl'] > 0).mean() * 100
    avg = sub['net_pnl'].mean()
    print(f"  {r}: n={len(sub)}, WR={wr:.1f}%, avg_pnl=${avg:.2f}")

# ── Analisi su dati grezzi: cosa succede ai prezzi nei 15 min dopo un whale print ──
print()
print("=== ANALISI PREDITTIVA SU DATI RAW ===")
print("Caricamento 30 file per analisi statistica rapida...")

MIN_SIZE = 80
MAX_SIZE = 150

results = []

files = sorted(glob.glob(os.path.join(DATA_DIR, "glbx-mdp3-*.trades.csv")))[:60]

for filepath in files:
    try:
        df_raw = pd.read_csv(filepath, usecols=['ts_event', 'price', 'size', 'side'])
    except Exception:
        continue

    df_raw['ts_event'] = pd.to_datetime(df_raw['ts_event'], utc=True, errors='coerce')
    df_raw.dropna(subset=['ts_event', 'price', 'size'], inplace=True)
    df_raw.sort_values('ts_event', inplace=True)
    df_raw['ts_eastern'] = df_raw['ts_event'].dt.tz_convert('US/Eastern')

    # Filtro prezzi corrotti (tick level)
    median_p = df_raw['price'].median()
    df_raw = df_raw[(df_raw['price'] >= median_p * 0.90) & (df_raw['price'] <= median_p * 1.10)].copy()
    if df_raw.empty:
        continue

    # RTH completo per il contesto forward
    t = df_raw['ts_eastern'].dt.time
    rth = df_raw[(t >= time(9, 30)) & (t < time(16, 0))].copy()
    if rth.empty:
        continue

    rth = rth[rth['side'].isin(['A', 'B'])].copy()
    rth['minute'] = rth['ts_eastern'].dt.floor('1min')

    bars = rth.groupby('minute').agg(
        open=('price', 'first'), high=('price', 'max'),
        low=('price', 'min'), close=('price', 'last')
    )

    idx_max = rth.groupby('minute')['size'].idxmax()
    wp = rth.loc[idx_max, ['minute', 'price', 'size', 'side']].set_index('minute')
    wp.columns = ['wp_price', 'wp_size', 'wp_side']
    bars = bars.join(wp)

    size_ok = (bars['wp_size'] >= MIN_SIZE) & (bars['wp_size'] <= MAX_SIZE)
    body_high = bars[['open', 'close']].max(axis=1)
    body_low  = bars[['open', 'close']].min(axis=1)
    on_upper_wick = bars['wp_price'] >= body_high
    on_lower_wick = bars['wp_price'] <= body_low

    signals = bars[size_ok & (on_upper_wick | on_lower_wick)].copy()
    signals['on_upper'] = on_upper_wick[signals.index]
    signals['on_lower'] = on_lower_wick[signals.index]

    bar_list = bars.index.tolist()

    for ts, row in signals.iterrows():
        idx = bar_list.index(ts)
        if idx + 15 >= len(bar_list):
            continue
        entry_p = bars['open'].iloc[idx + 1]
        future_p = bars['close'].iloc[idx + 15]
        fwd_move = future_p - entry_p  # positivo = salita

        results.append({
            'wp_side': row['wp_side'],
            'on_upper': row['on_upper'],
            'on_lower': row['on_lower'],
            'wp_size': row['wp_size'],
            'fwd_move_15min': fwd_move,
        })

res = pd.DataFrame(results)
print(f"Segnali analizzati: {len(res)}")
print()

if len(res) > 0:
    print("=== PREVISIONE A 15 MIN PER COMBINAZIONE WICK + SIDE ===")
    print("(fwd_move_15min > 0 = salita = LONG vincente)")
    print()

    combos = [
        ("Upper wick + side=A (big BUY al top)", res['on_upper'] & (res['wp_side'] == 'A')),
        ("Upper wick + side=B (big SELL al top)", res['on_upper'] & (res['wp_side'] == 'B')),
        ("Lower wick + side=A (big BUY al bottom)", res['on_lower'] & (res['wp_side'] == 'A')),
        ("Lower wick + side=B (big SELL al bottom)", res['on_lower'] & (res['wp_side'] == 'B')),
    ]

    for label, mask in combos:
        sub = res[mask]
        if len(sub) == 0:
            print(f"  {label}: nessun dato")
            continue
        pct_up   = (sub['fwd_move_15min'] > 0).mean() * 100
        avg_move = sub['fwd_move_15min'].mean()
        print(f"  {label}")
        print(f"    n={len(sub)}, % prezzo sale={pct_up:.1f}%, avg move={avg_move:+.2f} pts")
        print()

    print("=== IPOTESI WICK REJECTION (upper=SHORT, lower=LONG) ===")
    wr_upper_short = (res[res['on_upper']]['fwd_move_15min'] < 0).mean() * 100
    wr_lower_long  = (res[res['on_lower']]['fwd_move_15min'] > 0).mean() * 100
    print(f"  Upper wick -> SHORT: {wr_upper_short:.1f}% vincente a 15 min")
    print(f"  Lower wick -> LONG:  {wr_lower_long:.1f}% vincente a 15 min")

    print()
    print("=== IPOTESI FOLLOW ORDER (side=A->LONG, side=B->SHORT) ===")
    wr_A_long  = (res[res['wp_side'] == 'A']['fwd_move_15min'] > 0).mean() * 100
    wr_B_short = (res[res['wp_side'] == 'B']['fwd_move_15min'] < 0).mean() * 100
    print(f"  side=A -> LONG:  {wr_A_long:.1f}% vincente a 15 min")
    print(f"  side=B -> SHORT: {wr_B_short:.1f}% vincente a 15 min")
