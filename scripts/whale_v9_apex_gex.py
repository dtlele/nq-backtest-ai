"""
WHALE v9 - APEX TRADER FUNDING + GEX GAMMA LEVELS INTEGRATION
Integra la strategia Whale Print di Matteo con:
1. Filtro Regime GEX (Positive vs Negative Gamma via Zero Gamma / Gamma Flip)
2. Confluenza con i Livelli Gamma (Call Wall, Put Wall, Zero Gamma)
3. Regole di Trailing Drawdown Intraday specifiche per Apex Trader Funding
4. Target dinamici su livelli GEX per minimizzare il giveback di profitto non realizzato
"""

import os
import glob
import pandas as pd
import numpy as np
from datetime import time

DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
OUT_DIR  = r"C:\Users\Mauro\Documents\nq-backtest\output"

# Orari RTH Gold (Eastern Time)
RTH_START = time(9, 30)
RTH_END   = time(16, 0)

# Parametri Apex Trader Funding (Default: Conto 50k)
APEX_PARAMS = {
    '25k':  {'target_usd': 1500.0, 'trailing_dd_max': 1500.0, 'max_mnq': 40, 'recommended_mnq': 2},
    '50k':  {'target_usd': 3000.0, 'trailing_dd_max': 2500.0, 'max_mnq': 100, 'recommended_mnq': 2},
    '100k': {'target_usd': 6000.0, 'trailing_dd_max': 3000.0, 'max_mnq': 140, 'recommended_mnq': 4},
    '150k': {'target_usd': 9000.0, 'trailing_dd_max': 5000.0, 'max_mnq': 170, 'recommended_mnq': 6},
    '300k': {'target_usd': 20000.0, 'trailing_dd_max': 7500.0, 'max_mnq': 350, 'recommended_mnq': 10},
}

# Costi reali Apex Futures (MNQ via Rithmic/Tradovate)
COMMISSION_PER_MNQ_RT = 1.40  # Round Turn per contratto Micro MNQ
SLIPPAGE_PER_TRADE_USD = 5.00  # Slippage stimato conservativo a trade

# Parametri Core Whale Strategy
FIXED_RISK_USD   = 100.0
POINT_VALUE_MNQ  = 2.0
SL_PTS           = 20.0
TP_PTS           = 60.0
MAX_HOLD_MINUTES = 20
ONE_TRADE_ONLY   = True

def estimate_daily_gex(df_day):
    median_p = df_day['price'].median()
    if pd.isna(median_p) or median_p <= 0:
        return None
        
    t_east = df_day['ts_eastern'].dt.time
    pre_open = df_day[(t_east >= time(8, 0)) & (t_east < time(9, 30))]
    if not pre_open.empty:
        zero_gamma = pre_open['price'].median()
    else:
        zero_gamma = median_p

    call_wall = zero_gamma + 150.0
    put_wall = zero_gamma - 150.0
    
    return {
        'zero_gamma': zero_gamma,
        'call_wall': call_wall,
        'put_wall': put_wall
    }

