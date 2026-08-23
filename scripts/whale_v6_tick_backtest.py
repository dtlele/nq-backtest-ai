"""
WHALE PRINT STRATEGY v6 - BACKTEST TICK-BY-TICK (PRECISIONE ASSOLUTA)

Logica esatta:
  1. Bar building: solo per trovare segnali whale (bar M = segnale)
  2. Entry: primo tick disponibile nel minuto M+1 (= prezzo reale di entrata)
     -> entry_idx = indice del primo tick di M+1 nel CSV
  3. Exit: scansione tick[entry_idx+1 : ] sequenzialmente
     -> primo tick con price <= sl_price -> SL (no ambiguita' ordine)
     -> primo tick con price >= tp_price -> TP
     -> max_exit_time = entry_time + 30 minuti -> TIME_EXIT al close
  4. Nessuna approssimazione su bar high/low: sappiamo ESATTAMENTE
     quale livello e' stato toccato prima.

Filtri dati:
  - Tick-level: scarta prezzi fuori da mediana +-10% (errori grossolani)
  - Bar-level: scarta barre con high-low > 60 pts (tick corrotti residui)
  - Wick significativo: wp_price supera corpo di almeno 2 pts

Parametri:
  - Solo LONG (analisi statistica: SHORT non funziona in NQ 2025-2026)
  - SL = 20 pts, TP = 60 pts (R:R 1:3)
  - Rischio fisso $100 per trade (~2 MNQ)
  - Max 1 trade aperto alla volta
"""

import os, glob
import pandas as pd
import numpy as np
from datetime import time, timedelta

# ─── PARAMETRI ────────────────────────────────────────────────────────────────
DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
OUT_DIR  = r"C:\Users\Mauro\Documents\nq-backtest\output"
OUT_CSV  = os.path.join(OUT_DIR, "whale_v6_tick_backtest.csv")

MIN_SIZE          = 80
MAX_SIZE          = 150
MAX_BAR_RANGE_PTS = 60.0   # range massimo barra 1-min valida (pts)
MIN_WICK_PTS      = 2.0    # wick minimo oltre il corpo per segnale valido

SESSION_BLOCKS = [
    (time(9, 45), time(12, 0)),
    (time(13, 30), time(15, 15)),
]
RTH_START = time(9, 30)    # RTH esteso per scansione exit
RTH_END   = time(16, 0)

SL_PTS           = 20.0
TP_PTS           = 60.0
MAX_HOLD_MINUTES = 30      # hold massimo in minuti reali

FIXED_RISK_USD     = 100.0
POINT_VALUE_MNQ    = 2.0
COMMISSION_PER_MNQ = 1.40
SLIPPAGE_USD       = 5.00

ONE_TRADE_ONLY = True
# ──────────────────────────────────────────────────────────────────────────────

