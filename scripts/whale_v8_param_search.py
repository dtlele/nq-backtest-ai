"""
WHALE PRINT v8 - RICERCA PARAMETRI PER 1 TRADE/GIORNO CON WR > 70%
Testa 4 configurazioni complete (tick-by-tick) su tutti i 441 file e
riporta: n_trade, WR, PF, MaxDD per ognuna.
"""
import os, glob
import pandas as pd
import numpy as np
from datetime import time

DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
OUT_DIR  = r"C:\Users\Mauro\Documents\nq-backtest\output"

RTH_START = time(9, 30)
RTH_END   = time(16, 0)

FIXED_RISK_USD     = 100.0
POINT_VALUE_MNQ    = 2.0
COMMISSION_PER_MNQ = 1.40
SLIPPAGE_USD       = 5.00
SL_PTS             = 20.0
TP_PTS             = 60.0
MAX_HOLD_MINUTES   = 20
ONE_TRADE_ONLY     = True

# ── 4 Configurazioni da testare ───────────────────────────────────────────────
CONFIGS = [
    {
        'name':         'A: v7 base (70-190, wick>=1)',
        'min_size':     70, 'max_size': 190,
        'max_bar_range': 150.0, 'min_wick': 1.0,
        'sessions':     [(time(9,45), time(12,0)), (time(13,30), time(15,15))],
    },
    {
        'name':         'B: size 50-200, wick>=0.5',
        'min_size':     50, 'max_size': 200,
        'max_bar_range': 150.0, 'min_wick': 0.5,
        'sessions':     [(time(9,45), time(12,0)), (time(13,30), time(15,15))],
    },
    {
        'name':         'C: size 40-250, wick>=0.5',
        'min_size':     40, 'max_size': 250,
        'max_bar_range': 200.0, 'min_wick': 0.5,
        'sessions':     [(time(9,45), time(12,0)), (time(13,30), time(15,15))],
    },
    {
        'name':         'D: size 50-200, wick>=0, +ore 9:30-9:45',
        'min_size':     50, 'max_size': 200,
        'max_bar_range': 150.0, 'min_wick': 0.0,
        'sessions':     [(time(9,30), time(12,0)), (time(13,30), time(15,30))],
    },
]
# ──────────────────────────────────────────────────────────────────────────────

