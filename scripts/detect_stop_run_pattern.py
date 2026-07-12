"""
detect_stop_run_pattern.py
--------------------------
Rileva automaticamente il pattern "Stop Run + Assorbimento Istituzionale + Inversione"
su M1 bars usando pandas + footprint Big Trades.

LOGICA AUTOMATICA (nessuna ipotesi manuale):
  L'assorbimento viene cercato sia nella candela spike stessa
  che nella candela successiva (+1), coprendo entrambi i casi reali.

Uso: python scripts/detect_stop_run_pattern.py --date 20250110
     python scripts/detect_stop_run_pattern.py --date 20250110 --direction bearish_trap
     python scripts/detect_stop_run_pattern.py --all
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import argparse
import pandas as pd
import numpy as np
import pytz

from src.data_loader import load_day, list_data_files
from src.bar_aggregator import aggregate_to_bars
from src.session_context import filter_ny_window

# ── PARAMETRI ─────────────────────────────────────────────────────────────────
NQ_TICK         = 0.25
ROLLING_WIN     = 20       # finestra rolling per range/volume medi

SPIKE_RANGE_X   = 2.0      # range spike > N * media
SPIKE_VOL_X     = 1.3      # volume spike > N * media
SPIKE_CLOSE_PCT = 0.65     # close nella parte alta (bullish) o bassa (bearish) della candela

ABSORB_PRICE_TICKS = 8     # il big trade "avversario" deve essere entro N tick dal high/low spike
ABSORB_MIN_SIZE    = 20    # size minima big trade assorbimento

REVERSAL_ENGULF    = 0.40  # la barra di conferma deve coprire almeno 40% del range spike
# ─────────────────────────────────────────────────────────────────────────────

ET = pytz.timezone('America/New_York')


def bars_to_df(bars: list) -> pd.DataFrame:
    rows = []
    for b in bars:
        rows.append({
            'ts':          b.timestamp,
            'open':        b.open,
            'high':        b.high,
            'low':         b.low,
            'close':       b.close,
            'volume':      b.volume,
            'delta':       b.delta,
            'buy_vol':     b.buy_volume,
            'sell_vol':    b.sell_volume,
            # Big Trades per lato (la lista tiene prezzo e side)
            '_big_trades': b.big_trades,
        })
    df = pd.DataFrame(rows).set_index('ts')
    df['range']  = df['high'] - df['low']
    df['body']   = (df['close'] - df['open']).abs()
    df['body_d'] = np.sign(df['close'] - df['open'])   # +1 bullish, -1 bearish
    df['close_pos'] = ((df['close'] - df['low']) / df['range'].replace(0, np.nan)).fillna(0.5)

    # Rolling medie
    df['avg_range']  = df['range'].rolling(ROLLING_WIN, min_periods=5).mean()
    df['avg_vol']    = df['volume'].rolling(ROLLING_WIN, min_periods=5).mean()
    return df


def _sell_absorption_near_high(big_trades, high_price: float) -> dict | None:
    """
    Cerca Big Trades SELL (side='B') il cui prezzo è entro ABSORB_PRICE_TICKS
    dal massimo della spike. Restituisce il trade più grande trovato, o None.
    """
    best = None
    for bt in big_trades:
        if bt.side != 'B':
            continue
        if bt.size < ABSORB_MIN_SIZE:
            continue
        dist_ticks = (high_price - bt.price) / NQ_TICK
        if 0 <= dist_ticks <= ABSORB_PRICE_TICKS:
            if best is None or bt.size > best['size']:
                best = {'price': bt.price, 'size': bt.size, 'dist_ticks': round(dist_ticks, 1)}
    return best


def _buy_absorption_near_low(big_trades, low_price: float) -> dict | None:
    """
    Cerca Big Trades BUY (side='A') il cui prezzo è entro ABSORB_PRICE_TICKS
    dal minimo della spike. Restituisce il trade più grande trovato, o None.
    """
    best = None
    for bt in big_trades:
        if bt.side != 'A':
            continue
        if bt.size < ABSORB_MIN_SIZE:
            continue
        dist_ticks = (bt.price - low_price) / NQ_TICK
        if 0 <= dist_ticks <= ABSORB_PRICE_TICKS:
            if best is None or bt.size > best['size']:
                best = {'price': bt.price, 'size': bt.size, 'dist_ticks': round(dist_ticks, 1)}
    return best


def detect_patterns(df: pd.DataFrame, direction: str = 'both') -> list:
    results = []
    idxs = df.index.tolist()
    n = len(idxs)

    for i in range(ROLLING_WIN, n - 2):
        i0 = idxs[i]       # Barra SPIKE (N)
        i1 = idxs[i + 1]   # Barra ASSORBIMENTO o TRANSIZIONE (N+1)
        i2 = idxs[i + 2]   # Barra CONFERMA (N+2)

        spike = df.loc[i0]
        nxt   = df.loc[i1]
        conf  = df.loc[i2]

        if spike['avg_range'] <= 0 or spike['avg_vol'] <= 0:
            continue

        # ── BULLISH TRAP: spike UP → aspettati short ────────────────────────
        if direction in ('bullish_trap', 'both'):
            is_spike = (
                spike['range']    > spike['avg_range'] * SPIKE_RANGE_X and
                spike['volume']   > spike['avg_vol']   * SPIKE_VOL_X   and
                spike['body_d']   > 0 and                           # corpo bullish
                spike['close_pos'] > SPIKE_CLOSE_PCT                # chiude in alto
            )
            if is_spike:
                # Cerca assorbimento SELL: prima nella barra spike stessa,
                # poi nella barra successiva (N+1) se non trovato
                absorb = _sell_absorption_near_high(
                    spike['_big_trades'], spike['high']
                )
                absorb_bar = i0
                if absorb is None:
                    absorb = _sell_absorption_near_high(
                        nxt['_big_trades'], spike['high']
                    )
                    absorb_bar = i1

                # Delta flip: N+1 deve avere delta negativo
                delta_flip = nxt['delta'] < 0

                # Conferma inversione: N+2 chiude significativamente sotto
                reversal_range = spike['high'] - conf['close']
                reversal_ok = (
                    conf['body_d'] < 0 and
                    reversal_range >= spike['range'] * REVERSAL_ENGULF
                )

                # Segnale forte: almeno assorbimento O delta_flip + reversal
                signal_strength = sum([
                    absorb is not None,
                    delta_flip,
                    reversal_ok,
                ])

                if signal_strength >= 2:
                    results.append({
                        'type':            'BULLISH_TRAP → SHORT',
                        'spike_time':      i0.astimezone(ET).strftime('%H:%M ET'),
                        'confirm_time':    i2.astimezone(ET).strftime('%H:%M ET'),
                        'spike_high':      spike['high'],
                        'spike_range':     round(spike['range'], 2),
                        'spike_delta':     int(spike['delta']),
                        'spike_volume':    int(spike['volume']),
                        'absorb_found':    absorb is not None,
                        'absorb_bar':      ('SPIKE' if absorb_bar == i0 else 'N+1') if absorb else '-',
                        'absorb_price':    absorb['price'] if absorb else None,
                        'absorb_size':     absorb['size'] if absorb else None,
                        'absorb_dist_ticks': absorb['dist_ticks'] if absorb else None,
                        'delta_flip':      delta_flip,
                        'nxt_delta':       int(nxt['delta']),
                        'reversal_ok':     reversal_ok,
                        'conf_close':      conf['close'],
                        'signal_strength': signal_strength,
                        '_ts':             i0,
                    })

        # ── BEARISH TRAP: spike DOWN → aspettati long ───────────────────────
        if direction in ('bearish_trap', 'both'):
            is_spike = (
                spike['range']    > spike['avg_range'] * SPIKE_RANGE_X and
                spike['volume']   > spike['avg_vol']   * SPIKE_VOL_X   and
                spike['body_d']   < 0 and                           # corpo bearish
                spike['close_pos'] < (1 - SPIKE_CLOSE_PCT)          # chiude in basso
            )
            if is_spike:
                absorb = _buy_absorption_near_low(
                    spike['_big_trades'], spike['low']
                )
                absorb_bar = i0
                if absorb is None:
                    absorb = _buy_absorption_near_low(
                        nxt['_big_trades'], spike['low']
                    )
                    absorb_bar = i1

                delta_flip = nxt['delta'] > 0

                reversal_range = conf['close'] - spike['low']
                reversal_ok = (
                    conf['body_d'] > 0 and
                    reversal_range >= spike['range'] * REVERSAL_ENGULF
                )

                signal_strength = sum([
                    absorb is not None,
                    delta_flip,
                    reversal_ok,
                ])

                if signal_strength >= 2:
                    results.append({
                        'type':            'BEARISH_TRAP → LONG',
                        'spike_time':      i0.astimezone(ET).strftime('%H:%M ET'),
                        'confirm_time':    i2.astimezone(ET).strftime('%H:%M ET'),
                        'spike_low':       spike['low'],
                        'spike_range':     round(spike['range'], 2),
                        'spike_delta':     int(spike['delta']),
                        'spike_volume':    int(spike['volume']),
                        'absorb_found':    absorb is not None,
                        'absorb_bar':      ('SPIKE' if absorb_bar == i0 else 'N+1') if absorb else '-',
                        'absorb_price':    absorb['price'] if absorb else None,
                        'absorb_size':     absorb['size'] if absorb else None,
                        'absorb_dist_ticks': absorb['dist_ticks'] if absorb else None,
                        'delta_flip':      delta_flip,
                        'nxt_delta':       int(nxt['delta']),
                        'reversal_ok':     reversal_ok,
                        'conf_close':      conf['close'],
                        'signal_strength': signal_strength,
                        '_ts':             i0,
                    })

    return results


def run_date(csv_path: str, direction: str) -> list:
    trades = load_day(csv_path)
    bars   = filter_ny_window(aggregate_to_bars(trades, freq='1min'))
    if not bars:
        return []
    df = bars_to_df(bars)
    return detect_patterns(df, direction)


def print_results(patterns: list, date_label: str):
    if not patterns:
        print(f"  [{date_label}] Nessun pattern trovato.")
        return
    for p in patterns:
        stars = '★' * p['signal_strength']
        print(f"\n  {stars} [{date_label}] {p['type']}")
        print(f"     Spike:      {p['spike_time']}  range={p['spike_range']}pt  "
              f"vol={p['spike_volume']}  delta={p['spike_delta']:+d}")
        if p['absorb_found']:
            print(f"     Absorb:     @{p['absorb_price']} size={p['absorb_size']} "
                  f"({p['absorb_dist_ticks']} tick dal high)  barra={p['absorb_bar']}")
        else:
            print(f"     Absorb:     NON trovato con big trade (delta_flip o reversal compensano)")
        print(f"     Delta flip: {p['delta_flip']}  nxt_delta={p['nxt_delta']:+d}")
        print(f"     Reversal:   {p['reversal_ok']}  conf_close={p['conf_close']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date',      help='Data YYYYMMDD es: 20250110')
    parser.add_argument('--all',       action='store_true', help='Scansiona tutti i CSV in archive_data/')
    parser.add_argument('--direction', default='both',
                        choices=['bullish_trap', 'bearish_trap', 'both'])
    args = parser.parse_args()

    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'archive_data')

    if args.all:
        csv_files = list_data_files(DATA_DIR)
    elif args.date:
        csv_files = [f for f in list_data_files(DATA_DIR) if args.date in f]
    else:
        print("Specifica --date YYYYMMDD oppure --all")
        sys.exit(1)

    if not csv_files:
        print(f"Nessun file trovato in {DATA_DIR}")
        sys.exit(1)

    all_patterns = []
    for csv_path in csv_files:
        date_label = os.path.basename(csv_path).split('-')[-1].replace('.trades.csv', '')
        try:
            patterns = run_date(csv_path, args.direction)
            print_results(patterns, date_label)
            for p in patterns:
                p['date'] = date_label
            all_patterns.extend(patterns)
        except Exception as e:
            print(f"  [{date_label}] ERRORE: {e}")

    # Salva CSV per analisi
    if all_patterns:
        out = pd.DataFrame(all_patterns).drop(columns=['_ts'])
        out_path = os.path.join('agent_memory', f'stop_run_patterns.csv')
        out.to_csv(out_path, index=False)
        print(f"\n💾 {len(all_patterns)} pattern totali salvati in: {out_path}")
        print(f"\n📊 Breakdown:")
        print(out.groupby(['type', 'signal_strength']).size().to_string())


if __name__ == '__main__':
    main()
