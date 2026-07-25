"""
Tune Fabio's 3-step model on V8b period.

The first-pass model found 9 setups in V8b but most were "outside prime window"
and the +$766 winner was not caught. This script:
1. Loosens the time-of-day filter (extend to all NY, not just 9:55-11:30)
2. Loosens the LVN proximity (only require LVN exists, not near price)
3. Removes the LVN strength threshold completely (it's a soft filter)
4. Uses lower swing_lookback to catch more swings
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src import Bar, Trade, NQ_TICK_SIZE, NQ_BIG_TRADE_THRESHOLD
from src.session_context import _to_et, ET


class MarketState(str, Enum):
    BALANCED   = "balanced"
    IMBALANCED = "imbalanced"
    NEUTRAL    = "neutral"


def is_ny_session(bar: Bar) -> bool:
    t = _to_et(bar)
    if t.weekday() >= 5:
        return False
    start = t.replace(hour=9, minute=30, second=0, microsecond=0)
    end   = t.replace(hour=16, minute=0, second=0, microsecond=0)
    return start <= t < end


def compute_atr_m5(m5_bars, period=20):
    if len(m5_bars) < 2:
        return 0.0
    trs = []
    for i in range(1, len(m5_bars)):
        b, p = m5_bars[i], m5_bars[i - 1]
        tr = max(b.high - b.low, abs(b.high - p.close), abs(b.low - p.close))
        trs.append(tr)
    if not trs:
        return 0.0
    return float(np.mean(trs[-period:]))


def find_swings(m5_bars, lookback=3):
    swings = []
    n = len(m5_bars)
    if n < lookback * 2 + 1:
        return swings
    for i in range(lookback, n - lookback):
        bar = m5_bars[i]
        if all(bar.high > m5_bars[j].high for j in range(i - lookback, i + lookback + 1) if j != i):
            swings.append((i, bar.high, "high"))
        if all(bar.low < m5_bars[j].low for j in range(i - lookback, i + lookback + 1) if j != i):
            swings.append((i, bar.low, "low"))
    return swings


def find_lvn(m5_bars, start_idx, end_idx):
    if start_idx >= end_idx or end_idx >= len(m5_bars):
        return (0.0, 0.0)
    sub = m5_bars[start_idx:end_idx + 1]
    if not sub:
        return (0.0, 0.0)
    lo = min(b.low for b in sub)
    hi = max(b.high for b in sub)
    if hi <= lo:
        return (0.0, 0.0)
    lo_t = round(lo / NQ_TICK_SIZE) * NQ_TICK_SIZE
    hi_t = round(hi / NQ_TICK_SIZE) * NQ_TICK_SIZE
    n_ticks = int(round((hi_t - lo_t) / NQ_TICK_SIZE)) + 1
    if n_ticks <= 0:
        return (0.0, 0.0)
    visits = np.zeros(n_ticks, dtype=np.int32)
    for b in sub:
        s = int(round((round(b.low / NQ_TICK_SIZE) * NQ_TICK_SIZE - lo_t) / NQ_TICK_SIZE))
        e = int(round((round(b.high / NQ_TICK_SIZE) * NQ_TICK_SIZE - lo_t) / NQ_TICK_SIZE))
        s = max(0, s); e = min(n_ticks - 1, e)
        if e >= s:
            visits[s:e + 1] += 1
    if visits.sum() == 0:
        return (0.0, 0.0)
    min_v = visits.min()
    lvn_mask = (visits == min_v)
    best_start, best_len = 0, 0
    cur_start, cur_len = 0, 0
    for i, m in enumerate(lvn_mask):
        if m:
            if cur_len == 0:
                cur_start = i
            cur_len += 1
            if cur_len > best_len:
                best_len = cur_len
                best_start = cur_start
        else:
            cur_len = 0
    avg = visits.mean()
    if avg == 0:
        return (0.0, 0.0)
    strength = 1.0 - (min_v / avg)
    mid_idx = best_start + best_len // 2
    lvn_price = lo_t + mid_idx * NQ_TICK_SIZE
    return (lvn_price, max(0.0, min(1.0, strength)))


def has_big_trade_in_direction(bar, direction, min_size=30):
    if not bar.big_trades:
        return (False, 0, 0.0)
    target_side = 'A' if direction == 'long' else 'B'
    best_size = 0
    best_price = 0.0
    found = False
    for t in bar.big_trades:
        if t.side == target_side and t.size >= min_size:
            if t.size > best_size:
                best_size = t.size
                best_price = t.price
                found = True
    return (found, best_size, best_price)


# ── Main simulation ─────────────────────────────────────────────────────────

def row_to_bar(row):
    ts = pd.Timestamp(row['datetime_et'])
    if ts.tz is None:
        ts = ts.tz_localize('America/New_York')
    ts_utc = ts.tz_convert('UTC').to_pydatetime()
    big_count = int(row.get('big_trades_count', 0))
    big_total = int(row.get('big_trades_total', 0))
    big_trades = []
    if big_count > 0 and big_total > 0:
        avg_size = max(1, big_total // big_count)
        if avg_size >= 30:
            is_buy = row.get('delta', 0) > 0
            side = 'A' if is_buy else 'B'
            n = min(big_count, 3)
            for _ in range(n):
                big_trades.append(Trade(
                    ts_event=ts_utc, side=side,
                    price=float(row['close']),
                    size=max(NQ_BIG_TRADE_THRESHOLD, avg_size),
                ))
    return Bar(
        timestamp=ts_utc,
        open=float(row['open']), high=float(row['high']),
        low=float(row['low']), close=float(row['close']),
        volume=int(row.get('volume', 0)),
        buy_volume=0, sell_volume=0,
        delta=int(row.get('delta', 0)),
        delta_pct=0.0, cvd=0, vwap=0.0,
        big_trades=big_trades, footprint={},
    )


def run_fabio_tuned(v8b_ny, label='', **kwargs):
    """Run tuned Fabio model on V8b NY session data."""
    setups = []
    for date, day_df in v8b_ny.groupby('date'):
        day_df = day_df.sort_values('datetime_et').reset_index(drop=True)
        bars = [row_to_bar(row) for _, row in day_df.iterrows()]
        for i in range(8, len(bars)):
            m5 = bars[max(0, i - 30):i + 1]
            cur = bars[i]
            if not is_ny_session(cur):
                continue
            # Find recent swing
            sw = find_swings(m5, lookback=kwargs.get('swing_lookback', 3))
            if not sw:
                continue
            # Try the most recent swing
            last_sw_idx, last_sw_price, last_sw_type = sw[-1]
            direction = 'short' if last_sw_type == 'high' else 'long'
            # Find LVN in last 15 bars (relaxed)
            lvn_start = max(0, len(m5) - kwargs.get('lvn_lookback', 15))
            lvn_price, lvn_strength = find_lvn(m5, lvn_start, len(m5) - 1)
            # Get big trade
            big_ok, big_size, _ = has_big_trade_in_direction(
                cur, direction,
                min_size=kwargs.get('min_big_size', 30),
            )
            if not big_ok:
                continue
            # Compute targets
            atr = compute_atr_m5(m5, period=20)
            if direction == 'long':
                stop = cur.low - max(2, kwargs.get('stop_atr', 0.5)) * atr
                risk = cur.close - stop
                target_1 = cur.close + 3 * risk
                target_2 = cur.close + 5 * risk
            else:
                stop = cur.high + max(2, kwargs.get('stop_atr', 0.5)) * atr
                risk = stop - cur.close
                target_1 = cur.close - 3 * risk
                target_2 = cur.close - 5 * risk
            confidence = 50 + int(min(20, lvn_strength * 30))
            if big_size >= 100: confidence += 10
            elif big_size >= 50: confidence += 5
            confidence = min(100, confidence)
            setups.append({
                'date': date,
                'time_et': day_df.iloc[i]['time_et'],
                'direction': direction,
                'entry': cur.close,
                'stop': stop,
                'target_1': target_1,
                'target_2': target_2,
                'lvn_price': lvn_price,
                'lvn_strength': lvn_strength,
                'trigger_size': big_size,
                'confidence': confidence,
                'atr': atr,
                'risk_pts': abs(cur.close - stop),
            })
    return setups


# ── PnL simulator ──────────────────────────────────────────────────────────

def simulate_pnl(setups, v8b_ny, hold_bars=6, target_r=1.0, max_hold=12):
    """Simulate PnL for a list of setups.
    For each setup, look forward `hold_bars` M5 bars and check outcome:
    - If target hit first → WIN (target_r * risk)
    - If stop hit first → LOSS (-risk)
    - Else: EOD exit at last close (PnL = close - entry for long, entry - close for short)
    """
    trades = []
    for s in setups:
        date = s['date']
        day_df = v8b_ny[v8b_ny['date'] == date].sort_values('datetime_et').reset_index(drop=True)
        # Find the index of the entry bar
        entry_time = s['time_et']
        # Convert to comparable format
        entry_matches = day_df[day_df['time_et'] == entry_time]
        if entry_matches.empty:
            continue
        entry_idx = entry_matches.index[0]
        # Look forward hold_bars
        future = day_df.iloc[entry_idx + 1: entry_idx + 1 + hold_bars]
        if future.empty:
            continue
        entry = s['entry']
        stop = s['stop']
        risk = s['risk_pts']
        direction = s['direction']
        target = entry + (target_r * risk * (1 if direction == 'long' else -1))
        outcome = 'timeout'
        pnl_pts = 0.0
        exit_price = entry
        # Reuse future but extend if needed
        if len(future) < max_hold:
            extra = day_df.iloc[entry_idx + 1 + len(future): entry_idx + 1 + max_hold]
            future = pd.concat([future, extra])
        for _, fb in future.iterrows():
            if direction == 'long':
                if fb['low'] <= stop:
                    outcome = 'stop'
                    pnl_pts = -risk
                    exit_price = stop
                    break
                if fb['high'] >= target:
                    outcome = 'target'
                    pnl_pts = target - entry
                    exit_price = target
                    break
                pnl_pts = fb['close'] - entry
                exit_price = fb['close']
            else:
                if fb['high'] >= stop:
                    outcome = 'stop'
                    pnl_pts = -risk
                    exit_price = stop
                    break
                if fb['low'] <= target:
                    outcome = 'target'
                    pnl_pts = entry - target
                    exit_price = target
                    break
                pnl_pts = entry - fb['close']
                exit_price = fb['close']
        trades.append({
            'date': date,
            'time_et': entry_time,
            'direction': direction,
            'entry': entry,
            'stop': stop,
            'target_1': target,
            'risk_pts': risk,
            'exit': exit_price,
            'outcome': outcome,
            'pnl_pts': pnl_pts,
            'pnl_usd': pnl_pts * 5.0,  # $5/tick NQ
        })
    return trades


# ── Run experiments ────────────────────────────────────────────────────────

if __name__ == '__main__':
    df = pd.read_csv('data/ml/features_230d.csv')
    df['date'] = df['date'].astype(str)
    df['datetime_et'] = pd.to_datetime(df['date'] + ' ' + df['time_et'])
    v8b = df[(df['date'] >= '20250204') & (df['date'] <= '20250211')]
    v8b_ny = v8b[(v8b['tod'] >= 9.5) & (v8b['tod'] <= 16.0)].copy()

    print('=' * 80)
    print('Fabio Model — Tuned Variants on V8b (4-11 Feb 2025)')
    print('=' * 80)

    # Variant 1: Tighter triggers (>=50 contracts, lvn_lookback=10)
    print('\n[Variant 1: min_big_size=50, lvn_lookback=10, swing_lookback=3, R:R=1:1, hold=12]')
    s1 = run_fabio_tuned(v8b_ny, min_big_size=50, lvn_lookback=10, swing_lookback=3)
    print(f'  Setups: {len(s1)}')
    if s1:
        t1 = simulate_pnl(s1, v8b_ny, hold_bars=6, target_r=1.0, max_hold=12)
        if t1:
            df_t1 = pd.DataFrame(t1)
            wins = (df_t1['outcome'] == 'target').sum()
            losses = (df_t1['outcome'] == 'stop').sum()
            timeouts = (df_t1['outcome'] == 'timeout').sum()
            total_pnl = df_t1['pnl_usd'].sum()
            print(f'  Trades: {len(t1)} | Wins: {wins} | Losses: {losses} | Timeouts: {timeouts}')
            print(f'  Win rate: {wins/len(t1)*100:.1f}%')
            print(f'  Total PnL: ${total_pnl:.0f} ({total_pnl/50:.0f}R)')

    # Variant 2: Looser (>=30 contracts, lvn_lookback=20)
    print('\n[Variant 2: min_big_size=30, lvn_lookback=20, swing_lookback=3, R:R=2:1, hold=12]')
    s2 = run_fabio_tuned(v8b_ny, min_big_size=30, lvn_lookback=20, swing_lookback=3)
    print(f'  Setups: {len(s2)}')
    if s2:
        t2 = simulate_pnl(s2, v8b_ny, hold_bars=6, target_r=2.0, max_hold=12)
        if t2:
            df_t2 = pd.DataFrame(t2)
            wins = (df_t2['outcome'] == 'target').sum()
            losses = (df_t2['outcome'] == 'stop').sum()
            timeouts = (df_t2['outcome'] == 'timeout').sum()
            total_pnl = df_t2['pnl_usd'].sum()
            print(f'  Trades: {len(t2)} | Wins: {wins} | Losses: {losses} | Timeouts: {timeouts}')
            print(f'  Win rate: {wins/len(t2)*100:.1f}%')
            print(f'  Total PnL: ${total_pnl:.0f} ({total_pnl/50:.0f}R)')

    # Variant 3: Even looser (>=30 contracts, lvn_lookback=30, swing_lookback=2)
    print('\n[Variant 3: min_big_size=30, lvn_lookback=30, swing_lookback=2, R:R=3:1, hold=18]')
    s3 = run_fabio_tuned(v8b_ny, min_big_size=30, lvn_lookback=30, swing_lookback=2)
    print(f'  Setups: {len(s3)}')
    if s3:
        t3 = simulate_pnl(s3, v8b_ny, hold_bars=6, target_r=3.0, max_hold=18)
        if t3:
            df_t3 = pd.DataFrame(t3)
            wins = (df_t3['outcome'] == 'target').sum()
            losses = (df_t3['outcome'] == 'stop').sum()
            timeouts = (df_t3['outcome'] == 'timeout').sum()
            total_pnl = df_t3['pnl_usd'].sum()
            print(f'  Trades: {len(t3)} | Wins: {wins} | Losses: {losses} | Timeouts: {timeouts}')
            print(f'  Win rate: {wins/len(t3)*100:.1f}%')
            print(f'  Total PnL: ${total_pnl:.0f} ({total_pnl/50:.0f}R)')

    print('\n' + '=' * 80)
    print('V8b TARGET: +$666 (3 trades: 1 short BE, 1 short -$50, 1 long +$766)')
    print('=' * 80)