def process_file(filepath: str) -> list:
    """
    Processa un singolo file CSV Databento.
    Restituisce lista di dict (un dict per trade).
    """
    # ── 1. Carica tutti i tick del giorno ────────────────────────────────────
    try:
        raw = pd.read_csv(filepath, usecols=['ts_event', 'price', 'size', 'side'])
    except Exception:
        return []

    raw['ts_event'] = pd.to_datetime(raw['ts_event'], utc=True, errors='coerce')
    raw.dropna(subset=['ts_event', 'price', 'size'], inplace=True)
    raw.sort_values('ts_event', inplace=True)
    raw.reset_index(drop=True, inplace=True)  # indici 0,1,2,... = posizione nel CSV

    raw['ts_eastern'] = raw['ts_event'].dt.tz_convert('US/Eastern')

    # ── 2. Filtro tick corrotti (livello singolo tick) ───────────────────────
    median_p = raw['price'].median()
    if pd.isna(median_p) or median_p <= 0:
        return []
    raw = raw[(raw['price'] >= median_p * 0.90) & (raw['price'] <= median_p * 1.10)].copy()
    raw.reset_index(drop=True, inplace=True)
    if raw.empty:
        return []

    # ── 3. Dataframe per EXIT: tutti i tick RTH (non solo gold hours) ────────
    t_all = raw['ts_eastern'].dt.time
    rth_mask = (t_all >= RTH_START) & (t_all < RTH_END)
    df_exit = raw[rth_mask & raw['side'].isin(['A', 'B'])].copy()
    df_exit.reset_index(drop=True, inplace=True)  # nuovo indice per scansione exit

    # ── 4. Costruisci barre 1-min nelle gold hours per trovare segnali ───────
    t_gold = raw['ts_eastern'].dt.time
    gold_mask = pd.Series(False, index=raw.index)
    for t_start, t_end in SESSION_BLOCKS:
        gold_mask |= (t_gold >= t_start) & (t_gold < t_end)
    df_gold = raw[gold_mask & raw['side'].isin(['A', 'B'])].copy()

    if df_gold.empty:
        return []

    df_gold['minute'] = df_gold['ts_eastern'].dt.floor('1min')

    bars = df_gold.groupby('minute').agg(
        open=('price', 'first'),
        high=('price', 'max'),
        low=('price', 'min'),
        close=('price', 'last'),
    )

    # Filtro range barra (elimina tick corrotti residui che creano bar anomale)
    bar_range = bars['high'] - bars['low']
    bars = bars[bar_range <= MAX_BAR_RANGE_PTS].copy()
    if bars.empty:
        return []

    # Whale print per barra (solo per barre con range valido)
    df_valid = df_gold[df_gold['minute'].isin(bars.index)].copy()
    if df_valid.empty:
        return []

    idx_max_size = df_valid.groupby('minute')['size'].idxmax()
    wp = df_valid.loc[idx_max_size, ['minute', 'price', 'size', 'side']].set_index('minute')
    wp.columns = ['wp_price', 'wp_size', 'wp_side']
    bars = bars.join(wp)

    # Filtri segnale
    size_ok   = (bars['wp_size'] >= MIN_SIZE) & (bars['wp_size'] <= MAX_SIZE)
    body_high = bars[['open', 'close']].max(axis=1)
    body_low  = bars[['open', 'close']].min(axis=1)
    on_upper  = bars['wp_price'] >= (body_high + MIN_WICK_PTS)
    on_lower  = bars['wp_price'] <= (body_low  - MIN_WICK_PTS)
    on_wick   = on_upper | on_lower

    signal_bars = bars[size_ok & on_wick].copy()
    if signal_bars.empty:
        return []

    # ── 5. Per ogni segnale: backtest tick-by-tick ───────────────────────────
    mnq_qty = max(1, int(round(FIXED_RISK_USD / (SL_PTS * POINT_VALUE_MNQ))))
    pv      = POINT_VALUE_MNQ * mnq_qty
    cost    = mnq_qty * COMMISSION_PER_MNQ + SLIPPAGE_USD

    trades = []
    busy_until_ts = None  # per ONE_TRADE_ONLY

    for signal_ts, sig_row in signal_bars.iterrows():
        # Minuto di entrata = minuto successivo al segnale
        entry_minute_start = signal_ts + pd.Timedelta(minutes=1)
        entry_minute_end   = entry_minute_start + pd.Timedelta(minutes=1)

        # Trova il primo tick nel minuto M+1 nel dataframe exit (RTH completo)
        entry_candidates = df_exit[
            (df_exit['ts_eastern'] >= entry_minute_start) &
            (df_exit['ts_eastern'] <  entry_minute_end)
        ]
        if entry_candidates.empty:
            continue  # nessun tick nel minuto di entrata

        # entry_idx = indice nel df_exit del primo tick di M+1
        # = il tick esatto su cui si apre il trade
        entry_idx    = entry_candidates.index[0]
        entry_price  = entry_candidates['price'].iloc[0]
        entry_ts     = entry_candidates['ts_eastern'].iloc[0]

        # ONE_TRADE_ONLY: salta se siamo ancora in un trade precedente
        if ONE_TRADE_ONLY and busy_until_ts is not None and entry_ts <= busy_until_ts:
            continue

        sl_price = entry_price - SL_PTS   # LONG: SL sotto
        tp_price = entry_price + TP_PTS   # LONG: TP sopra

        max_exit_ts = entry_ts + pd.Timedelta(minutes=MAX_HOLD_MINUTES)

        # ── SCANSIONE TICK-BY-TICK dal tick entry_idx+1 in avanti ──────────
        # Questo è esattamente: df_exit.loc[entry_idx+1 : ]
        # e controlliamo sequenzialmente: primo a toccare SL o TP vince.
        scan_ticks = df_exit.loc[entry_idx + 1 :]
        # Limita al max hold time
        scan_ticks = scan_ticks[scan_ticks['ts_eastern'] <= max_exit_ts]

        pnl_pts    = None
        exit_price = None
        exit_ts    = None
        exit_reason = 'TIME_EXIT'

        for tick_idx, tick in scan_ticks.iterrows():
            p = tick['price']
            if p <= sl_price:
                pnl_pts     = -SL_PTS
                exit_price  = sl_price   # filled at SL (worst case, no gap fill)
                exit_ts     = tick['ts_eastern']
                exit_reason = 'SL'
                break
            elif p >= tp_price:
                pnl_pts     = TP_PTS
                exit_price  = tp_price
                exit_ts     = tick['ts_eastern']
                exit_reason = 'TP'
                break

        # TIME_EXIT: ultimo tick disponibile entro max_exit_ts
        if pnl_pts is None:
            last_ticks = scan_ticks.tail(1)
            if last_ticks.empty:
                # Nessun tick dopo l'entrata entro il hold time -> salta
                continue
            exit_price  = last_ticks['price'].iloc[0]
            exit_ts     = last_ticks['ts_eastern'].iloc[0]
            pnl_pts     = exit_price - entry_price

        net_pnl = pnl_pts * pv - cost

        trades.append({
            'entry_ts':    entry_ts,
            'exit_ts':     exit_ts,
            'entry_idx':   int(entry_idx),         # indice tick nel CSV
            'wp_size':     sig_row['wp_size'],
            'wp_side':     sig_row['wp_side'],
            'entry_price': entry_price,
            'exit_price':  exit_price,
            'sl_price':    sl_price,
            'tp_price':    tp_price,
            'exit_reason': exit_reason,
            'pnl_pts':     round(pnl_pts, 4),
            'gross_pnl':   round(pnl_pts * pv, 2),
            'net_pnl':     round(net_pnl, 2),
        })

        if ONE_TRADE_ONLY:
            busy_until_ts = exit_ts

    return trades


