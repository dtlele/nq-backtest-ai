"""
Mock Tick Generator — SOLO per test UI/dev. MAI per backtest/strategia.

Genera tick virtuali da cache_ohlc (OHLC 1min, senza volume):
- volume stimato da range + sessione NY
- random walk open->close vincolata in [low, high]
- side 65/35 in base alla direzione candela
- big trade randomici (size >= 30)

Output: cache_mock/YYYYMMDD.csv con colonne ts_event,action,side,price,size
(formato identico a quello atteso da platform/data_service._load_csv_raw).

Uso:
  python scripts/mock_tick_generator.py --date 2025-02-03
  python scripts/mock_tick_generator.py --all --out cache_mock
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent
CACHE_OHLC = PROJECT_ROOT / 'cache_ohlc'
TICK = 0.25
BIG_TRADE_THRESHOLD = 30


def generate_day(ohlc_csv: Path, seed: int = 42) -> pd.DataFrame:
    """Genera tick sintetici per un giorno di OHLC 1min."""
    rng = np.random.default_rng(seed)
    df = pd.read_csv(ohlc_csv)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)

    rows = []
    for bar in df.itertuples(index=False):
        ts_open = bar.timestamp
        o, h, l, c = bar.open, bar.high, bar.low, bar.close
        if not (np.isfinite(o) and np.isfinite(h) and np.isfinite(l) and np.isfinite(c)) or h < l:
            continue

        rng_bar = np.random.default_rng(seed + int(ts_open.timestamp()))

        # Volume stimato: base + range, boost ore NY (13:30-16:00 UTC)
        hour = ts_open.hour + ts_open.minute / 60
        ny_boost = 2.5 if 13.5 <= hour < 16.0 else (1.5 if 16.0 <= hour < 21.0 else 1.0)
        vol = int((400 + (h - l) * 120) * ny_boost * rng_bar.uniform(0.7, 1.3))
        vol = max(50, vol)

        # Side dominante
        up = c > o
        p_buy = 0.65 if up else (0.35 if c < o else 0.50)

        # Tick sizes
        n_ticks = max(10, vol // 2)
        sizes = rng_bar.choice([1, 2, 3, 4, 5, 7, 10], size=n_ticks,
                               p=[0.60, 0.25, 0.05, 0.04, 0.03, 0.02, 0.01])
        # Scala per matchare il volume target
        scale = vol / sizes.sum()
        sizes = np.maximum(1, np.round(sizes * scale)).astype(int)

        # Random walk open -> close vincolata in [l, h]
        steps = rng_bar.normal(0, 1, size=n_ticks).cumsum()
        steps = (steps - steps.min()) / max(1e-9, np.ptp(steps))  # 0..1
        drift = np.linspace(0, 1, n_ticks)
        prices = o + (c - o) * (0.5 * steps + 0.5 * drift)
        prices = np.clip(prices, l, h)
        prices = np.round(prices / TICK) * TICK
        # Forza fedelta' OHLC: primo tick=open, ultimo=close, tocca high e low
        prices[0] = o
        prices[-1] = c
        prices[rng_bar.integers(1, max(2, n_ticks // 2))] = h
        prices[rng_bar.integers(max(2, n_ticks // 2), n_ticks)] = l

        sides = np.where(rng_bar.random(n_ticks) < p_buy, 'A', 'B')

        # Big trade randomico (~3% per minuto)
        if rng_bar.random() < 0.03:
            idx = rng_bar.integers(0, n_ticks)
            sizes[idx] = int(rng_bar.integers(BIG_TRADE_THRESHOLD, 150))
            sides[idx] = 'A' if up else 'B'

        # Timestamp ns spalmati nel minuto, monotoni
        offsets = np.sort(rng_bar.integers(0, 60_000_000_000, size=n_ticks))
        ts_ns = ts_open.value + offsets

        for i in range(n_ticks):
            rows.append((ts_ns[i], 'T', sides[i], float(prices[i]), int(sizes[i])))

    out = pd.DataFrame(rows, columns=['ts_event', 'action', 'side', 'price', 'size'])
    out['ts_event'] = pd.to_datetime(out['ts_event'], utc=True)
    return out


def main():
    ap = argparse.ArgumentParser(description='Mock tick generator (SOLO UI/dev)')
    ap.add_argument('--date', help='Data YYYY-MM-DD')
    ap.add_argument('--all', action='store_true', help='Tutti i file in cache_ohlc')
    ap.add_argument('--out', default='cache_mock', help='Directory output')
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()

    out_dir = PROJECT_ROOT / args.out
    out_dir.mkdir(exist_ok=True)

    if args.date:
        files = [CACHE_OHLC / f"{args.date.replace('-', '')}.csv"]
    elif args.all:
        files = sorted(CACHE_OHLC.glob('*.csv'))
    else:
        print('Specifica --date o --all')
        sys.exit(1)

    for f in files:
        if not f.exists():
            print(f'[SKIP] {f.name} non trovato')
            continue
        df = generate_day(f, seed=args.seed)
        out_path = out_dir / f.name
        df.to_csv(out_path, index=False)
        n_big = (df['size'] >= BIG_TRADE_THRESHOLD).sum()
        print(f'[OK] {f.name}: {len(df)} tick, vol={df["size"].sum()}, big_trades={n_big} -> {out_path}')


if __name__ == '__main__':
    main()
