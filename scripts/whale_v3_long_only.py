"""
WHALE PRINT STRATEGY v3 - LONG ONLY
Basato sull'analisi statistica dei dati reali:
  - LONG: WR=43.5%, avg_pnl=+$69  ✓
  - SHORT: WR=1.4%, avg_pnl=-$84  ✗ (distrugge il PnL)
  - Upper wick + side=B -> 60.7% prezzo sale -> LONG, non SHORT
  - Tutte le whale prints su wick vengono usate come segnale LONG
  
Cambiamenti rispetto v2:
  1. Solo LONG (niente short)
  2. Rimosso confirm check (era basato sulla direzione sbagliata)
  3. Filtro tick corrotti su TUTTO il file (gia' dalla v2)
  4. SL=20 pts, TP=60 pts fissi (R:R 1:3)
"""

import os, glob
import pandas as pd
import numpy as np
from datetime import time

# ─── PARAMETRI ────────────────────────────────────────────────────────────────
DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
OUT_DIR  = r"C:\Users\Mauro\Documents\nq-backtest\output"
OUT_CSV  = os.path.join(OUT_DIR, "whale_v3_long_only.csv")

MIN_SIZE = 80
MAX_SIZE = 150

SESSION_BLOCKS = [
    (time(9, 45), time(12, 0)),
    (time(13, 30), time(15, 15)),
]

SL_PTS   = 20.0
TP_PTS   = 60.0

FIXED_RISK_USD     = 100.0
POINT_VALUE_MNQ    = 2.0
COMMISSION_PER_MNQ = 1.40
SLIPPAGE_USD       = 5.00

MAX_HOLD_BARS = 30
# ──────────────────────────────────────────────────────────────────────────────

def load_bars(filepath: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(filepath, usecols=['ts_event', 'price', 'size', 'side'])
    except Exception:
        return pd.DataFrame()

    df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True, errors='coerce')
    df.dropna(subset=['ts_event', 'price', 'size'], inplace=True)
    df.sort_values('ts_event', inplace=True)

    # Filtro tick corrotti: mediana su TUTTO il file (prima di qualsiasi filtro)
    median_p = df['price'].median()
    if pd.isna(median_p) or median_p <= 0:
        return pd.DataFrame()
    df = df[(df['price'] >= median_p * 0.90) & (df['price'] <= median_p * 1.10)].copy()
    if df.empty:
        return pd.DataFrame()

    df['ts_eastern'] = df['ts_event'].dt.tz_convert('US/Eastern')

    # Filtra orari gold RTH
    t = df['ts_eastern'].dt.time
    mask = pd.Series(False, index=df.index)
    for t_start, t_end in SESSION_BLOCKS:
        mask |= (t >= t_start) & (t < t_end)
    df = df[mask].copy()
    if df.empty:
        return pd.DataFrame()

    df = df[df['side'].isin(['A', 'B'])].copy()
    if df.empty:
        return pd.DataFrame()

    df['minute'] = df['ts_eastern'].dt.floor('1min')

    bars = df.groupby('minute').agg(
        open=('price', 'first'),
        high=('price', 'max'),
        low=('price', 'min'),
        close=('price', 'last'),
        volume=('size', 'sum')
    )

    idx_max = df.groupby('minute')['size'].idxmax()
    wp = df.loc[idx_max, ['minute', 'price', 'size', 'side']].set_index('minute')
    wp.columns = ['wp_price', 'wp_size', 'wp_side']
    bars = bars.join(wp)

    # Filtro size whale
    size_ok = (bars['wp_size'] >= MIN_SIZE) & (bars['wp_size'] <= MAX_SIZE)

    # Location: whale print su wick (sopra o sotto il corpo)
    body_high = bars[['open', 'close']].max(axis=1)
    body_low  = bars[['open', 'close']].min(axis=1)
    on_wick   = (bars['wp_price'] >= body_high) | (bars['wp_price'] <= body_low)

    # SOLO LONG: tutti i whale print su wick = segnale long
    # (analisi statistica mostra side=A e side=B su wick entrambi tendono
    #  ad avere prezzo che sale a 15min, specialmente upper wick + side=B = 60.7%)
    bars['signal'] = 0
    bars.loc[size_ok & on_wick, 'signal'] = 1  # LONG

    return bars


