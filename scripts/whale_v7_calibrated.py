"""
WHALE PRINT v7 - TICK-BY-TICK, FILTRI CALIBRATI
Problema v6: troppi pochi trade (75/441gg) per via di filtri eccessivi.

Correzioni:
  - MAX_BAR_RANGE_PTS: 60 -> 150 pts (rimuove solo corruzioni evidenti 200+)
    Con backtest tick-by-tick il range della barra NON influenza l'exit,
    serve solo a proteggere la signal detection (wick check).
    MIN_WICK_PTS=2 gia' gestisce i falsi wick marginali.
  - MIN_WICK_PTS: 2 -> 1 pt (leggermente piu' permissivo ma comunque non 0)
  - MIN_SIZE/MAX_SIZE: 80-150 -> 70-190 (range originale del video Matt Conte)
  - MAX_HOLD_MINUTES: 30 -> 20 min (piu' aderente alla strategia originale)

Tutto il resto e' identico a v6:
  - Entry: primo tick del minuto M+1 (prezzo reale)
  - Exit: scansione tick sequenziale df_exit.loc[entry_idx+1:]
  - Solo LONG, 1 trade alla volta, SL=20 TP=60, rischio $100
"""

import os, glob
import pandas as pd
import numpy as np
from datetime import time

DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
OUT_DIR  = r"C:\Users\Mauro\Documents\nq-backtest\output"
OUT_CSV  = os.path.join(OUT_DIR, "whale_v7_calibrated.csv")

# ── Filtri segnale ───────────────────────────────────────────────────────────
MIN_SIZE          = 70      # contratti minimi (originale video: 70)
MAX_SIZE          = 190     # contratti massimi (originale video: 190)
MAX_BAR_RANGE_PTS = 150.0   # scarta solo barre con range > 150 pts (corruzioni evidenti)
MIN_WICK_PTS      = 1.0     # whale print deve superare il corpo di almeno 1 pt

SESSION_BLOCKS = [
    (time(9, 45), time(12, 0)),
    (time(13, 30), time(15, 15)),
]
RTH_START = time(9, 30)
RTH_END   = time(16, 0)

# ── Parametri trade ──────────────────────────────────────────────────────────
SL_PTS           = 20.0
TP_PTS           = 60.0
MAX_HOLD_MINUTES = 20      # 20 minuti (piu' aderente al video)

FIXED_RISK_USD     = 100.0
POINT_VALUE_MNQ    = 2.0
COMMISSION_PER_MNQ = 1.40
SLIPPAGE_USD       = 5.00
ONE_TRADE_ONLY     = True
# ──────────────────────────────────────────────────────────────────────────────