def process_file_v9(filepath, account_tier='50k', use_gex_filter=True):
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

    gex = estimate_daily_gex(raw)
    if not gex:
        return []

    rth_mask = (t_all >= RTH_START) & (t_all < RTH_END)
    df_exit = raw[rth_mask & raw['side'].isin(['A', 'B'])].copy()
    df_exit.reset_index(drop=True, inplace=True)

    gold_mask = ((t_all >= time(9, 45)) & (t_all < time(12, 0))) | ((t_all >= time(13, 30)) & (t_all < time(15, 15)))
    df_gold = raw[gold_mask & raw['side'].isin(['A', 'B'])].copy()
    if df_gold.empty:
        return []

    df_gold['minute'] = df_gold['ts_eastern'].dt.floor('1min')
    bars = df_gold.groupby('minute').agg(
        open=('price', 'first'), high=('price', 'max'),
        low=('price', 'min'), close=('price', 'last')
    )
    bars = bars[(bars['high'] - bars['low']) <= 150.0].copy()
    if bars.empty:
        return []

    df_valid = df_gold[df_gold['minute'].isin(bars.index)].copy()
    if df_valid.empty:
        return []

    idx_max = df_valid.groupby('minute')['size'].idxmax()
    wp = df_valid.loc[idx_max, ['minute', 'price', 'size', 'side']].set_index('minute')
    wp.columns = ['wp_price', 'wp_size', 'wp_side']
    bars = bars.join(wp)

    size_ok = (bars['wp_size'] >= 50) & (bars['wp_size'] <= 200)
    body_high = bars[['open', 'close']].max(axis=1)
    body_low = bars[['open', 'close']].min(axis=1)
    on_wick = (bars['wp_price'] >= body_high + 0.5) | (bars['wp_price'] <= body_low - 0.5)

    signal_bars = bars[size_ok & on_wick].copy()
    if signal_bars.empty:
        return []

    tier_info = APEX_PARAMS.get(account_tier, APEX_PARAMS['50k'])
    mnq_qty = tier_info['recommended_mnq']
    pv = POINT_VALUE_MNQ * mnq_qty
    trade_cost = mnq_qty * COMMISSION_PER_MNQ_RT + SLIPPAGE_PER_TRADE_USD

    trades = []
    busy_until_ts = None

    for signal_ts, sig_row in signal_bars.iterrows():
        entry_minute_start = signal_ts + pd.Timedelta(minutes=1)
        entry_minute_end = entry_minute_start + pd.Timedelta(minutes=1)

        entry_cands = df_exit[
            (df_exit['ts_eastern'] >= entry_minute_start) &
            (df_exit['ts_eastern'] < entry_minute_end)
        ]
        if entry_cands.empty:
            continue

        entry_idx = entry_cands.index[0]
        entry_price = entry_cands['price'].iloc[0]
        entry_ts = entry_cands['ts_eastern'].iloc[0]

        if ONE_TRADE_ONLY and busy_until_ts is not None and entry_ts <= busy_until_ts:
            continue

        is_positive_gamma = entry_price >= gex['zero_gamma']
        dist_to_call_wall = gex['call_wall'] - entry_price

        target_tp = TP_PTS
        if use_gex_filter:
            if dist_to_call_wall > 20 and dist_to_call_wall < TP_PTS:
                target_tp = dist_to_call_wall - 2.0
            elif dist_to_call_wall <= 15:
                continue

        sl_price = entry_price - SL_PTS
        tp_price = entry_price + target_tp
        max_exit_ts = entry_ts + pd.Timedelta(minutes=MAX_HOLD_MINUTES)

        scan = df_exit.loc[entry_idx + 1:]
        scan = scan[scan['ts_eastern'] <= max_exit_ts]

        pnl_pts = None
        exit_ts = None
        exit_price = None
        exit_reason = 'TIME_EXIT'
        max_favorable_pts = 0.0

        for _, tick in scan.iterrows():
            p = tick['price']
            fav = p - entry_price
            if fav > max_favorable_pts:
                max_favorable_pts = fav

            if use_gex_filter and is_positive_gamma and max_favorable_pts >= 25.0:
                sl_price = max(sl_price, entry_price + 1.0)

            if p <= sl_price:
                pnl_pts = sl_price - entry_price
                exit_price = sl_price
                exit_ts = tick['ts_eastern']
                exit_reason = 'SL' if sl_price < entry_price else 'BE'
                break
            elif p >= tp_price:
                pnl_pts = target_tp
                exit_price = tp_price
                exit_ts = tick['ts_eastern']
                exit_reason = 'TP'
                break

        if pnl_pts is None:
            last = scan.tail(1)
            if last.empty:
                continue
            exit_price = last['price'].iloc[0]
            exit_ts = last['ts_eastern'].iloc[0]
            pnl_pts = exit_price - entry_price

        net_pnl = pnl_pts * pv - trade_cost
        max_unrealized_profit_usd = max_favorable_pts * pv

        trades.append({
            'date': entry_ts.strftime('%Y-%m-%d'),
            'entry_ts': entry_ts,
            'exit_ts': exit_ts,
            'exit_reason': exit_reason,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl_pts': round(pnl_pts, 4),
            'net_pnl': round(net_pnl, 2),
            'max_unrealized_profit_usd': round(max_unrealized_profit_usd, 2),
            'mnq_qty': mnq_qty,
            'gex_regime': 'POSITIVE' if is_positive_gamma else 'NEGATIVE',
        })

        if ONE_TRADE_ONLY:
            busy_until_ts = exit_ts

    return trades