def run_backtest():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "glbx-mdp3-*.trades.csv")))
    print(f"Caricamento {len(files)} file Databento...")

    all_bars = []
    for i, f in enumerate(files):
        b = load_bars(f)
        if not b.empty:
            all_bars.append(b)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(files)} processati...")

    df = pd.concat(all_bars).sort_index()
    df = df[~df.index.duplicated(keep='first')]
    print(f"Barre 1-min totali: {len(df)}")

    signals = df[df['signal'] == 1]
    print(f"Segnali LONG totali: {len(signals)}")

    mnq_qty = max(1, int(round(FIXED_RISK_USD / (SL_PTS * POINT_VALUE_MNQ))))
    pv   = POINT_VALUE_MNQ * mnq_qty
    cost = mnq_qty * COMMISSION_PER_MNQ + SLIPPAGE_USD

    trades = []

    for ts, row in signals.iterrows():
        idx = df.index.get_loc(ts)
        if idx + 1 >= len(df):
            continue

        entry_bar = idx + 1
        entry_time  = df.index[entry_bar]
        entry_price = df['open'].iloc[entry_bar]

        sl_price = entry_price - SL_PTS
        tp_price = entry_price + TP_PTS

        pnl_pts    = 0.0
        exit_price = entry_price
        exit_time  = None
        exit_reason = 'TIME_EXIT'

        for fi in range(entry_bar + 1, min(entry_bar + MAX_HOLD_BARS + 1, len(df))):
            bh = df['high'].iloc[fi]
            bl = df['low'].iloc[fi]

            if bl <= sl_price:
                pnl_pts     = -SL_PTS
                exit_price  = sl_price
                exit_time   = df.index[fi]
                exit_reason = 'SL'
                break
            elif bh >= tp_price:
                pnl_pts     = TP_PTS
                exit_price  = tp_price
                exit_time   = df.index[fi]
                exit_reason = 'TP'
                break

        if exit_time is None:
            fi         = min(entry_bar + MAX_HOLD_BARS, len(df) - 1)
            exit_price = df['close'].iloc[fi]
            exit_time  = df.index[fi]
            pnl_pts    = exit_price - entry_price

        trades.append({
            'entry_time':  entry_time,
            'exit_time':   exit_time,
            'wp_side':     row['wp_side'],
            'wp_size':     row['wp_size'],
            'entry_price': entry_price,
            'exit_price':  exit_price,
            'exit_reason': exit_reason,
            'pnl_pts':     pnl_pts,
            'gross_pnl':   pnl_pts * pv,
            'net_pnl':     pnl_pts * pv - cost,
        })

    tdf = pd.DataFrame(trades)
    tdf.to_csv(OUT_CSV, index=False)

    # Statistiche
    total = len(tdf)
    wins  = (tdf['net_pnl'] > 0).sum()
    wr    = wins / total * 100
    net   = tdf['net_pnl'].sum()
    gw    = tdf[tdf['net_pnl'] > 0]['net_pnl'].sum()
    gl    = abs(tdf[tdf['net_pnl'] < 0]['net_pnl'].sum())
    pf    = gw / gl if gl > 0 else float('inf')
    avg_w = tdf[tdf['net_pnl'] > 0]['net_pnl'].mean() if wins > 0 else 0
    avg_l = tdf[tdf['net_pnl'] < 0]['net_pnl'].mean() if (total - wins) > 0 else 0

    tdf['equity'] = tdf['net_pnl'].cumsum()
    tdf['peak']   = tdf['equity'].cummax()
    tdf['dd']     = tdf['peak'] - tdf['equity']
    max_dd        = tdf['dd'].max()

    sep = "=" * 65
    print(f"\n{sep}")
    print("  WHALE PRINT v3 - LONG ONLY (SL=20, TP=60 pts, R:R=1:3)")
    print(sep)
    print(f"  Trade eseguiti:    {total} ({total/441:.1f}/giorno)")
    print(f"  Win Rate:          {wr:.2f}%")
    print(f"  Profit Factor:     {pf:.2f}")
    print(f"  Net PnL totale:    ${net:,.2f}")
    print(f"  Avg Win:           ${avg_w:,.2f}")
    print(f"  Avg Loss:          ${avg_l:,.2f}")
    print(f"  Max Drawdown:      ${max_dd:,.2f} ({max_dd/2500*100:.1f}% del limite $2,500)")
    print(sep)
    print("\nEsiti:")
    print(tdf['exit_reason'].value_counts().to_string())
    print("\nPer side:")
    for s in ['A', 'B']:
        sub = tdf[tdf['wp_side'] == s]
        sw  = (sub['net_pnl'] > 0).mean() * 100
        print(f"  side={s}: n={len(sub)}, WR={sw:.1f}%, avg=${sub['net_pnl'].mean():.2f}")
    print(f"\nRisultati: {OUT_CSV}")


if __name__ == "__main__":
    run_backtest()
