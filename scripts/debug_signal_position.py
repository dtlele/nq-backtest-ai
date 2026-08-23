"""
Analisi segnali speculari: verifica se long e short appaiono
sullo stesso timestamp o a distanza ravvicinata (bug di posizionamento).
Verifica anche la logica della wick detection.
"""
import os, glob
import pandas as pd
import numpy as np
from datetime import time

DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"

SESSION_BLOCKS = [
    (time(9, 45), time(12, 0)),
    (time(13, 30), time(15, 15)),
]
MIN_SIZE = 80
MAX_SIZE = 150

# ─── Carica un campione di giorni e mostra i segnali con dettagli wick ────────
files = sorted(glob.glob(os.path.join(DATA_DIR, "glbx-mdp3-*.trades.csv")))[:10]

all_signals = []

for filepath in files:
    df = pd.read_csv(filepath, usecols=['ts_event', 'price', 'size', 'side'])
    df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True, errors='coerce')
    df.dropna(subset=['ts_event', 'price', 'size'], inplace=True)
    df.sort_values('ts_event', inplace=True)

    # Filtro tick corrotti
    median_p = df['price'].median()
    df = df[(df['price'] >= median_p * 0.90) & (df['price'] <= median_p * 1.10)].copy()
    if df.empty:
        continue

    df['ts_eastern'] = df['ts_event'].dt.tz_convert('US/Eastern')
    t = df['ts_eastern'].dt.time
    mask = pd.Series(False, index=df.index)
    for t_start, t_end in SESSION_BLOCKS:
        mask |= (t >= t_start) & (t < t_end)
    df = df[mask].copy()
    if df.empty:
        continue

    df = df[df['side'].isin(['A', 'B'])].copy()
    if df.empty:
        continue

    df['minute'] = df['ts_eastern'].dt.floor('1min')

    bars = df.groupby('minute').agg(
        open=('price', 'first'),
        high=('price', 'max'),
        low=('price', 'min'),
        close=('price', 'last'),
    )

    # Whale print per minuto
    idx_max = df.groupby('minute')['size'].idxmax()
    wp = df.loc[idx_max, ['minute', 'price', 'size', 'side']].set_index('minute')
    wp.columns = ['wp_price', 'wp_size', 'wp_side']
    bars = bars.join(wp)

    size_ok   = (bars['wp_size'] >= MIN_SIZE) & (bars['wp_size'] <= MAX_SIZE)
    body_high = bars[['open', 'close']].max(axis=1)
    body_low  = bars[['open', 'close']].min(axis=1)
    on_upper  = bars['wp_price'] >= body_high
    on_lower  = bars['wp_price'] <= body_low
    on_wick   = on_upper | on_lower

    sigs = bars[size_ok & on_wick].copy()
    sigs['on_upper'] = on_upper[sigs.index]
    sigs['on_lower'] = on_lower[sigs.index]
    sigs['body_high'] = body_high[sigs.index]
    sigs['body_low']  = body_low[sigs.index]

    # Segnale v2 (con direzione basata su side)
    sigs['signal_v2'] = 0
    sigs.loc[sigs['wp_side'] == 'A', 'signal_v2'] =  1   # LONG
    sigs.loc[sigs['wp_side'] == 'B', 'signal_v2'] = -1   # SHORT

    # Segnale alternativo (basato sulla posizione del wick, non sul side)
    sigs['signal_wick'] = 0
    sigs.loc[sigs['on_upper'], 'signal_wick'] = -1  # upper wick = SHORT (rejection)
    sigs.loc[sigs['on_lower'], 'signal_wick'] =  1  # lower wick = LONG  (rejection)
    # Nota: se sia upper che lower sono True (caso doji), segnale ambiguo

    all_signals.append(sigs)

if not all_signals:
    print("Nessun segnale trovato")
    exit()

res = pd.concat(all_signals)

print("=== SEGNALI WHALE PRINT - ANALISI WICK ===")
print(f"Totale segnali in 10 giorni: {len(res)}")
print()

print("Distribuzione wick position + side:")
for side in ['A', 'B']:
    for wick in ['upper', 'lower', 'both']:
        if wick == 'upper':
            mask = (res['wp_side'] == side) & res['on_upper'] & ~res['on_lower']
        elif wick == 'lower':
            mask = (res['wp_side'] == side) & res['on_lower'] & ~res['on_upper']
        else:
            mask = (res['wp_side'] == side) & res['on_upper'] & res['on_lower']
        n = mask.sum()
        if n > 0:
            print(f"  side={side} + {wick} wick: {n} segnali")

print()

# Verifica: ci sono DOJI (body_high == body_low) che generano segnali ambigui?
doji = res[res['on_upper'] & res['on_lower']]
print(f"Barre DOJI (wp_price soddisfa sia upper che lower wick): {len(doji)}")
if len(doji) > 0:
    print(doji[['open', 'high', 'low', 'close', 'wp_price', 'wp_size', 'wp_side']].head(10).to_string())
print()

# Verifica: segnali a timestamp consecutivi o sovrapposti
print("=== SEGNALI RAVVICINATI (< 2 minuti di distanza) ===")
res_sorted = res.sort_index()
res_sorted['prev_ts'] = res_sorted.index.to_series().shift(1)
res_sorted['gap_min'] = (res_sorted.index.to_series() - res_sorted['prev_ts']).dt.total_seconds() / 60
close_signals = res_sorted[res_sorted['gap_min'] <= 2].copy()
print(f"Segnali entro 2 minuti dal precedente: {len(close_signals)}")
if len(close_signals) > 0:
    print(close_signals[['gap_min','wp_size','wp_side','on_upper','on_lower','signal_v2']].head(20).to_string())
print()

print("=== CAMPIONE SEGNALI CON DETTAGLI ===")
print(res[['open','high','low','close','wp_price','wp_size','wp_side',
           'on_upper','on_lower','body_high','body_low','signal_v2','signal_wick']].head(30).to_string())