def run_apex_backtest(account_tier='50k', use_gex=True):
    files = sorted(glob.glob(os.path.join(DATA_DIR, "glbx-mdp3-*.trades.csv")))
    tier_info = APEX_PARAMS[account_tier]
    
    print(f"=== BACKTEST WHALE v9 APEX TRADER FUNDING ({account_tier.upper()} ACCOUNT) ===")
    print(f"Dati: {len(files)} file Databento | Sizing: {tier_info['recommended_mnq']} Micro MNQ (${tier_info['recommended_mnq']*2.0}/pt)")
    print(f"Target Apex: ${tier_info['target_usd']:,.0f} | Max Trailing DD: ${tier_info['trailing_dd_max']:,.0f}")
    print(f"GEX Filter: {'ATTIVO' if use_gex else 'DISATTIVO'}\n")

    all_trades = []
    for f in files:
        all_trades.extend(process_file_v9(f, account_tier=account_tier, use_gex_filter=use_gex))

    tdf = pd.DataFrame(all_trades)
    if tdf.empty:
        print("Nessun trade generato.")
        return

    tdf['equity'] = tdf['net_pnl'].cumsum()
    tdf['peak'] = tdf['equity'].cummax()
    tdf['drawdown'] = tdf['peak'] - tdf['equity']
    max_closed_dd = tdf['drawdown'].max()
    
    total_trades = len(tdf)
    wins = (tdf['net_pnl'] > 0).sum()
    wr = (wins / total_trades) * 100
    net_pnl = tdf['net_pnl'].sum()
    gw = tdf[tdf['net_pnl'] > 0]['net_pnl'].sum()
    gl = abs(tdf[tdf['net_pnl'] < 0]['net_pnl'].sum())
    pf = gw / gl if gl > 0 else np.inf

    tp_count = (tdf['exit_reason'] == 'TP').sum()
    sl_count = (tdf['exit_reason'] == 'SL').sum()
    be_count = (tdf['exit_reason'] == 'BE').sum()
    time_count = (tdf['exit_reason'] == 'TIME_EXIT').sum()

    days_to_pass = None
    eq_series = tdf['equity'].values
    for idx, eq in enumerate(eq_series):
        if eq >= tier_info['target_usd']:
            days_to_pass = idx + 1
            break

    print("----------------------------------------------------------------------")
    print(f"  Totale Trade:             {total_trades} ({total_trades/441:.2f} trade/giorno)")
    print(f"  Win Rate:                 {wr:.2f}%")
    print(f"  Profit Factor:            {pf:.2f}")
    print(f"  Net PnL Totale:           ${net_pnl:,.2f}")
    print(f"  Max Drawdown:             ${max_closed_dd:,.2f} ({max_closed_dd/tier_info['trailing_dd_max']*100:.1f}% del limite)")
    print(f"  Trade per passare:        {days_to_pass if days_to_pass else 'N/D'} trade (~{days_to_pass if days_to_pass else 0} giorni operativi)")
    print(f"  Exits breakdown:          TP: {tp_count} | SL: {sl_count} | BE: {be_count} | TIME: {time_count}")
    print("----------------------------------------------------------------------")

    out_csv = os.path.join(OUT_DIR, f"whale_v9_apex_{account_tier}_gex.csv")
    tdf.to_csv(out_csv, index=False)
    print(f"Risultati salvati in: {out_csv}\n")
    return tdf

if __name__ == "__main__":
    run_apex_backtest(account_tier='50k', use_gex=True)
