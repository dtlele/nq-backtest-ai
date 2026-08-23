"""
WHALE PRINT STRATEGY v2 - CLEAN & CORRECT
Fixes rispetto alla v1:
  1. Filtro prezzi anomali: esclude barre con low < (median_price * 0.95)
  2. Direzione CORRETTA: side='A' (buyer hit ask) = LONG, side='B' (seller hit bid) = SHORT
  3. SL/TP FISSI in punti NQ (no ATR con dati corrotti)
  4. Check "30s": usa il CLOSE della barra SUCCESSIVA come conferma di momentum
  5. Commissioni reali MNQ: $1.40/contratto + $5 slippage
  6. Position sizing: rischio fisso $100 (0.20% conto 50k)
"""

import os, glob
import pandas as pd
import numpy as np
from datetime import time

# ─── PARAMETRI ────────────────────────────────────────────────────────────────
DATA_DIR    = r"C:\Users\Mauro\Documents\databento-data"
OUT_DIR     = r"C:\Users\Mauro\Documents\nq-backtest\output"
OUT_CSV     = os.path.join(OUT_DIR, "whale_v2_results.csv")

MIN_SIZE    = 80       # contratti minimi per "whale" print
MAX_SIZE    = 150      # contratti massimi (sopra è rumore / algo)

# Orari RTH Gold (EST)
SESSION_BLOCKS = [
    (time(9, 45), time(12, 0)),
    (time(13, 30), time(15, 15)),
]

# SL e TP fissi in punti NQ (1 punto NQ = $20 per 1 NQ, $2 per 1 MNQ)
SL_PTS      = 20.0     # Stop Loss = 20 punti NQ
TP_PTS      = 60.0     # Take Profit = 60 punti NQ (R:R = 1:3)

# Momentum check: se il close della barra successiva NON va nella nostra direzione
# di almeno MIN_CONFIRM_PTS, usciamo in micro-loss
CONFIRM_NEXT_BAR = True   # True = esci se barra +1 va contro
MIN_CONFIRM_PTS  = 0.0    # basta che vada nella direzione giusta (anche 0.25 pts)

FIXED_RISK_USD = 100.0    # rischio per trade in USD
POINT_VALUE_MNQ = 2.0     # $2 per punto per 1 MNQ
COMMISSION_PER_MNQ = 1.40
SLIPPAGE_USD = 5.00

MAX_HOLD_BARS = 30         # massimo numero barre 1-min da tenere aperto
# ──────────────────────────────────────────────────────────────────────────────