def process_file(filepath, cfg):
    try:
        raw = pd.read_csv(filepath, usecols=['ts_event', 'price', 'size', 'side'])
    except Exception:
        return []

    raw['ts_event'] = pd.to_datetime(raw['ts_event'], utc=True, errors='coerce')
    raw.dropna(subset=['ts_event', 'price', 'size'], inplace=True)
    raw.sort_values('ts_event', inplace=True)
    raw.reset_index(drop=True, inplace=True)

    median_p = raw['price'].median()
    if pd.isna(median_p) or median_p <= 0:
        return []
    raw = raw[(raw['price'] >= median_p * 0.90) & (raw['price'] <= median_p * 1.10)].copy()
    raw.reset_index(drop=True, inplace=True)
    if raw.empty:
        return []

    raw['ts_eastern'] = raw['ts_event'].dt.tz_convert('US/Eastern')
    t_all = raw['ts_eastern'].dt.time

    # df_exit: RTH completo per scansione tick exit
    rth_mask = (t_all >= RTH_START) & (t_all < RTH_END)
    df_exit = raw[rth_mask & raw['side'].isin(['A', 'B'])].copy()
    df_exit.reset_index(drop=True, inplace=True)

    # df_gold: tick nelle ore di sessione per signal detection
    gold_mask = pd.Series(False, index=raw.index)
    for t_start, t_end in cfg['sessions']:
        gold_mask |= (t_all >= t_start) & (t_all < t_end)
    df_gold = raw[gold_mask & raw['side'].isin(['A', 'B'])].copy()
    if df_gold.empty:
        return []

    df_gold['minute'] = df_gold['ts_eastern'].dt.floor('1min')
    bars = df_gold.groupby('minute').agg(
        open=('price', 'first'), high=('price', 'max'),
        low=('price', 'min'), close=('price', 'last'),
    )
    bars = bars[(bars['high'] - bars['low']) <= cfg['max_bar_range']].copy()
    if bars.empty:
        return []

    df_valid = df_gold[df_gold['minute'].isin(bars.index)].copy()
    if df_valid.empty:
        return []

    idx_max_size = df_valid.groupby('minute')['size'].idxmax()
    wp = df_valid.loc[idx_max_size, ['minute', 'price', 'size', 'side']].set_index('minute')
    wp.columns = ['wp_price', 'wp_size', 'wp_side']
    bars = bars.join(wp)

    size_ok   = (bars['wp_size'] >= cfg['min_size']) & (bars['wp_size'] <= cfg['max_size'])
    body_high = bars[['open', 'close']].max(axis=1)
    body_low  = bars[['open', 'close']].min(axis=1)

    if cfg['min_wick'] > 0:
        on_wick = (bars['wp_price'] >= body_high + cfg['min_wick']) | \
                  (bars['wp_price'] <= body_low  - cfg['min_wick'])
    else:
        on_wick = pd.Series(True, index=bars.index)  # qualsiasi print

    signal_bars = bars[size_ok & on_wick].copy()
    if signal_bars.empty:
        return []

    mnq_qty = max(1, int(round(FIXED_RISK_USD / (SL_PTS * POINT_VALUE_MNQ))))
    pv   = POINT_VALUE_MNQ * mnq_qty
    cost = mnq_qty * COMMISSION_PER_MNQ + SLIPPAGE_USD

    trades = []
    busy_until_ts = None

    for signal_ts, sig_row in signal_bars.iterrows():
        entry_minute_start = signal_ts + pd.Timedelta(minutes=1)
        entry_minute_end   = entry_minute_start + pd.Timedelta(minutes=1)

        entry_cands = df_exit[
            (df_exit['ts_eastern'] >= entry_minute_start) &
            (df_exit['ts_eastern'] <  entry_minute_end)
        ]
        if entry_cands.empty:
            continue

        entry_idx   = entry_cands.index[0]
        entry_price = entry_cands['price'].iloc[0]
        entry_ts    = entry_cands['ts_eastern'].iloc[0]

        if ONE_TRADE_ONLY and busy_until_ts is not None and entry_ts <= busy_until_ts:
            continue

        sl_price    = entry_price - SL_PTS
        tp_price    = entry_price + TP_PTS
        max_exit_ts = entry_ts + pd.Timedelta(minutes=MAX_HOLD_MINUTES)

        scan = df_exit.loc[entry_idx + 1:]
        scan = scan[scan['ts_eastern'] <= max_exit_ts]

        pnl_pts    = None
        exit_ts    = None
        exit_price = None
        exit_reason = 'TIME_EXIT'

        for _, tick in scan.iterrows():
            p = tick['price']
            if p <= sl_price:
                pnl_pts, exit_price, exit_ts, exit_reason = -SL_PTS, sl_price, tick['ts_eastern'], 'SL'
                break
            elif p >= tp_price:
                pnl_pts, exit_price, exit_ts, exit_reason = TP_PTS, tp_price, tick['ts_eastern'], 'TP'
                break

        if pnl_pts is None:
            last = scan.tail(1)
            if last.empty:
                continue
            exit_price  = last['price'].iloc[0]
            exit_ts     = last['ts_eastern'].iloc[0]
            pnl_pts     = exit_price - entry_price

        trades.append({
            'entry_ts':    entry_ts,
            'exit_ts':     exit_ts,
            'exit_reason': exit_reason,
            'pnl_pts':     round(pnl_pts, 4),
            'net_pnl':     round(pnl_pts * pv - cost, 2),
        })
        if ONE_TRADE_ONLY:
            busy_until_ts = exit_ts

    return trades


def run_config(cfg):
    files = sorted(glob.glob(os.path.join(DATA_DIR, "glbx-mdp3-*.trades.csv")))
    all_trades = []
    for i, f in enumerate(files):
        all_trades.extend(process_file(f, cfg))
    return pd.DataFrame(all_trades)


def print_stats(name, tdf):
    if tdf.empty:
        print(f"  {name}: 0 trade")
        return
    total = len(tdf)
    wins  = (tdf['net_pnl'] > 0).sum()
    wr    = wins / total * 100
    net   = tdf['net_pnl'].sum()
    gw    = tdf[tdf['net_pnl'] > 0]['net_pnl'].sum()
    gl    = abs(tdf[tdf['net_pnl'] < 0]['net_pnl'].sum())
    pf    = gw / gl if gl > 0 else float('inf')
    tdf['equity'] = tdf['net_pnl'].cumsum()
    tdf['peak']   = tdf['equity'].cummax()
    max_dd        = (tdf['peak'] - tdf['equity']).max()
    print(f"  {name}")
    print(f"    Trade: {total} ({total/441:.1f}/gg) | WR: {wr:.1f}% | PF: {pf:.2f} | "
          f"Net: ${net:,.0f} | MaxDD: ${max_dd:.0f}")
    print(f"    TP:{(tdf['exit_reason']=='TP').sum()} SL:{(tdf['exit_reason']=='SL').sum()} "
          f"TIME:{(tdf['exit_reason']=='TIME_EXIT').sum()}")


files = sorted(glob.glob(os.path.join(DATA_DIR, "glbx-mdp3-*.trades.csv")))
print(f"Test su {len(files)} file Databento (tick-by-tick)\n")

for cfg in CONFIGS:
    print(f"Running {cfg['name']}...")
    tdf = run_config(cfg)
    print_stats(cfg['name'], tdf)
    # Salva risultati
    safe = cfg['name'].split(':')[0].strip()
    tdf.to_csv(os.path.join(OUT_DIR, f"whale_v8_config_{safe}.csv"), index=False)
    print()