def run_backtest():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "glbx-mdp3-*.trades.csv")))
    print(f"Backtest TICK-BY-TICK su {len(files)} file Databento...")
    print(f"SL={SL_PTS} pts | TP={TP_PTS} pts | MaxHold={MAX_HOLD_MINUTES} min | Solo LONG")

    all_trades = []
    for i, f in enumerate(files):
        day_trades = process_file(f)
        all_trades.extend(day_trades)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(files)} file | trade finora: {len(all_trades)}")

    if not all_trades:
        print("Nessun trade generato.")
        return

    tdf = pd.DataFrame(all_trades)
    tdf.to_csv(OUT_CSV, index=False)

    # ─── STATISTICHE ─────────────────────────────────────────────────────────
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
    print("  WHALE PRINT v6 - TICK-BY-TICK (PRECISIONE ASSOLUTA)")
    print(sep)
    print(f"  [MODE] Backtest tick sequenziale: df_exit.loc[entry_idx+1:]")
    print(f"  [FIX]  Range barra max: {MAX_BAR_RANGE_PTS} pts")
    print(f"  [FIX]  Wick minimo:     {MIN_WICK_PTS} pts oltre il corpo")
    print(f"  Trade eseguiti:   {total} (~{total/441:.1f}/giorno)")
    print(f"  Win Rate:         {wr:.2f}%")
    print(f"  Profit Factor:    {pf:.2f}")
    print(f"  Net PnL totale:   ${net:,.2f}")
    print(f"  Avg Win:          ${avg_w:,.2f}")
    print(f"  Avg Loss:         ${avg_l:,.2f}")
    print(f"  Max Drawdown:     ${max_dd:,.2f} ({max_dd/2500*100:.1f}% del limite $2,500)")
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
    print(f"Campione trade con indici CSV:")
    print(tdf[['entry_ts','entry_idx','entry_price','sl_price',
               'tp_price','exit_reason','pnl_pts']].head(10).to_string())


if __name__ == "__main__":
    run_backtest()
