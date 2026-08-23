"""
WHALE PRINT STRATEGY v5 - LONG ONLY, DATI PULITI
Fix rispetto v4:
  1. [NUOVO] Filtro range barra: scarta barre con high-low > 60 pts.
     Motivo: tick corrotti con prezzi plausibili (es. 22099 su barre a 21868)
     passano il filtro tick-level +-10% ma creano range di 200-250 pts in 1 min
     (impossibile per NQ), generando false wick detection e segnali speculari.
  2. [NUOVO] Filtro wick significativo: wp_price deve superare il corpo
     di almeno MIN_WICK_PTS (2 pts) per essere un vero segnale su wick.
  3. Controlla SL/TP anche sulla barra di entrata
  4. Max 1 trade aperto alla volta
  5. SL=20 pts, TP=60 pts (R:R 1:3)
"""

import os, glob
import pandas as pd
import numpy as np
from datetime import time

# ─── PARAMETRI ────────────────────────────────────────────────────────────────
DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
OUT_DIR  = r"C:\Users\Mauro\Documents\nq-backtest\output"
OUT_CSV  = os.path.join(OUT_DIR, "whale_v5_clean_bars.csv")

MIN_SIZE = 80
MAX_SIZE = 150

SESSION_BLOCKS = [
    (time(9, 45), time(12, 0)),
    (time(13, 30), time(15, 15)),
]

SL_PTS   = 20.0
TP_PTS   = 60.0

FIXED_RISK_USD     = 100.0
POINT_VALUE_MNQ    = 2.0     # $/punto per 1 MNQ
COMMISSION_PER_MNQ = 1.40
SLIPPAGE_USD       = 5.00

MAX_HOLD_BARS    = 30
ONE_TRADE_ONLY   = True   # max 1 trade aperto alla volta
MAX_BAR_RANGE_PTS = 60.0  # scarta barre con high-low > 60 pts (tick corrotti residui)
MIN_WICK_PTS      = 2.0   # whale print deve essere almeno 2 pts oltre il corpo
# ──────────────────────────────────────────────────────────────────────────────