def process_file(filepath: str) -> list:
    try:
        raw = pd.read_csv(filepath, usecols=['ts_event', 'price', 'size', 'side'])
    except Exception:
        return []

    raw['ts_event'] = pd.to_datetime(raw['ts_event'], utc=True, errors='coerce')
    raw.dropna(subset=['ts_event', 'price', 'size'], inplace=True)
    raw.sort_values('ts_event', inplace=True)
    raw.reset_index(drop=True, inplace=True)

    raw['ts_eastern'] = raw['ts_event'].dt.tz_convert('US/Eastern')

    # Filtro tick corrotti (mediana +-10%)
    median_p = raw['price'].median()
    if pd.isna(median_p) or median_p <= 0:
        return []
    raw = raw[(raw['price'] >= median_p * 0.90) & (raw['price'] <= median_p * 1.10)].copy()
    raw.reset_index(drop=True, inplace=True)
    if raw.empty:
        return []

    # df_exit: tutti i tick RTH per la scansione exit
    t_all = raw['ts_eastern'].dt.time
    rth_mask = (t_all >= RTH_START) & (t_all < RTH_END)
    df_exit = raw[rth_mask & raw['side'].isin(['A', 'B'])].copy()
    df_exit.reset_index(drop=True, inplace=True)

    # df_gold: tick nelle gold hours per la signal detection
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

    # Filtro range barra (solo corruzioni evidenti > 150 pts)
    bar_range = bars['high'] - bars['low']
    bars = bars[bar_range <= MAX_BAR_RANGE_PTS].copy()
    if bars.empty:
        return []

    df_valid = df_gold[df_gold['minute'].isin(bars.index)].copy()
    if df_valid.empty:
        return []

    idx_max_size = df_valid.groupby('minute')['size'].idxmax()
    wp = df_valid.loc[idx_max_size, ['minute', 'price', 'size', 'side']].set_index('minute')
    wp.columns = ['wp_price', 'wp_size', 'wp_side']
    bars = bars.join(wp)

    size_ok   = (bars['wp_size'] >= MIN_SIZE) & (bars['wp_size'] <= MAX_SIZE)
    body_high = bars[['open', 'close']].max(axis=1)
    body_low  = bars[['open', 'close']].min(axis=1)
    on_upper  = bars['wp_price'] >= (body_high + MIN_WICK_PTS)
    on_lower  = bars['wp_price'] <= (body_low  - MIN_WICK_PTS)
    on_wick   = on_upper | on_lower

    signal_bars = bars[size_ok & on_wick].copy()
    if signal_bars.empty:
        return []

    mnq_qty = max(1, int(round(FIXED_RISK_USD / (SL_PTS * POINT_VALUE_MNQ))))
    pv      = POINT_VALUE_MNQ * mnq_qty
    cost    = mnq_qty * COMMISSION_PER_MNQ + SLIPPAGE_USD

    trades = []
    busy_until_ts = None

    for signal_ts, sig_row in signal_bars.iterrows():
        entry_minute_start = signal_ts + pd.Timedelta(minutes=1)
        entry_minute_end   = entry_minute_start + pd.Timedelta(minutes=1)

        entry_candidates = df_exit[
            (df_exit['ts_eastern'] >= entry_minute_start) &
            (df_exit['ts_eastern'] <  entry_minute_end)
        ]
        if entry_candidates.empty:
            continue

        entry_idx    = entry_candidates.index[0]
        entry_price  = entry_candidates['price'].iloc[0]
        entry_ts     = entry_candidates['ts_eastern'].iloc[0]

        if ONE_TRADE_ONLY and busy_until_ts is not None and entry_ts <= busy_until_ts:
            continue

        sl_price     = entry_price - SL_PTS
        tp_price     = entry_price + TP_PTS
        max_exit_ts  = entry_ts + pd.Timedelta(minutes=MAX_HOLD_MINUTES)

        # SCANSIONE TICK-BY-TICK: df_exit.loc[entry_idx+1 : ]
        scan_ticks = df_exit.loc[entry_idx + 1 :]
        scan_ticks = scan_ticks[scan_ticks['ts_eastern'] <= max_exit_ts]

        pnl_pts     = None
        exit_price  = None
        exit_ts     = None
        exit_reason = 'TIME_EXIT'

        for tick_idx, tick in scan_ticks.iterrows():
            p = tick['price']
            if p <= sl_price:
                pnl_pts     = -SL_PTS
                exit_price  = sl_price
                exit_ts     = tick['ts_eastern']
                exit_reason = 'SL'
                break
            elif p >= tp_price:
                pnl_pts     = TP_PTS
                exit_price  = tp_price
                exit_ts     = tick['ts_eastern']
                exit_reason = 'TP'
                break

        if pnl_pts is None:
            last_ticks = scan_ticks.tail(1)
            if last_ticks.empty:
                continue
            exit_price  = last_ticks['price'].iloc[0]
            exit_ts     = last_ticks['ts_eastern'].iloc[0]
            pnl_pts     = exit_price - entry_price

        net_pnl = pnl_pts * pv - cost

        trades.append({
            'entry_ts':    entry_ts,
            'exit_ts':     exit_ts,
            'entry_idx':   int(entry_idx),
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
    print(f"WHALE v7 - TICK-BY-TICK su {len(files)} file")
    print(f"SL={SL_PTS}pts | TP={TP_PTS}pts | MaxHold={MAX_HOLD_MINUTES}min")
    print(f"Size: {MIN_SIZE}-{MAX_SIZE} | BarRange<={MAX_BAR_RANGE_PTS}pts | Wick>={MIN_WICK_PTS}pt")

    all_trades = []
    for i, f in enumerate(files):
        all_trades.extend(process_file(f))
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(files)} file | trade: {len(all_trades)}")

    if not all_trades:
        print("Nessun trade.")
        return

    tdf = pd.DataFrame(all_trades)
    tdf.to_csv(OUT_CSV, index=False)

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
    max_dd        = (tdf['peak'] - tdf['equity']).max()

    sep = "=" * 65
    print(f"\n{sep}")
    print("  WHALE PRINT v7 - TICK-BY-TICK CALIBRATO")
    print(sep)
    print(f"  Trade:         {total} (~{total/441:.1f}/giorno)")
    print(f"  Win Rate:      {wr:.2f}%")
    print(f"  Profit Factor: {pf:.2f}")
    print(f"  Net PnL:       ${net:,.2f}")
    print(f"  Avg Win:       ${avg_w:,.2f}")
    print(f"  Avg Loss:      ${avg_l:,.2f}")
    print(f"  Max DD:        ${max_dd:,.2f} ({max_dd/2500*100:.1f}% del limite)")
    print(sep)
    print("\nEsiti:")
    print(tdf['exit_reason'].value_counts().to_string())
    print("\nPer side:")
    for s in ['A', 'B']:
        sub = tdf[tdf['wp_side'] == s]
        if not sub.empty:
            print(f"  side={s}: n={len(sub)}, WR={(sub['net_pnl']>0).mean()*100:.1f}%, avg=${sub['net_pnl'].mean():.2f}")
    print(f"\nRisultati: {OUT_CSV}")


if __name__ == "__main__":
    run_backtest()