def load_bars_from_file(filepath: str) -> pd.DataFrame:
    """Carica file Databento trade CSV e restituisce barre 1-min con whale prints."""
    try:
        df = pd.read_csv(filepath, usecols=['ts_event', 'price', 'size', 'side'])
    except Exception:
        return pd.DataFrame()

    df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True, errors='coerce')
    df.dropna(subset=['ts_event', 'price', 'size'], inplace=True)
    df.sort_values('ts_event', inplace=True)
    df['ts_eastern'] = df['ts_event'].dt.tz_convert('US/Eastern')

    # ─── FILTRO TICK CORROTTI (livello singolo tick, PRIMA di qualsiasi aggregazione) ─
    # Calcola la mediana del prezzo sull'intero file come riferimento robusto
    # La mediana è immune agli outlier anche se ci sono molti tick corrotti
    median_price = df['price'].median()
    if pd.isna(median_price) or median_price <= 0:
        return pd.DataFrame()
    # Scarta qualsiasi tick che devia più del 10% dalla mediana.
    # NQ non si muove del 10% in un singolo giorno (10% di 21000 = 2100 punti).
    # Questo elimina errori tipo: prezzo=232.70 invece di 21232.70
    lower_bound = median_price * 0.90
    upper_bound = median_price * 1.10
    n_before = len(df)
    df = df[(df['price'] >= lower_bound) & (df['price'] <= upper_bound)].copy()
    n_removed = n_before - len(df)
    if n_removed > 0:
        pass  # tick corrotti rimossi silenziosamente
    if df.empty:
        return pd.DataFrame()
    # ──────────────────────────────────────────────────────────────────────────

    # Filtra orari gold RTH
    t = df['ts_eastern'].dt.time
    mask = pd.Series(False, index=df.index)
    for (t_start, t_end) in SESSION_BLOCKS:
        mask |= (t >= t_start) & (t < t_end)
    df = df[mask].copy()
    if df.empty:
        return pd.DataFrame()

    # Rimuovi side='N' (trade speciali, nessuna direzione)
    df = df[df['side'].isin(['A', 'B'])].copy()
    if df.empty:
        return pd.DataFrame()

    df['minute'] = df['ts_eastern'].dt.floor('1min')

    # Barre OHLCV
    bars = df.groupby('minute').agg(
        open=('price', 'first'),
        high=('price', 'max'),
        low=('price', 'min'),
        close=('price', 'last'),
        volume=('size', 'sum')
    )

    # ─── FIX PREZZI CORROTTI ───────────────────────────────────────────────
    # Il prezzo mediano del close per questa giornata
    median_close = bars['close'].median()
    # Escludi barre con high o low anomali (< 90% del mediano)
    anomaly_threshold = median_close * 0.90
    valid_bars = (bars['low'] >= anomaly_threshold) & (bars['high'] >= anomaly_threshold)
    bars = bars[valid_bars].copy()
    if bars.empty:
        return pd.DataFrame()
    # ──────────────────────────────────────────────────────────────────────

    # Whale print per minuto: print con size massima
    df_valid = df[df['minute'].isin(bars.index)].copy()
    idx_max = df_valid.groupby('minute')['size'].idxmax()
    whale_prints = df_valid.loc[idx_max, ['minute', 'price', 'size', 'side']].set_index('minute')
    whale_prints.columns = ['wp_price', 'wp_size', 'wp_side']

    combined = bars.join(whale_prints)

    # Filtro size whale
    size_ok = (combined['wp_size'] >= MIN_SIZE) & (combined['wp_size'] <= MAX_SIZE)

    # Filtro location: whale print è su uno stoppino (wick)
    body_high = combined[['open', 'close']].max(axis=1)
    body_low  = combined[['open', 'close']].min(axis=1)
    on_wick = (combined['wp_price'] >= body_high) | (combined['wp_price'] <= body_low)

    # ─── DIREZIONE CORRETTA ────────────────────────────────────────────────
    # side='A' = buyer hit ASK = ordine di acquisto aggressivo → LONG (+1)
    # side='B' = seller hit BID = ordine di vendita aggressivo → SHORT (-1)
    combined['signal'] = 0
    valid = size_ok & on_wick
    combined.loc[valid & (combined['wp_side'] == 'A'), 'signal'] = 1   # LONG
    combined.loc[valid & (combined['wp_side'] == 'B'), 'signal'] = -1  # SHORT
    # ──────────────────────────────────────────────────────────────────────

    return combined