def load_bars(filepath: str) -> pd.DataFrame:
    """Carica 1 file Databento, filtra tick corrotti, restituisce barre 1-min con segnali."""
    try:
        df = pd.read_csv(filepath, usecols=['ts_event', 'price', 'size', 'side'])
    except Exception:
        return pd.DataFrame()

    df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True, errors='coerce')
    df.dropna(subset=['ts_event', 'price', 'size'], inplace=True)
    df.sort_values('ts_event', inplace=True)

    # ── Filtro tick corrotti PRIMA di tutto ─────────────────────────────────
    median_p = df['price'].median()
    if pd.isna(median_p) or median_p <= 0:
        return pd.DataFrame()
    # ±10% dalla mediana: copre qualsiasi movimento reale di NQ in un giorno
    df = df[(df['price'] >= median_p * 0.90) & (df['price'] <= median_p * 1.10)].copy()
    if df.empty:
        return pd.DataFrame()
    # ────────────────────────────────────────────────────────────────────────

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

    # ── FIX SPECULARI: Filtro range barra post-aggregazione ─────────────────
    # Tick corrotti con prezzi "plausibili" (es. 22099 su barre a 21868)
    # passano il filtro tick ±10%, ma creano range 200-250 pts/min su NQ.
    # Media range 1-min NQ = 10-20 pts. Oltre 60 pts = tick residuo corrotto.
    # Questi bar generano false upper/lower wick e segnali speculari.
    bar_range = bars['high'] - bars['low']
    bars = bars[bar_range <= MAX_BAR_RANGE_PTS].copy()
    if bars.empty:
        return pd.DataFrame()
    # ────────────────────────────────────────────────────────────────────────

    # Whale print (ricalcolato solo sulle barre sopravvissute al filtro range)
    df_clean = df[df['minute'].isin(bars.index)].copy()
    if df_clean.empty:
        return pd.DataFrame()
    idx_max = df_clean.groupby('minute')['size'].idxmax()
    wp = df_clean.loc[idx_max, ['minute', 'price', 'size', 'side']].set_index('minute')
    wp.columns = ['wp_price', 'wp_size', 'wp_side']
    bars = bars.join(wp)

    size_ok   = (bars['wp_size'] >= MIN_SIZE) & (bars['wp_size'] <= MAX_SIZE)
    body_high = bars[['open', 'close']].max(axis=1)
    body_low  = bars[['open', 'close']].min(axis=1)

    # ── FIX: Wick SIGNIFICATIVO (almeno MIN_WICK_PTS oltre il corpo) ────────
    # Evita falsi positivi dove wp_price supera body_high di soli 0.25 pts
    on_upper = bars['wp_price'] >= (body_high + MIN_WICK_PTS)
    on_lower = bars['wp_price'] <= (body_low  - MIN_WICK_PTS)
    on_wick  = on_upper | on_lower
    # ────────────────────────────────────────────────────────────────────────

    bars['signal'] = 0
    bars.loc[size_ok & on_wick, 'signal'] = 1  # tutti LONG

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

    trades     = []
    busy_until = None  # timestamp fino al quale siamo occupati (1 trade alla volta)

    for ts, row in signals.iterrows():
        idx = df.index.get_loc(ts)
        if idx + 1 >= len(df):
            continue

        entry_bar   = idx + 1
        entry_time  = df.index[entry_bar]
        entry_price = df['open'].iloc[entry_bar]

        # ── Max 1 trade aperto alla volta ───────────────────────────────────
        if ONE_TRADE_ONLY and busy_until is not None and entry_time <= busy_until:
            continue
        # ────────────────────────────────────────────────────────────────────

        sl_price = entry_price - SL_PTS
        tp_price = entry_price + TP_PTS

        pnl_pts    = 0.0
        exit_price = entry_price
        exit_time  = None
        exit_reason = 'TIME_EXIT'

        # ── FIX: controlla SL/TP sulla barra di ENTRATA (bar M+1) ──────────
        entry_bar_high = df['high'].iloc[entry_bar]
        entry_bar_low  = df['low'].iloc[entry_bar]

        sl_hit_on_entry = entry_bar_low  <= sl_price
        tp_hit_on_entry = entry_bar_high >= tp_price

        if sl_hit_on_entry and tp_hit_on_entry:
            # Entrambi attraversati nello stesso minuto: conservativo = SL
            pnl_pts     = -SL_PTS
            exit_price  = sl_price
            exit_time   = entry_time
            exit_reason = 'SL'
        elif sl_hit_on_entry:
            pnl_pts     = -SL_PTS
            exit_price  = sl_price
            exit_time   = entry_time
            exit_reason = 'SL'
        elif tp_hit_on_entry:
            pnl_pts     = TP_PTS
            exit_price  = tp_price
            exit_time   = entry_time
            exit_reason = 'TP'
        # ────────────────────────────────────────────────────────────────────

        # Se non colpito sull'entry bar, scansiona le barre successive
        if exit_time is None:
            for fi in range(entry_bar + 1, min(entry_bar + MAX_HOLD_BARS + 1, len(df))):
                bh = df['high'].iloc[fi]
                bl = df['low'].iloc[fi]

                if bl <= sl_price and bh >= tp_price:
                    # Entrambi nella stessa barra: SL conservativo
                    pnl_pts     = -SL_PTS
                    exit_price  = sl_price
                    exit_time   = df.index[fi]
                    exit_reason = 'SL'
                    break
                elif bl <= sl_price:
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
                fi          = min(entry_bar + MAX_HOLD_BARS, len(df) - 1)
                exit_price  = df['close'].iloc[fi]
                exit_time   = df.index[fi]
                pnl_pts     = exit_price - entry_price

        net_pnl = pnl_pts * pv - cost

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
            'net_pnl':     net_pnl,
        })

        # Aggiorna busy_until
        if ONE_TRADE_ONLY:
            busy_until = exit_time

    tdf = pd.DataFrame(trades)
    tdf.to_csv(OUT_CSV, index=False)

    # ─── STATISTICHE ──────────────────────────────────────────────────────
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

    trading_days = df.index.normalize().nunique()

    sep = "=" * 65
    print(f"\n{sep}")
    print("  WHALE PRINT v4 - LONG ONLY CORRETTO (SL=20, TP=60)")
    print(sep)
    print(f"  [FIX] Entry bar SL/TP check: SI")
    print(f"  [FIX] Max 1 trade alla volta: SI")
    print(f"  Segnali trovati:   {len(signals)}")
    print(f"  Trade eseguiti:    {total} (~{total/441:.1f}/giorno)")
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
        if len(sub) == 0:
            continue
        sw = (sub['net_pnl'] > 0).mean() * 100
        print(f"  side={s}: n={len(sub)}, WR={sw:.1f}%, avg=${sub['net_pnl'].mean():.2f}")
    print(f"\nRisultati: {OUT_CSV}")


if __name__ == "__main__":
    run_backtest()