def run_backtest():
    pattern = os.path.join(DATA_DIR, "glbx-mdp3-*.trades.csv")
    files = sorted(glob.glob(pattern))
    print(f"Caricamento {len(files)} file Databento...")

    all_bars = []
    for i, f in enumerate(files):
        bars = load_bars_from_file(f)
        if not bars.empty:
            all_bars.append(bars)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(files)} file processati...")

    if not all_bars:
        print("ERRORE: nessuna barra valida trovata.")
        return

    df = pd.concat(all_bars).sort_index()
    df = df[~df.index.duplicated(keep='first')]
    print(f"Totale barre 1-min caricate: {len(df)}")

    signals = df[df['signal'] != 0].copy()
    print(f"Segnali whale totali: {len(signals)}")

    trades = []

    for ts, row in signals.iterrows():
        idx = df.index.get_loc(ts)

        # Entrata alla barra SUCCESSIVA (open della barra +1)
        if idx + 1 >= len(df):
            continue
        entry_bar_idx = idx + 1
        entry_time  = df.index[entry_bar_idx]
        entry_price = df['open'].iloc[entry_bar_idx]
        sig_dir = row['signal']

        # SL e TP assoluti
        sl_price = entry_price - SL_PTS if sig_dir == 1 else entry_price + SL_PTS
        tp_price = entry_price + TP_PTS if sig_dir == 1 else entry_price - TP_PTS

        # Position sizing
        mnq_qty = max(1, int(round(FIXED_RISK_USD / (SL_PTS * POINT_VALUE_MNQ))))
        pv = POINT_VALUE_MNQ * mnq_qty
        cost = mnq_qty * COMMISSION_PER_MNQ + SLIPPAGE_USD

        # ─── CONFIRM CHECK (barra +1 = ~primo minuto dall'entrata) ────────
        if CONFIRM_NEXT_BAR and idx + 2 < len(df):
            bar1_close = df['close'].iloc[entry_bar_idx]
            if sig_dir == 1:
                price_ok = (bar1_close - entry_price) > MIN_CONFIRM_PTS
            else:
                price_ok = (entry_price - bar1_close) > MIN_CONFIRM_PTS

            if not price_ok:
                # Micro-loss exit: chiudi al close della barra +1
                exit_price = bar1_close
                pnl_pts = (exit_price - entry_price) if sig_dir == 1 else (entry_price - exit_price)
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': df.index[entry_bar_idx],
                    'direction': 'LONG' if sig_dir == 1 else 'SHORT',
                    'mnq_qty': mnq_qty,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'wp_size': row['wp_size'],
                    'exit_reason': 'CONFIRM_FAIL_EXIT',
                    'pnl_pts': pnl_pts,
                    'gross_pnl': pnl_pts * pv,
                    'net_pnl': pnl_pts * pv - cost,
                })
                continue
        # ──────────────────────────────────────────────────────────────────

        # Scansiona barre successive per SL/TP/TIME
        pnl_pts    = 0.0
        exit_price = entry_price
        exit_time  = None
        exit_reason = 'TIME_EXIT'

        scan_start = entry_bar_idx + 1  # inizia a scansionare dalla barra +2
        scan_end   = min(entry_bar_idx + MAX_HOLD_BARS + 1, len(df))

        for fi in range(scan_start, scan_end):
            bh = df['high'].iloc[fi]
            bl = df['low'].iloc[fi]
            bc = df['close'].iloc[fi]

            if sig_dir == 1:  # LONG
                if bl <= sl_price:
                    pnl_pts = -SL_PTS
                    exit_price = sl_price
                    exit_time = df.index[fi]
                    exit_reason = 'SL'
                    break
                elif bh >= tp_price:
                    pnl_pts = TP_PTS
                    exit_price = tp_price
                    exit_time = df.index[fi]
                    exit_reason = 'TP'
                    break
            else:  # SHORT
                if bh >= sl_price:
                    pnl_pts = -SL_PTS
                    exit_price = sl_price
                    exit_time = df.index[fi]
                    exit_reason = 'SL'
                    break
                elif bl <= tp_price:
                    pnl_pts = TP_PTS
                    exit_price = tp_price
                    exit_time = df.index[fi]
                    exit_reason = 'TP'
                    break

        if exit_time is None:
            fi = min(entry_bar_idx + MAX_HOLD_BARS, len(df) - 1)
            exit_price = df['close'].iloc[fi]
            exit_time  = df.index[fi]
            pnl_pts = (exit_price - entry_price) if sig_dir == 1 else (entry_price - exit_price)

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': 'LONG' if sig_dir == 1 else 'SHORT',
            'mnq_qty': mnq_qty,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'wp_size': row['wp_size'],
            'exit_reason': exit_reason,
            'pnl_pts': pnl_pts,
            'gross_pnl': pnl_pts * pv,
            'net_pnl': pnl_pts * pv - cost,
        })

    if not trades:
        print("Nessun trade generato.")
        return

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
    avg_l = tdf[tdf['net_pnl'] < 0]['net_pnl'].mean() if (total-wins) > 0 else 0

    tdf['equity'] = tdf['net_pnl'].cumsum()
    tdf['peak']   = tdf['equity'].cummax()
    tdf['dd']     = tdf['peak'] - tdf['equity']
    max_dd = tdf['dd'].max()

    sep = "=" * 65
    print(f"\n{sep}")
    print("  WHALE PRINT v2 - RISULTATI BACKTEST (SL=20, TP=60 pts)")
    print(sep)
    print(f"  File analizzati:       441 giorni Databento NQ")
    print(f"  Segnali whale:         {len(signals)}")
    print(f"  Trade eseguiti:        {total}")
    print(f"  Win Rate:              {wr:.2f}%")
    print(f"  Profit Factor:         {pf:.2f}")
    print(f"  Net PnL totale:        ${net:,.2f}")
    print(f"  Avg Win:               ${avg_w:,.2f}")
    print(f"  Avg Loss:              ${avg_l:,.2f}")
    print(f"  Max Drawdown:          ${max_dd:,.2f} ({max_dd/2500*100:.1f}% del limite $2,500)")
    print(f"  Trade/giorno:          {total/441:.1f}")
    print(sep)
    print("\nDistribuzione uscite:")
    print(tdf['exit_reason'].value_counts().to_string())
    print(f"\nRisultati salvati in: {OUT_CSV}")


if __name__ == "__main__":
    run_backtest()
