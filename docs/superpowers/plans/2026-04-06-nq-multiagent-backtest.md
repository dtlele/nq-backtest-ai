# NQ Multi-Agent Backtesting System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-agent AI backtesting system for NQ futures that uses two Claude agents — one reasoning with Andrea Cimi's PBD/Failed-Auction methodology and one with Fabio Valentini's Squeeze/IVB methodology — to evaluate each trade opportunity in 106 days of DataBento MBP-1 tick data, produce per-trade reasoning logs, and output a full performance metrics report.

**Architecture:** Pre-compute all bar aggregates and indicators offline using pandas, detect "candidate windows" (price near VA edges, IB breakouts, large delta divergences) to limit expensive Claude API calls to ~20–50 per day, then call two parallel Claude API agents per candidate window. A consensus layer combines signals before trade simulation.

**Tech Stack:** Python 3.11+, pandas, numpy, anthropic SDK, python-dotenv, matplotlib, pytest, DataBento MBP-1 CSV data (`C:\Users\Mauro\Documents\databento-data\`)

---

## File Map

```
nq-backtest/
├── src/
│   ├── __init__.py
│   ├── data_loader.py          # Parse DataBento CSVs → raw Trade list
│   ├── bar_aggregator.py       # Aggregate trades → 1-min/5-min OHLCV+delta bars
│   ├── volume_profile.py       # Session VP: VA (70%), POC, HVN, LVN
│   ├── session_context.py      # IB (first 30 min), session times, no-trade zones
│   ├── candidate_detector.py   # Rule-based filter: which bars need agent review
│   ├── signal_context.py       # Build context dict sent to agents per candidate
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py       # Claude API call wrapper (structured JSON output)
│   │   ├── andrea_agent.py     # Andrea Cimi: PBD patterns + Failed Auction
│   │   └── fabio_agent.py      # Fabio Valentini: Squeeze + IVB breakout
│   ├── consensus.py            # Combine two signals → ConsensusSignal or no-trade
│   ├── trade_simulator.py      # Execute trades, track P&L, mark-to-market
│   ├── backtest_runner.py      # Main loop: days → bars → candidates → signals → trades
│   └── metrics_reporter.py     # Win rate, profit factor, equity curve, reasoning log
├── tests/
│   ├── test_data_loader.py
│   ├── test_bar_aggregator.py
│   ├── test_volume_profile.py
│   ├── test_session_context.py
│   ├── test_candidate_detector.py
│   ├── test_signal_context.py
│   ├── test_agents.py          # Mocked Claude API — no real calls in tests
│   ├── test_consensus.py
│   ├── test_trade_simulator.py
│   └── test_metrics_reporter.py
├── output/
│   ├── reasoning_logs/         # JSONL file per day, one entry per trade
│   └── reports/                # metrics_YYYY-MM-DD.md + equity_curve.png
├── docs/superpowers/plans/
│   └── 2026-04-06-nq-multiagent-backtest.md  ← this file
├── .env                        # ANTHROPIC_API_KEY=sk-...
├── requirements.txt
└── run_backtest.py             # CLI entry point
```

---

## Core Data Structures (defined in `src/__init__.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict

@dataclass
class Trade:
    ts_event: int     # nanosecond unix timestamp
    side: str         # 'A' = ask aggressor (buyer), 'B' = bid aggressor (seller)
    price: float      # actual price (DataBento raw / 1e9)
    size: int         # contracts

@dataclass
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    buy_volume: int   # sum of size where side='A'
    sell_volume: int  # sum of size where side='B'
    delta: int        # buy_volume - sell_volume
    delta_pct: float  # abs(delta)/volume*100; 0 if volume=0
    cvd: int          # cumulative session delta up to this bar
    vwap: float
    big_trades: List[Trade] = field(default_factory=list)  # size >= 30

@dataclass
class VolumeProfile:
    poc: float
    va_high: float
    va_low: float
    hvn_levels: List[float]   # up to 5 HVN prices
    lvn_levels: List[float]   # up to 5 LVN prices

@dataclass
class SessionContext:
    date: str           # 'YYYY-MM-DD'
    ib_high: float
    ib_low: float
    ib_complete: bool
    daily_vp: Optional[VolumeProfile]
    is_tradeable: bool  # False during news, lunch, first hour

@dataclass
class TradeSignal:
    agent: str          # 'andrea' | 'fabio'
    direction: str      # 'long' | 'short' | 'none'
    confidence: int     # 0-100
    entry: Optional[float]
    stop: Optional[float]
    target: Optional[float]
    setup_type: str     # e.g. 'failed_auction' | 'squeeze' | 'pbd_p' | 'ib_breakout'
    reasoning: str

@dataclass
class ConsensusSignal:
    direction: str
    entry: float
    stop: float
    target: float
    andrea: TradeSignal
    fabio: TradeSignal
    agreement: str      # 'unanimous' | 'weighted' | 'no_trade'

@dataclass
class OpenTrade:
    direction: str
    entry: float
    stop: float
    target: float
    entry_time: datetime
    size: int           # contracts (1 for backtesting simplicity)
    andrea_reasoning: str
    fabio_reasoning: str

@dataclass
class ClosedTrade:
    direction: str
    entry: float
    stop: float
    target: float
    exit_price: float
    exit_reason: str    # 'target' | 'stop' | 'eod'
    pnl_ticks: float    # (exit - entry) * direction_sign / tick_size
    pnl_usd: float      # pnl_ticks * $5/tick for NQ
    entry_time: datetime
    exit_time: datetime
    andrea_reasoning: str
    fabio_reasoning: str
    setup_type: str
```

---

## Key Constants

```python
# NQ Futures
NQ_TICK_SIZE = 0.25        # points
NQ_TICK_VALUE = 5.0        # USD per tick
NQ_BIG_TRADE_THRESHOLD = 30  # contracts/trade (Fabio's filter)

# Sessions (UTC offsets for EST = UTC-5 standard, UTC-4 summer)
# DataBento timestamps are UTC nanoseconds
NY_OPEN_EST  = (9, 30)     # 09:30 EST
NY_CLOSE_EST = (16, 0)     # 16:00 EST
NY_LUNCH_START_EST = (12, 0)
NY_LUNCH_END_EST   = (13, 30)
IB_DURATION_MIN = 30       # Initial Balance: first 30 min of NY session

# Volume Profile
VA_PERCENTAGE = 0.70       # Value Area = 70% of session volume
TICK_BUCKET_SIZE = 0.25    # group prices into 0.25-point buckets

# Candidate Detection
MIN_VOLUME_PER_BAR = 3000  # below this, skip (Andrea's "negligible" threshold)
DELTA_PCT_INITIATIVE = 10  # above 10% = initiative candle (Andrea's rule)
DELTA_PCT_ABSORBED   = -5  # negative delta at price high = absorption
VA_PROXIMITY_TICKS   = 4   # candidate if price within 4 ticks of VA edge or POC
```

---

## Task 1: Project Setup + Data Loader

**Files:**
- Create: `src/__init__.py` (data structures above)
- Create: `src/data_loader.py`
- Create: `tests/test_data_loader.py`
- Create: `requirements.txt`
- Create: `.env.example`

- [ ] **Step 1.1: Create `requirements.txt`**

```
pandas>=2.0
numpy>=1.25
anthropic>=0.25
python-dotenv>=1.0
matplotlib>=3.7
pytest>=7.4
pytest-mock>=3.11
```

Install: `pip install -r requirements.txt`

- [ ] **Step 1.2: Create `src/__init__.py` with all data structures**

Copy the Core Data Structures block above verbatim. Also add:

```python
NQ_TICK_SIZE = 0.25
NQ_TICK_VALUE = 5.0
NQ_BIG_TRADE_THRESHOLD = 30
VA_PERCENTAGE = 0.70
TICK_BUCKET_SIZE = 0.25
MIN_VOLUME_PER_BAR = 3000
DELTA_PCT_INITIATIVE = 10.0
VA_PROXIMITY_TICKS = 4
IB_DURATION_MIN = 30
```

- [ ] **Step 1.3: Write failing test for data_loader**

```python
# tests/test_data_loader.py
import pytest
from pathlib import Path
import tempfile, textwrap
from src.data_loader import load_day, list_data_files

SAMPLE_CSV = textwrap.dedent("""\
    ts_recv,ts_event,rtype,publisher_id,instrument_id,action,side,depth,price,size,flags,ts_in_delta,sequence,symbol
    1746000000000000000,1746000000000000001,0,1,1,T,A,0,200000000000,5,0,1000,1,NQM5
    1746000000100000000,1746000000100000001,0,1,1,T,B,0,199750000000,10,0,1000,2,NQM5
    1746000000200000000,1746000000200000001,0,1,1,T,A,0,200000000000,35,0,1000,3,NQM5
""")

def test_load_day_returns_trades():
    with tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False) as f:
        f.write(SAMPLE_CSV)
        path = f.name
    trades = load_day(path)
    assert len(trades) == 3
    assert trades[0].side == 'A'
    assert trades[0].price == pytest.approx(200.0)   # 200000000000 / 1e9 = 200.0
    assert trades[0].size == 5
    assert trades[1].side == 'B'
    assert trades[1].price == pytest.approx(199.75)
    assert trades[2].size == 35  # big trade

def test_load_day_filters_non_trade_actions():
    # rows with action != 'T' (e.g. 'A' for add, 'C' for cancel) must be skipped
    csv = SAMPLE_CSV.replace(',T,A,', ',A,A,', 1)  # first row action=A
    with tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False) as f:
        f.write(csv)
        path = f.name
    trades = load_day(path)
    assert len(trades) == 2  # only the T rows

def test_list_data_files():
    with tempfile.TemporaryDirectory() as d:
        Path(d, 'glbx-mdp3-20250401.trades.csv').touch()
        Path(d, 'glbx-mdp3-20250402.trades.csv').touch()
        Path(d, 'other.txt').touch()
        files = list_data_files(d)
        assert len(files) == 2
        assert all(f.endswith('.trades.csv') for f in files)
```

- [ ] **Step 1.4: Run test — verify FAIL**

```bash
cd C:\Users\Mauro\Documents\nq-backtest
pytest tests/test_data_loader.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.data_loader'`

- [ ] **Step 1.5: Implement `src/data_loader.py`**

```python
# src/data_loader.py
import glob
import os
import pandas as pd
from src import Trade

PRICE_SCALE = 1e9

def load_day(filepath: str) -> list[Trade]:
    """Load one DataBento trades CSV. Returns only action='T' rows as Trade objects."""
    df = pd.read_csv(filepath, usecols=['ts_event', 'action', 'side', 'price', 'size'])
    df = df[df['action'] == 'T'].copy()
    df['price_actual'] = df['price'] / PRICE_SCALE
    trades = [
        Trade(
            ts_event=int(row.ts_event),
            side=row.side,
            price=float(row.price_actual),
            size=int(row.size),
        )
        for row in df.itertuples(index=False)
    ]
    return trades

def list_data_files(directory: str) -> list[str]:
    """Return sorted list of *.trades.csv paths in directory."""
    pattern = os.path.join(directory, '*.trades.csv')
    return sorted(glob.glob(pattern))
```

- [ ] **Step 1.6: Run test — verify PASS**

```bash
pytest tests/test_data_loader.py -v
```
Expected: all 3 tests PASS

- [ ] **Step 1.7: Commit**

```bash
git -C C:\Users\Mauro\Documents\nq-backtest init
git -C C:\Users\Mauro\Documents\nq-backtest add src/__init__.py src/data_loader.py tests/test_data_loader.py requirements.txt
git -C C:\Users\Mauro\Documents\nq-backtest commit -m "feat: data structures + DataBento CSV loader"
```

---

## Task 2: Bar Aggregator

**Files:**
- Create: `src/bar_aggregator.py`
- Create: `tests/test_bar_aggregator.py`

Aggregates raw trades into 1-minute bars. Each bar computes OHLCV, delta, delta_pct, CVD (cumulative since midnight UTC or session start), VWAP, and the list of big trades (size ≥ 30).

DataBento `ts_event` is nanoseconds since Unix epoch (UTC). Convert to UTC datetime, then to US/Eastern for session logic.

- [ ] **Step 2.1: Write failing tests**

```python
# tests/test_bar_aggregator.py
import pytest
from datetime import datetime, timezone
from src import Trade, NQ_BIG_TRADE_THRESHOLD
from src.bar_aggregator import aggregate_to_bars

def _ns(dt_str: str) -> int:
    """Parse 'YYYY-MM-DD HH:MM:SS' UTC to nanoseconds."""
    dt = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1e9)

def test_single_bar_ohlcv():
    trades = [
        Trade(_ns('2025-04-01 13:30:05'), 'A', 20000.00, 10),  # buy
        Trade(_ns('2025-04-01 13:30:10'), 'B', 19999.75, 20),  # sell
        Trade(_ns('2025-04-01 13:30:55'), 'A', 20000.25, 5),   # buy
    ]
    bars = aggregate_to_bars(trades, freq='1min')
    assert len(bars) == 1
    b = bars[0]
    assert b.open == pytest.approx(20000.00)
    assert b.high == pytest.approx(20000.25)
    assert b.low  == pytest.approx(19999.75)
    assert b.close == pytest.approx(20000.25)
    assert b.volume == 35
    assert b.buy_volume == 15   # 10 + 5
    assert b.sell_volume == 20
    assert b.delta == -5        # 15 - 20
    assert b.delta_pct == pytest.approx(abs(-5) / 35 * 100)

def test_cvd_accumulates_across_bars():
    trades = [
        Trade(_ns('2025-04-01 13:30:05'), 'A', 20000.00, 30),  # bar 1: delta +30
        Trade(_ns('2025-04-01 13:31:05'), 'B', 20000.00, 10),  # bar 2: delta -10
    ]
    bars = aggregate_to_bars(trades, freq='1min')
    assert len(bars) == 2
    assert bars[0].cvd == 30
    assert bars[1].cvd == 20   # 30 + (-10)

def test_big_trades_captured():
    trades = [
        Trade(_ns('2025-04-01 13:30:05'), 'A', 20000.00, 29),  # not big
        Trade(_ns('2025-04-01 13:30:10'), 'B', 20000.00, 30),  # exactly threshold
        Trade(_ns('2025-04-01 13:30:15'), 'A', 20000.00, 100), # big
    ]
    bars = aggregate_to_bars(trades, freq='1min')
    assert len(bars[0].big_trades) == 2
    assert all(t.size >= NQ_BIG_TRADE_THRESHOLD for t in bars[0].big_trades)

def test_vwap_calculation():
    trades = [
        Trade(_ns('2025-04-01 13:30:05'), 'A', 100.0, 10),
        Trade(_ns('2025-04-01 13:30:10'), 'A', 200.0, 10),
    ]
    bars = aggregate_to_bars(trades, freq='1min')
    assert bars[0].vwap == pytest.approx(150.0)  # (100*10 + 200*10) / 20

def test_delta_pct_zero_volume_bar():
    # Should not raise ZeroDivisionError
    bars = aggregate_to_bars([], freq='1min')
    assert bars == []
```

- [ ] **Step 2.2: Run test — verify FAIL**

```bash
pytest tests/test_bar_aggregator.py -v
```

- [ ] **Step 2.3: Implement `src/bar_aggregator.py`**

```python
# src/bar_aggregator.py
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from src import Trade, Bar, NQ_BIG_TRADE_THRESHOLD

def aggregate_to_bars(trades: list[Trade], freq: str = '1min') -> list[Bar]:
    """Aggregate list of Trade objects into OHLCV+delta bars."""
    if not trades:
        return []

    records = [
        {
            'ts': pd.Timestamp(t.ts_event, unit='ns', tz='UTC'),
            'side': t.side,
            'price': t.price,
            'size': t.size,
        }
        for t in trades
    ]
    df = pd.DataFrame(records).set_index('ts').sort_index()
    df['buy_vol']  = np.where(df['side'] == 'A', df['size'], 0)
    df['sell_vol'] = np.where(df['side'] == 'B', df['size'], 0)
    df['dollar']   = df['price'] * df['size']
    df['is_big']   = df['size'] >= NQ_BIG_TRADE_THRESHOLD

    grouped = df.resample(freq)
    ohlcv = grouped['price'].ohlc()
    vol   = grouped['size'].sum().rename('volume')
    buy   = grouped['buy_vol'].sum().rename('buy_volume')
    sell  = grouped['sell_vol'].sum().rename('sell_volume')
    dol   = grouped['dollar'].sum().rename('dollar')

    agg = pd.concat([ohlcv, vol, buy, sell, dol], axis=1).dropna(subset=['open'])
    agg['delta']     = agg['buy_volume'] - agg['sell_volume']
    agg['delta_pct'] = np.where(
        agg['volume'] > 0,
        agg['delta'].abs() / agg['volume'] * 100,
        0.0
    )
    agg['vwap'] = np.where(agg['volume'] > 0, agg['dollar'] / agg['volume'], agg['close'])

    # Build big_trades index: ts_floor -> list of Trade
    big_map: dict[pd.Timestamp, list[Trade]] = {}
    for t, row in zip(trades, records):
        if t.size >= NQ_BIG_TRADE_THRESHOLD:
            floor = row['ts'].floor(freq)
            big_map.setdefault(floor, []).append(t)

    # Compute CVD (cumulative delta across all bars)
    agg['cvd'] = agg['delta'].cumsum()

    bars = []
    for ts, row in agg.iterrows():
        bars.append(Bar(
            timestamp=ts.to_pydatetime(),
            open=float(row['open']),
            high=float(row['high']),
            low=float(row['low']),
            close=float(row['close']),
            volume=int(row['volume']),
            buy_volume=int(row['buy_volume']),
            sell_volume=int(row['sell_volume']),
            delta=int(row['delta']),
            delta_pct=float(row['delta_pct']),
            cvd=int(row['cvd']),
            vwap=float(row['vwap']),
            big_trades=big_map.get(ts, []),
        ))
    return bars
```

- [ ] **Step 2.4: Run test — verify PASS**

```bash
pytest tests/test_bar_aggregator.py -v
```

- [ ] **Step 2.5: Commit**

```bash
git -C C:\Users\Mauro\Documents\nq-backtest add src/bar_aggregator.py tests/test_bar_aggregator.py
git -C C:\Users\Mauro\Documents\nq-backtest commit -m "feat: bar aggregator with OHLCV, delta, CVD, big trades"
```

---

## Task 3: Volume Profile

**Files:**
- Create: `src/volume_profile.py`
- Create: `tests/test_volume_profile.py`

Computes session Volume Profile: POC, Value Area (70%), top-5 HVN, top-5 LVN.

- [ ] **Step 3.1: Write failing tests**

```python
# tests/test_volume_profile.py
import pytest
from src import Bar, VA_PERCENTAGE
from src.volume_profile import compute_volume_profile
from datetime import datetime

def _bar(price: float, volume: int) -> Bar:
    return Bar(
        timestamp=datetime(2025, 4, 1, 14, 0),
        open=price, high=price+0.25, low=price-0.25, close=price,
        volume=volume, buy_volume=volume//2, sell_volume=volume//2,
        delta=0, delta_pct=0.0, cvd=0, vwap=price
    )

def test_poc_is_highest_volume_price():
    bars = [_bar(100.00, 100), _bar(100.25, 200), _bar(100.50, 50)]
    vp = compute_volume_profile(bars)
    assert vp.poc == pytest.approx(100.25)

def test_value_area_contains_70pct():
    # All volume at 100.00 (heavy), with smaller amounts around
    bars = [_bar(99.75, 10), _bar(100.00, 700), _bar(100.25, 10), _bar(100.50, 10)]
    vp = compute_volume_profile(bars)
    total = 730
    # VA must contain at least 70% of total
    assert vp.va_low <= 100.00 <= vp.va_high

def test_empty_bars_returns_none():
    vp = compute_volume_profile([])
    assert vp is None

def test_hvn_lvn_identified():
    # Create clear peaks and valleys
    bars = [
        _bar(99.75, 10),
        _bar(100.00, 500),  # HVN
        _bar(100.25, 10),   # LVN
        _bar(100.50, 400),  # HVN
        _bar(100.75, 5),    # LVN
    ]
    vp = compute_volume_profile(bars)
    assert 100.00 in vp.hvn_levels or 100.50 in vp.hvn_levels
    assert len(vp.hvn_levels) >= 1
```

- [ ] **Step 3.2: Run test — verify FAIL**

```bash
pytest tests/test_volume_profile.py -v
```

- [ ] **Step 3.3: Implement `src/volume_profile.py`**

```python
# src/volume_profile.py
import numpy as np
import pandas as pd
from src import Bar, VolumeProfile, VA_PERCENTAGE, TICK_BUCKET_SIZE

def compute_volume_profile(bars: list[Bar]) -> VolumeProfile | None:
    """Build session volume profile from list of bars."""
    if not bars:
        return None

    # Aggregate volume at each price bucket (rounded to TICK_BUCKET_SIZE)
    price_vol: dict[float, int] = {}
    for bar in bars:
        for price, vol_share in _split_bar_volume(bar):
            bucket = round(round(price / TICK_BUCKET_SIZE) * TICK_BUCKET_SIZE, 2)
            price_vol[bucket] = price_vol.get(bucket, 0) + vol_share

    if not price_vol:
        return None

    prices = sorted(price_vol.keys())
    volumes = [price_vol[p] for p in prices]
    total_vol = sum(volumes)

    # POC = price with highest volume
    poc_idx = int(np.argmax(volumes))
    poc = prices[poc_idx]

    # Value Area (70%): expand outward from POC
    va_low, va_high = _compute_value_area(prices, volumes, poc_idx, total_vol)

    # HVN: top-5 peaks (local maxima with volume > mean)
    hvn_levels, lvn_levels = _compute_hvn_lvn(prices, volumes)

    return VolumeProfile(
        poc=poc,
        va_high=va_high,
        va_low=va_low,
        hvn_levels=hvn_levels,
        lvn_levels=lvn_levels,
    )

def _split_bar_volume(bar: Bar) -> list[tuple[float, int]]:
    """Distribute bar volume across OHLC range uniformly."""
    prices = sorted({bar.open, bar.high, bar.low, bar.close})
    if len(prices) == 1:
        return [(prices[0], bar.volume)]
    share = bar.volume // len(prices)
    return [(p, share) for p in prices]

def _compute_value_area(
    prices: list[float], volumes: list[int], poc_idx: int, total: int
) -> tuple[float, float]:
    target = total * VA_PERCENTAGE
    lo = hi = poc_idx
    accumulated = volumes[poc_idx]
    while accumulated < target:
        up_vol   = volumes[hi + 1] if hi + 1 < len(prices) else 0
        down_vol = volumes[lo - 1] if lo - 1 >= 0 else 0
        if up_vol >= down_vol and hi + 1 < len(prices):
            hi += 1
            accumulated += up_vol
        elif lo - 1 >= 0:
            lo -= 1
            accumulated += down_vol
        else:
            break
    return prices[lo], prices[hi]

def _compute_hvn_lvn(
    prices: list[float], volumes: list[int], top_n: int = 5
) -> tuple[list[float], list[float]]:
    if len(volumes) < 3:
        return [], []
    arr = np.array(volumes, dtype=float)
    mean_vol = arr.mean()
    hvn, lvn = [], []
    for i in range(1, len(arr) - 1):
        if arr[i] > arr[i-1] and arr[i] > arr[i+1] and arr[i] > mean_vol:
            hvn.append((prices[i], arr[i]))
        if arr[i] < arr[i-1] and arr[i] < arr[i+1] and arr[i] < mean_vol:
            lvn.append((prices[i], arr[i]))
    hvn.sort(key=lambda x: -x[1])
    lvn.sort(key=lambda x: x[1])
    return [p for p, _ in hvn[:top_n]], [p for p, _ in lvn[:top_n]]
```

- [ ] **Step 3.4: Run test — verify PASS**

```bash
pytest tests/test_volume_profile.py -v
```

- [ ] **Step 3.5: Commit**

```bash
git -C C:\Users\Mauro\Documents\nq-backtest add src/volume_profile.py tests/test_volume_profile.py
git -C C:\Users\Mauro\Documents\nq-backtest commit -m "feat: volume profile with VA, POC, HVN, LVN"
```

---

## Task 4: Session Context + Candidate Detector

**Files:**
- Create: `src/session_context.py`
- Create: `src/candidate_detector.py`
- Create: `tests/test_session_context.py`
- Create: `tests/test_candidate_detector.py`

Session context determines: IB range (first 30 min), is_tradeable (no lunch, no news), session phase.
Candidate detector identifies bars worth sending to agents (~20–50/day max).

- [ ] **Step 4.1: Write failing tests for session_context**

```python
# tests/test_session_context.py
import pytest
from datetime import datetime, timezone
from src.session_context import (
    bar_timestamp_est, is_ny_session, is_lunch, is_in_ib_window,
    build_session_context
)
from src import Bar

def _utc_bar(hour: int, minute: int) -> Bar:
    # e.g. 2025-04-01 14:30 UTC = 10:30 EDT (summer, UTC-4)
    ts = datetime(2025, 4, 1, hour, minute, 0, tzinfo=timezone.utc)
    return Bar(ts, 20000, 20001, 19999, 20000, 1000, 500, 500, 0, 0.0, 0, 20000)

def test_ny_session_recognition():
    # 14:30 UTC = 10:30 EDT → in NY session
    assert is_ny_session(_utc_bar(14, 30))
    # 12:00 UTC = 08:00 EDT → pre-market, not in session
    assert not is_ny_session(_utc_bar(12, 0))
    # 21:00 UTC = 17:00 EDT → after close
    assert not is_ny_session(_utc_bar(21, 0))

def test_lunch_detection():
    # 16:15 UTC = 12:15 EDT → lunch
    assert is_lunch(_utc_bar(16, 15))
    # 14:45 UTC = 10:45 EDT → not lunch
    assert not is_lunch(_utc_bar(14, 45))

def test_ib_window():
    # 13:30 UTC = 09:30 EDT → start of IB window
    assert is_in_ib_window(_utc_bar(13, 30))
    # 13:59 UTC = 09:59 EDT → still in IB window (< 30 min)
    assert is_in_ib_window(_utc_bar(13, 59))
    # 14:01 UTC = 10:01 EDT → IB complete
    assert not is_in_ib_window(_utc_bar(14, 1))
```

- [ ] **Step 4.2: Write failing tests for candidate_detector**

```python
# tests/test_candidate_detector.py
import pytest
from datetime import datetime, timezone
from src import Bar, VolumeProfile
from src.candidate_detector import is_candidate

def _bar(price: float, delta: int, volume: int, cvd: int, ts=None) -> Bar:
    if ts is None:
        ts = datetime(2025, 4, 1, 15, 0, tzinfo=timezone.utc)  # 11:00 EDT, NY session
    delta_pct = abs(delta) / volume * 100 if volume else 0
    return Bar(ts, price, price+0.25, price-0.25, price,
               volume, max(0,delta), max(0,-delta), delta, delta_pct, cvd, price)

VP = VolumeProfile(poc=20000.0, va_high=20010.0, va_low=19990.0, hvn_levels=[], lvn_levels=[])

def test_price_near_va_high_is_candidate():
    bar = _bar(price=20010.25, delta=50, volume=5000, cvd=100)  # 1 tick above VA_high
    assert is_candidate(bar, VP, ib_high=20020.0, ib_low=19980.0)

def test_low_volume_not_candidate():
    bar = _bar(price=20010.0, delta=50, volume=2000, cvd=100)  # below MIN_VOLUME_PER_BAR
    assert not is_candidate(bar, VP, ib_high=20020.0, ib_low=19980.0)

def test_ib_breakout_is_candidate():
    bar = _bar(price=20021.0, delta=500, volume=8000, cvd=500)  # above IB high
    assert is_candidate(bar, VP, ib_high=20020.0, ib_low=19980.0)

def test_high_delta_pct_is_candidate():
    bar = _bar(price=20005.0, delta=1200, volume=5000, cvd=1200)  # 24% delta
    assert is_candidate(bar, VP, ib_high=20020.0, ib_low=19980.0)

def test_quiet_middle_of_range_not_candidate():
    bar = _bar(price=20000.0, delta=50, volume=5000, cvd=50)  # POC, low delta
    # Not near VA edges by more than 4 ticks, not high delta
    assert not is_candidate(bar, VP, ib_high=20020.0, ib_low=19980.0)
```

- [ ] **Step 4.3: Run tests — verify FAIL**

```bash
pytest tests/test_session_context.py tests/test_candidate_detector.py -v
```

- [ ] **Step 4.4: Implement `src/session_context.py`**

```python
# src/session_context.py
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from src import Bar, SessionContext, VolumeProfile, IB_DURATION_MIN

EST = ZoneInfo('America/New_York')
NY_OPEN  = (9, 30)
NY_CLOSE = (16, 0)
LUNCH_START = (12, 0)
LUNCH_END   = (13, 30)

def bar_timestamp_est(bar: Bar) -> datetime:
    """Convert bar UTC timestamp → US/Eastern (handles DST)."""
    ts = bar.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(EST)

def is_ny_session(bar: Bar) -> bool:
    t = bar_timestamp_est(bar)
    open_dt  = t.replace(hour=NY_OPEN[0],  minute=NY_OPEN[1],  second=0, microsecond=0)
    close_dt = t.replace(hour=NY_CLOSE[0], minute=NY_CLOSE[1], second=0, microsecond=0)
    return open_dt <= t < close_dt

def is_lunch(bar: Bar) -> bool:
    t = bar_timestamp_est(bar)
    start = t.replace(hour=LUNCH_START[0], minute=LUNCH_START[1], second=0, microsecond=0)
    end   = t.replace(hour=LUNCH_END[0],   minute=LUNCH_END[1],   second=0, microsecond=0)
    return start <= t < end

def is_in_ib_window(bar: Bar) -> bool:
    """True if bar falls within first IB_DURATION_MIN of NY session."""
    t = bar_timestamp_est(bar)
    open_dt = t.replace(hour=NY_OPEN[0], minute=NY_OPEN[1], second=0, microsecond=0)
    ib_end  = open_dt + timedelta(minutes=IB_DURATION_MIN)
    return open_dt <= t < ib_end

def build_session_context(date_str: str, bars: list[Bar], daily_vp: VolumeProfile | None) -> SessionContext:
    """Compute IB high/low from first 30 min of NY session bars."""
    ib_bars = [b for b in bars if is_ny_session(b) and is_in_ib_window(b)]
    ib_high = max((b.high for b in ib_bars), default=0.0)
    ib_low  = min((b.low  for b in ib_bars), default=0.0)
    return SessionContext(
        date=date_str,
        ib_high=ib_high,
        ib_low=ib_low,
        ib_complete=len(ib_bars) > 0,
        daily_vp=daily_vp,
        is_tradeable=True,  # caller sets False for news days
    )
```

- [ ] **Step 4.5: Implement `src/candidate_detector.py`**

```python
# src/candidate_detector.py
from src import Bar, VolumeProfile, MIN_VOLUME_PER_BAR, VA_PROXIMITY_TICKS, \
    DELTA_PCT_INITIATIVE, NQ_TICK_SIZE
from src.session_context import is_ny_session, is_lunch

VA_PROX = VA_PROXIMITY_TICKS * NQ_TICK_SIZE  # 4 ticks = 1.0 point

def is_candidate(
    bar: Bar,
    vp: VolumeProfile | None,
    ib_high: float,
    ib_low: float,
) -> bool:
    """Return True if this bar warrants agent review."""
    if bar.volume < MIN_VOLUME_PER_BAR:
        return False
    if not is_ny_session(bar):
        return False
    if is_lunch(bar):
        return False

    price = bar.close

    # 1. Near VA edges (potential failed auction / mean reversion)
    if vp:
        if abs(price - vp.va_high) <= VA_PROX:
            return True
        if abs(price - vp.va_low) <= VA_PROX:
            return True
        if abs(price - vp.poc) <= VA_PROX:
            return True

    # 2. IB breakout (Fabio's key trigger)
    if ib_high > 0 and price > ib_high:
        return True
    if ib_low > 0 and price < ib_low:
        return True

    # 3. High delta percentage (initiative or exhaustion)
    if bar.delta_pct >= DELTA_PCT_INITIATIVE:
        return True

    # 4. Big trade cluster (≥ 2 big trades in this bar)
    if len(bar.big_trades) >= 2:
        return True

    return False
```

- [ ] **Step 4.6: Run tests — verify PASS**

```bash
pytest tests/test_session_context.py tests/test_candidate_detector.py -v
```

- [ ] **Step 4.7: Commit**

```bash
git -C C:\Users\Mauro\Documents\nq-backtest add src/session_context.py src/candidate_detector.py tests/test_session_context.py tests/test_candidate_detector.py
git -C C:\Users\Mauro\Documents\nq-backtest commit -m "feat: session context + candidate bar detector"
```

---

## Task 5: Signal Context Builder

**Files:**
- Create: `src/signal_context.py`
- Create: `tests/test_signal_context.py`

Builds the structured context dict that gets serialized to JSON and sent to each agent. Contains: last 20 bars summary, VP reference levels, IB range, big trades near current price, CVD trend.

- [ ] **Step 5.1: Write failing tests**

```python
# tests/test_signal_context.py
import pytest
from datetime import datetime, timezone
from src import Bar, VolumeProfile, SessionContext
from src.signal_context import build_signal_context

def _bar(i, price=20000.0, delta=100, vol=5000):
    ts = datetime(2025, 4, 1, 14, i % 60, tzinfo=timezone.utc)
    return Bar(ts, price, price+0.5, price-0.5, price, vol, vol//2, vol//2,
               delta, abs(delta)/vol*100, delta*i, price)

VP = VolumeProfile(20000.0, 20010.0, 19990.0, [20005.0], [19995.0])
SESSION = SessionContext('2025-04-01', 20015.0, 19985.0, True, VP, True)

def test_context_has_required_keys():
    bars = [_bar(i) for i in range(25)]
    ctx = build_signal_context(bars[-1], bars[-20:], VP, SESSION)
    for key in ['current_bar', 'recent_bars_summary', 'vp', 'session', 'cvd_trend']:
        assert key in ctx

def test_recent_bars_capped_at_20():
    bars = [_bar(i) for i in range(30)]
    ctx = build_signal_context(bars[-1], bars, VP, SESSION)
    assert len(ctx['recent_bars_summary']) <= 20

def test_cvd_trend_direction():
    # Rising CVD: last bar CVD > first bar CVD
    bars = [_bar(i, delta=100) for i in range(5)]
    ctx = build_signal_context(bars[-1], bars, VP, SESSION)
    assert ctx['cvd_trend'] == 'rising'
```

- [ ] **Step 5.2: Run test — verify FAIL**

```bash
pytest tests/test_signal_context.py -v
```

- [ ] **Step 5.3: Implement `src/signal_context.py`**

```python
# src/signal_context.py
from src import Bar, VolumeProfile, SessionContext, NQ_TICK_SIZE

def build_signal_context(
    current: Bar,
    recent_bars: list[Bar],   # up to last 20
    vp: VolumeProfile | None,
    session: SessionContext,
) -> dict:
    """Build context dict to pass to agent system prompt."""
    recent = recent_bars[-20:]

    # CVD trend: compare first and last CVD in window
    if len(recent) >= 2:
        cvd_diff = recent[-1].cvd - recent[0].cvd
        cvd_trend = 'rising' if cvd_diff > 0 else 'falling' if cvd_diff < 0 else 'flat'
    else:
        cvd_trend = 'flat'

    # Distance from VP levels in ticks
    def ticks_from(level: float) -> int:
        return round((current.close - level) / NQ_TICK_SIZE)

    vp_info = None
    if vp:
        vp_info = {
            'poc': vp.poc,
            'va_high': vp.va_high,
            'va_low': vp.va_low,
            'ticks_from_va_high': ticks_from(vp.va_high),
            'ticks_from_va_low': ticks_from(vp.va_low),
            'ticks_from_poc': ticks_from(vp.poc),
            'hvn_levels': vp.hvn_levels,
            'lvn_levels': vp.lvn_levels,
        }

    # Big trades in recent window (last 5 bars)
    big_trades_nearby = []
    for b in recent[-5:]:
        for t in b.big_trades:
            big_trades_nearby.append({
                'time': str(b.timestamp),
                'side': 'buy' if t.side == 'A' else 'sell',
                'price': t.price,
                'size': t.size,
            })

    return {
        'current_bar': {
            'time': str(current.timestamp),
            'open': current.open, 'high': current.high,
            'low': current.low,  'close': current.close,
            'volume': current.volume,
            'delta': current.delta,
            'delta_pct': round(current.delta_pct, 1),
            'cvd': current.cvd,
        },
        'recent_bars_summary': [
            {
                'time': str(b.timestamp),
                'close': b.close,
                'delta': b.delta,
                'delta_pct': round(b.delta_pct, 1),
                'volume': b.volume,
                'cvd': b.cvd,
            }
            for b in recent
        ],
        'vp': vp_info,
        'session': {
            'date': session.date,
            'ib_high': session.ib_high,
            'ib_low': session.ib_low,
            'ib_complete': session.ib_complete,
        },
        'cvd_trend': cvd_trend,
        'big_trades_nearby': big_trades_nearby,
    }
```

- [ ] **Step 5.4: Run test — verify PASS**

```bash
pytest tests/test_signal_context.py -v
```

- [ ] **Step 5.5: Commit**

```bash
git -C C:\Users\Mauro\Documents\nq-backtest add src/signal_context.py tests/test_signal_context.py
git -C C:\Users\Mauro\Documents\nq-backtest commit -m "feat: signal context builder for agents"
```

---

## Task 6: Agent Layer — Base + Andrea + Fabio

**Files:**
- Create: `src/agents/__init__.py`
- Create: `src/agents/base_agent.py`
- Create: `src/agents/andrea_agent.py`
- Create: `src/agents/fabio_agent.py`
- Create: `tests/test_agents.py`
- Create: `.env.example`

Each agent calls Claude API with a system prompt encoding the trader's methodology, receives a JSON response with direction/confidence/entry/stop/target/reasoning.

**IMPORTANT:** Tests must mock the Anthropic client — never make real API calls in tests.

- [ ] **Step 6.1: Create `.env.example`**

```
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```

Copy to `.env` and fill in your real key. `claude-haiku-4-5-20251001` is cheapest for high-volume backtesting.

- [ ] **Step 6.2: Write failing tests (all mocked)**

```python
# tests/test_agents.py
import pytest
import json
from unittest.mock import MagicMock, patch
from src import TradeSignal
from src.agents.andrea_agent import AndreaCimiAgent
from src.agents.fabio_agent import FabioValentiniAgent

SAMPLE_CONTEXT = {
    'current_bar': {'time': '2025-04-01 14:30', 'close': 20005.0, 'delta': 500,
                    'delta_pct': 12.5, 'volume': 8000, 'cvd': 500},
    'recent_bars_summary': [],
    'vp': {'poc': 20000.0, 'va_high': 20010.0, 'va_low': 19990.0,
           'ticks_from_va_high': -2, 'ticks_from_va_low': 6,
           'ticks_from_poc': 2, 'hvn_levels': [], 'lvn_levels': []},
    'session': {'date': '2025-04-01', 'ib_high': 20015.0, 'ib_low': 19985.0, 'ib_complete': True},
    'cvd_trend': 'rising',
    'big_trades_nearby': [],
}

MOCK_LONG_RESPONSE = json.dumps({
    'direction': 'long',
    'confidence': 75,
    'entry': 20005.25,
    'stop': 20004.0,
    'target': 20009.0,
    'setup_type': 'failed_auction',
    'reasoning': 'Price near VA high with positive delta initiative. CVD rising confirms buyers in control.',
})

MOCK_NO_TRADE_RESPONSE = json.dumps({
    'direction': 'none',
    'confidence': 0,
    'entry': None, 'stop': None, 'target': None,
    'setup_type': 'no_setup',
    'reasoning': 'No clear setup. Volume insufficient.',
})

def _mock_client(response_text: str):
    mock = MagicMock()
    mock.messages.create.return_value = MagicMock(
        content=[MagicMock(text=response_text)]
    )
    return mock

def test_andrea_agent_returns_trade_signal():
    agent = AndreaCimiAgent(client=_mock_client(MOCK_LONG_RESPONSE))
    signal = agent.analyze(SAMPLE_CONTEXT)
    assert isinstance(signal, TradeSignal)
    assert signal.agent == 'andrea'
    assert signal.direction == 'long'
    assert signal.confidence == 75
    assert signal.entry == pytest.approx(20005.25)
    assert signal.stop == pytest.approx(20004.0)
    assert signal.target == pytest.approx(20009.0)
    assert 'CVD' in signal.reasoning

def test_fabio_agent_returns_trade_signal():
    agent = FabioValentiniAgent(client=_mock_client(MOCK_LONG_RESPONSE))
    signal = agent.analyze(SAMPLE_CONTEXT)
    assert isinstance(signal, TradeSignal)
    assert signal.agent == 'fabio'
    assert signal.direction == 'long'

def test_agent_handles_no_trade():
    agent = AndreaCimiAgent(client=_mock_client(MOCK_NO_TRADE_RESPONSE))
    signal = agent.analyze(SAMPLE_CONTEXT)
    assert signal.direction == 'none'
    assert signal.entry is None

def test_agent_handles_malformed_json():
    agent = AndreaCimiAgent(client=_mock_client('INVALID JSON {{{'))
    signal = agent.analyze(SAMPLE_CONTEXT)
    assert signal.direction == 'none'  # graceful fallback
```

- [ ] **Step 6.3: Run test — verify FAIL**

```bash
pytest tests/test_agents.py -v
```

- [ ] **Step 6.4: Implement `src/agents/base_agent.py`**

```python
# src/agents/base_agent.py
import json
import os
from anthropic import Anthropic
from src import TradeSignal

DEFAULT_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-haiku-4-5-20251001')

RESPONSE_SCHEMA = """\
Respond with ONLY valid JSON (no markdown fences) in this exact schema:
{
  "direction": "long" | "short" | "none",
  "confidence": 0-100,
  "entry": float or null,
  "stop": float or null,
  "target": float or null,
  "setup_type": string,
  "reasoning": string (max 300 chars)
}"""

class BaseAgent:
    agent_name: str = 'base'
    system_prompt: str = ''

    def __init__(self, client: Anthropic | None = None):
        self._client = client or Anthropic()

    def analyze(self, context: dict) -> TradeSignal:
        user_msg = (
            f"Market data:\n{json.dumps(context, indent=2)}\n\n"
            f"{RESPONSE_SCHEMA}"
        )
        try:
            resp = self._client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=512,
                system=self.system_prompt,
                messages=[{'role': 'user', 'content': user_msg}],
            )
            raw = resp.content[0].text.strip()
            data = json.loads(raw)
            return TradeSignal(
                agent=self.agent_name,
                direction=data.get('direction', 'none'),
                confidence=int(data.get('confidence', 0)),
                entry=data.get('entry'),
                stop=data.get('stop'),
                target=data.get('target'),
                setup_type=data.get('setup_type', 'unknown'),
                reasoning=data.get('reasoning', ''),
            )
        except Exception as e:
            return TradeSignal(
                agent=self.agent_name,
                direction='none',
                confidence=0,
                entry=None, stop=None, target=None,
                setup_type='error',
                reasoning=f'Agent error: {e}',
            )
```

- [ ] **Step 6.5: Implement `src/agents/andrea_agent.py`**

```python
# src/agents/andrea_agent.py
from src.agents.base_agent import BaseAgent

ANDREA_SYSTEM = """\
You are an Auction Market Theory expert using Andrea Cimi's trading methodology for NQ Futures.

Your methodology (apply ALL rules):

## Market Structure
- Value Area (VA): 70% of session volume. Price INSIDE VA = balanced. OUTSIDE VA = seeking new value.
- POC: Maximum volume price. Strong mean-reversion magnet.
- HVN: High volume nodes = accepted prices, strong support/resistance.
- LVN: Low volume nodes = fast transit zones, price moves quickly through them.

## PBD Pattern Recognition
- P-shape: Sharp up move + balance at TOP → entry on Break-In (close below P-range then back inside) → target opposite VA
- B-shape: Sharp down move + balance at BOTTOM → entry on failed breakout up that closes back inside → target opposite VA
- D-shape: Balanced range → sell failed auction at top, buy failed auction at bottom

## Failed Auction Detection
- Price exits VA/range but candle CLOSES BACK INSIDE → failed auction confirmed → trade toward POC/opposite VA
- Required: absorption (high volume, no price progress) OR exhaustion (delta drying up at extreme)

## Delta & CVD Rules
- Initiative candle: delta_pct >= 10% → real participation → follow direction
- Absorption: high volume at price extreme but delta_pct < 5% or NEGATIVE → expect reversal
- CVD divergence: price makes new high but CVD lower → exhaustion/failed auction signal
- Minimum volume: 3000 contracts/bar. Below this = ignore.

## Entry & Stop Rules
- Entry: on candle close that confirms failed auction or initiative
- Stop: 1-2 ticks behind the absorption/iceberg level (firma dell'aggressività)
- Target 1: POC | Target 2: opposite VA edge (70% mean reversion probability)
- Target R:R must be at least 1:2, ideally 1:3 or 1:4

## No-Trade Conditions
- During news events
- NY Lunch (12:00-13:30 EST)
- Volume < 3000 contracts/bar
- No clear range/acceptance — pure price discovery spikes
- Delta 4% or below (no real imbalance)

Analyze the provided market data and give your trading decision."""

class AndreaCimiAgent(BaseAgent):
    agent_name = 'andrea'
    system_prompt = ANDREA_SYSTEM
```

- [ ] **Step 6.6: Implement `src/agents/fabio_agent.py`**

```python
# src/agents/fabio_agent.py
from src.agents.base_agent import BaseAgent

FABIO_SYSTEM = """\
You are a world-class NQ scalper using Fabio Valentini's (Fabervaale) trading methodology.

Your methodology (apply ALL rules):

## Core Philosophy: Squeeze & Trapped Participants
- A "squeeze" occurs when trapped buyers/sellers are forced to cover → creates directional explosion
- Pre-explosion: failed auction at HOD/LOD + CVD pressure building + IB breakout
- Identify "walls" = clusters of big trades (filter ≥30 contracts) acting as institutional absorption levels

## Initial Balance (IB)
- First 30 minutes of NY session (09:30-10:00 EST) defines the IB range
- IB breakout = strong directional signal (who won the battle of the open)
- Enter on SECOND test of IB breakout level, not the first probe
- Target: 1× IB range extension beyond breakout, then Value Area edges

## Orderflow Rules
- "Coherence of information": delta direction must match candle direction for valid initiative
- Absorption: large buy delta at candle HIGH with no upside follow-through = sell signal (trapped buyers)
- CVD trending against price = pressure building for reversal
- Big trades filter (≥30 contracts): these are the institutional "walls" — follow their direction

## Entry Rules
- Wait for SECOND drive (never enter on first breakout attempt)
- Enter when: (1) trapped participants visible in delta footprint + (2) IB/VA level confluence + (3) CVD confirms
- Effort vs. Result: if big volume (effort) produces no price movement (result) → fade that direction

## Stop & Target Rules
- Stop: behind the last institutional "wall" (big trade cluster) that your narrative depends on
- Move to break-even immediately after momentum follow-through
- Target 1: nearest VA edge (65-70% probability per statistical model)
- Target 2: 1:3 to 1:4 R:R, in volatile sessions can extend to 1:10+
- Trail aggressively once in profit — "stopping in profit"

## Position/Risk Grading
- A+ setup: all three confluences align (IB breakout + trapped participants + CVD confirmation)
- B setup: 2 of 3 confluences → still tradeable but smaller size
- C setup / counter-trend: avoid or skip
- Avoid: consolidation days, NY lunch, pre-open, off-hours

## No-Trade Conditions
- No clear IB breakout direction
- CVD and price moving together (no divergence to exploit)
- Volume below institutional threshold
- Late session (after 15:00 EST) without strong trend

Analyze the provided market data and give your trading decision."""

class FabioValentiniAgent(BaseAgent):
    agent_name = 'fabio'
    system_prompt = FABIO_SYSTEM
```

- [ ] **Step 6.7: Run test — verify PASS**

```bash
pytest tests/test_agents.py -v
```

- [ ] **Step 6.8: Commit**

```bash
git -C C:\Users\Mauro\Documents\nq-backtest add src/agents/ tests/test_agents.py .env.example
git -C C:\Users\Mauro\Documents\nq-backtest commit -m "feat: Andrea Cimi + Fabio Valentini Claude agents with mocked tests"
```

---

## Task 7: Consensus Layer + Trade Simulator

**Files:**
- Create: `src/consensus.py`
- Create: `src/trade_simulator.py`
- Create: `tests/test_consensus.py`
- Create: `tests/test_trade_simulator.py`

Consensus: both agents must agree on direction (unanimous) for a trade. If they disagree → no trade.
Trade Simulator: executes one trade at a time (no pyramiding), marks stop/target, tracks P&L in ticks and USD.

- [ ] **Step 7.1: Write failing tests for consensus**

```python
# tests/test_consensus.py
from src import TradeSignal, ConsensusSignal
from src.consensus import build_consensus

def _sig(agent, direction, confidence=70, entry=20005.0, stop=20003.0, target=20009.0):
    return TradeSignal(agent, direction, confidence, entry, stop, target, 'test', 'reason')

def test_unanimous_long():
    cs = build_consensus(_sig('andrea', 'long'), _sig('fabio', 'long'))
    assert cs.direction == 'long'
    assert cs.agreement == 'unanimous'
    assert cs.entry > 0

def test_disagreement_is_no_trade():
    cs = build_consensus(_sig('andrea', 'long'), _sig('fabio', 'short'))
    assert cs.direction == 'none'
    assert cs.agreement == 'no_trade'

def test_one_abstain_is_no_trade():
    cs = build_consensus(_sig('andrea', 'long'), _sig('fabio', 'none'))
    assert cs.direction == 'none'

def test_entry_is_average_of_both():
    cs = build_consensus(
        _sig('andrea', 'long', entry=20005.0),
        _sig('fabio',  'long', entry=20007.0),
    )
    assert cs.entry == 20006.0  # average

def test_stop_is_tighter_of_two_for_long():
    # For long: stop is below entry, take the HIGHER (tighter) stop
    cs = build_consensus(
        _sig('andrea', 'long', stop=20003.0),
        _sig('fabio',  'long', stop=20004.0),
    )
    assert cs.stop == 20004.0  # higher = tighter for a long
```

- [ ] **Step 7.2: Write failing tests for trade_simulator**

```python
# tests/test_trade_simulator.py
import pytest
from datetime import datetime, timezone
from src import OpenTrade, ClosedTrade, Bar
from src.trade_simulator import TradeSimulator

TS = datetime(2025, 4, 1, 14, 30, tzinfo=timezone.utc)

def _bar(price: float, high=None, low=None):
    h = high or price + 1.0
    l = low  or price - 1.0
    return Bar(TS, price, h, l, price, 5000, 2500, 2500, 0, 0.0, 0, price)

def test_target_hit_closes_long():
    sim = TradeSimulator()
    trade = OpenTrade('long', 20000.0, 19990.0, 20010.0, TS, 1, 'a reason', 'f reason')
    sim.open_trade(trade)
    # bar touches target
    result = sim.update(_bar(20005.0, high=20011.0))
    assert result is not None
    assert result.exit_reason == 'target'
    assert result.exit_price == pytest.approx(20010.0)

def test_stop_hit_closes_long():
    sim = TradeSimulator()
    trade = OpenTrade('long', 20000.0, 19990.0, 20010.0, TS, 1, 'a', 'f')
    sim.open_trade(trade)
    result = sim.update(_bar(19995.0, low=19989.0))
    assert result is not None
    assert result.exit_reason == 'stop'
    assert result.exit_price == pytest.approx(19990.0)

def test_pnl_calculation_long():
    sim = TradeSimulator()
    trade = OpenTrade('long', 20000.0, 19990.0, 20010.0, TS, 1, 'a', 'f')
    sim.open_trade(trade)
    result = sim.update(_bar(20010.0, high=20012.0))
    # 10 points / 0.25 tick = 40 ticks, 40 * $5 = $200
    assert result.pnl_ticks == pytest.approx(40.0)
    assert result.pnl_usd == pytest.approx(200.0)

def test_no_trade_open_returns_none():
    sim = TradeSimulator()
    result = sim.update(_bar(20000.0))
    assert result is None
```

- [ ] **Step 7.3: Run tests — verify FAIL**

```bash
pytest tests/test_consensus.py tests/test_trade_simulator.py -v
```

- [ ] **Step 7.4: Implement `src/consensus.py`**

```python
# src/consensus.py
from src import TradeSignal, ConsensusSignal

def build_consensus(andrea: TradeSignal, fabio: TradeSignal) -> ConsensusSignal:
    """Return ConsensusSignal. Only trade when both agree on direction."""
    if andrea.direction == fabio.direction and andrea.direction != 'none':
        direction = andrea.direction
        # Average entries, take tighter stop, take nearer target
        entry  = (andrea.entry + fabio.entry) / 2
        if direction == 'long':
            stop   = max(andrea.stop, fabio.stop)    # higher = tighter for long
            target = min(andrea.target, fabio.target) # closer = more conservative
        else:
            stop   = min(andrea.stop, fabio.stop)    # lower = tighter for short
            target = max(andrea.target, fabio.target)
        return ConsensusSignal(
            direction=direction,
            entry=entry, stop=stop, target=target,
            andrea=andrea, fabio=fabio,
            agreement='unanimous',
        )
    return ConsensusSignal(
        direction='none', entry=0.0, stop=0.0, target=0.0,
        andrea=andrea, fabio=fabio,
        agreement='no_trade',
    )
```

- [ ] **Step 7.5: Implement `src/trade_simulator.py`**

```python
# src/trade_simulator.py
from datetime import datetime
from src import Bar, OpenTrade, ClosedTrade, NQ_TICK_SIZE, NQ_TICK_VALUE

class TradeSimulator:
    def __init__(self):
        self._open: OpenTrade | None = None

    @property
    def has_open_trade(self) -> bool:
        return self._open is not None

    def open_trade(self, trade: OpenTrade) -> None:
        assert self._open is None, 'Already in a trade'
        self._open = trade

    def update(self, bar: Bar) -> ClosedTrade | None:
        """Check if bar triggers stop or target. Returns ClosedTrade or None."""
        if self._open is None:
            return None
        t = self._open
        exit_price: float | None = None
        exit_reason: str | None  = None

        if t.direction == 'long':
            if bar.low  <= t.stop:
                exit_price, exit_reason = t.stop, 'stop'
            elif bar.high >= t.target:
                exit_price, exit_reason = t.target, 'target'
        else:  # short
            if bar.high >= t.stop:
                exit_price, exit_reason = t.stop, 'stop'
            elif bar.low  <= t.target:
                exit_price, exit_reason = t.target, 'target'

        if exit_price is not None:
            return self._close(exit_price, exit_reason, bar.timestamp)
        return None

    def close_eod(self, bar: Bar) -> ClosedTrade | None:
        """Force-close at end of day if trade still open."""
        if self._open is None:
            return None
        return self._close(bar.close, 'eod', bar.timestamp)

    def _close(self, exit_price: float, reason: str, ts: datetime) -> ClosedTrade:
        t = self._open
        sign = 1 if t.direction == 'long' else -1
        pnl_ticks = sign * (exit_price - t.entry) / NQ_TICK_SIZE
        pnl_usd   = pnl_ticks * NQ_TICK_VALUE
        result = ClosedTrade(
            direction=t.direction,
            entry=t.entry, stop=t.stop, target=t.target,
            exit_price=exit_price, exit_reason=reason,
            pnl_ticks=pnl_ticks, pnl_usd=pnl_usd,
            entry_time=t.entry_time, exit_time=ts,
            andrea_reasoning=t.andrea_reasoning,
            fabio_reasoning=t.fabio_reasoning,
            setup_type='',
        )
        self._open = None
        return result
```

- [ ] **Step 7.6: Run tests — verify PASS**

```bash
pytest tests/test_consensus.py tests/test_trade_simulator.py -v
```

- [ ] **Step 7.7: Commit**

```bash
git -C C:\Users\Mauro\Documents\nq-backtest add src/consensus.py src/trade_simulator.py tests/test_consensus.py tests/test_trade_simulator.py
git -C C:\Users\Mauro\Documents\nq-backtest commit -m "feat: consensus layer + trade simulator"
```

---

## Task 8: Backtest Runner + Metrics Reporter

**Files:**
- Create: `src/backtest_runner.py`
- Create: `src/metrics_reporter.py`
- Create: `tests/test_metrics_reporter.py`
- Create: `run_backtest.py`

- [ ] **Step 8.1: Write failing tests for metrics_reporter**

```python
# tests/test_metrics_reporter.py
import pytest
from datetime import datetime, timezone
from src import ClosedTrade
from src.metrics_reporter import compute_metrics, format_report

TS = datetime(2025, 4, 1, 14, 0, tzinfo=timezone.utc)
TS2 = datetime(2025, 4, 1, 15, 0, tzinfo=timezone.utc)

def _trade(pnl_ticks: float, pnl_usd: float, direction='long') -> ClosedTrade:
    return ClosedTrade(direction, 20000.0, 19990.0, 20010.0,
                       20000.0 + (pnl_ticks * 0.25 if direction == 'long' else 0),
                       'target' if pnl_ticks > 0 else 'stop',
                       pnl_ticks, pnl_usd, TS, TS2, 'andrea reason', 'fabio reason', 'test')

def test_win_rate():
    trades = [_trade(40, 200), _trade(40, 200), _trade(-20, -100)]
    m = compute_metrics(trades)
    assert m['win_rate'] == pytest.approx(2/3)

def test_profit_factor():
    trades = [_trade(40, 200), _trade(40, 200), _trade(-20, -100)]
    m = compute_metrics(trades)
    # PF = gross_profit / gross_loss = 400 / 100 = 4.0
    assert m['profit_factor'] == pytest.approx(4.0)

def test_total_pnl():
    trades = [_trade(40, 200), _trade(-20, -100)]
    m = compute_metrics(trades)
    assert m['total_pnl_usd'] == pytest.approx(100.0)

def test_empty_trades():
    m = compute_metrics([])
    assert m['total_trades'] == 0
    assert m['win_rate'] == 0.0

def test_format_report_contains_key_fields():
    trades = [_trade(40, 200), _trade(-20, -100)]
    m = compute_metrics(trades)
    report = format_report(m, trades)
    assert 'Win Rate' in report
    assert 'Profit Factor' in report
    assert 'Total P&L' in report
```

- [ ] **Step 8.2: Run test — verify FAIL**

```bash
pytest tests/test_metrics_reporter.py -v
```

- [ ] **Step 8.3: Implement `src/metrics_reporter.py`**

```python
# src/metrics_reporter.py
import json
from pathlib import Path
from src import ClosedTrade

def compute_metrics(trades: list[ClosedTrade]) -> dict:
    if not trades:
        return {'total_trades': 0, 'win_rate': 0.0, 'profit_factor': 0.0,
                'total_pnl_usd': 0.0, 'total_pnl_ticks': 0.0,
                'wins': 0, 'losses': 0, 'avg_win_usd': 0.0, 'avg_loss_usd': 0.0,
                'max_drawdown_usd': 0.0}

    wins   = [t for t in trades if t.pnl_usd > 0]
    losses = [t for t in trades if t.pnl_usd <= 0]
    gross_profit = sum(t.pnl_usd for t in wins)
    gross_loss   = abs(sum(t.pnl_usd for t in losses))

    # Equity curve for drawdown
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        equity += t.pnl_usd
        peak = max(peak, equity)
        dd = peak - equity
        max_dd = max(max_dd, dd)

    return {
        'total_trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': len(wins) / len(trades),
        'profit_factor': gross_profit / gross_loss if gross_loss > 0 else float('inf'),
        'total_pnl_usd': sum(t.pnl_usd for t in trades),
        'total_pnl_ticks': sum(t.pnl_ticks for t in trades),
        'avg_win_usd': gross_profit / len(wins) if wins else 0.0,
        'avg_loss_usd': gross_loss / len(losses) if losses else 0.0,
        'max_drawdown_usd': max_dd,
    }

def format_report(metrics: dict, trades: list[ClosedTrade]) -> str:
    m = metrics
    lines = [
        '# NQ Multi-Agent Backtest Report',
        '',
        f'**Total Trades:** {m["total_trades"]}',
        f'**Win Rate:** {m["win_rate"]:.1%}  ({m["wins"]}W / {m["losses"]}L)',
        f'**Profit Factor:** {m["profit_factor"]:.2f}',
        f'**Total P&L:** ${m["total_pnl_usd"]:,.0f}  ({m["total_pnl_ticks"]:.0f} ticks)',
        f'**Avg Win:** ${m["avg_win_usd"]:,.0f}  |  **Avg Loss:** -${m["avg_loss_usd"]:,.0f}',
        f'**Max Drawdown:** ${m["max_drawdown_usd"]:,.0f}',
        '',
        '## Trade Log',
        '| Date | Dir | Entry | Exit | Reason | Ticks | USD | Setup |',
        '|------|-----|-------|------|--------|-------|-----|-------|',
    ]
    for t in trades:
        lines.append(
            f'| {t.entry_time.date()} | {t.direction} | {t.entry:.2f} | {t.exit_price:.2f} '
            f'| {t.exit_reason} | {t.pnl_ticks:+.0f} | ${t.pnl_usd:+,.0f} | {t.setup_type} |'
        )
    return '\n'.join(lines)

def save_reasoning_log(trades: list[ClosedTrade], output_dir: str) -> None:
    """Write per-trade reasoning to JSONL file."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / 'reasoning_log.jsonl'
    with open(path, 'w') as f:
        for t in trades:
            f.write(json.dumps({
                'date': str(t.entry_time.date()),
                'direction': t.direction,
                'entry': t.entry,
                'exit': t.exit_price,
                'pnl_usd': t.pnl_usd,
                'exit_reason': t.exit_reason,
                'andrea_reasoning': t.andrea_reasoning,
                'fabio_reasoning': t.fabio_reasoning,
                'setup_type': t.setup_type,
            }) + '\n')
```

- [ ] **Step 8.4: Implement `src/backtest_runner.py`**

```python
# src/backtest_runner.py
import os
from pathlib import Path
from dotenv import load_dotenv
from src import OpenTrade
from src.data_loader import load_day, list_data_files
from src.bar_aggregator import aggregate_to_bars
from src.volume_profile import compute_volume_profile
from src.session_context import build_session_context, is_ny_session, is_lunch
from src.candidate_detector import is_candidate
from src.signal_context import build_signal_context
from src.agents.andrea_agent import AndreaCimiAgent
from src.agents.fabio_agent import FabioValentiniAgent
from src.consensus import build_consensus
from src.trade_simulator import TradeSimulator
from src.metrics_reporter import compute_metrics, format_report, save_reasoning_log

load_dotenv()

def run_backtest(
    data_dir: str,
    output_dir: str = 'output',
    max_days: int | None = None,
    dry_run: bool = False,        # if True, skip Claude API calls (for testing infra)
) -> dict:
    """Main backtest loop. Returns metrics dict."""
    files = list_data_files(data_dir)
    if max_days:
        files = files[:max_days]

    andrea = AndreaCimiAgent()
    fabio  = FabioValentiniAgent()
    all_trades = []

    for filepath in files:
        date_str = Path(filepath).stem.split('-')[-1]  # e.g. '20250401'
        date_str = f'{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}'
        print(f'Processing {date_str}...')

        trades_raw = load_day(filepath)
        bars_1min  = aggregate_to_bars(trades_raw, freq='1min')

        # Build daily VP from all NY-session bars
        ny_bars = [b for b in bars_1min if is_ny_session(b)]
        daily_vp = compute_volume_profile(ny_bars)
        session  = build_session_context(date_str, bars_1min, daily_vp)

        sim = TradeSimulator()
        recent_window: list = []

        for i, bar in enumerate(bars_1min):
            # Update simulator with current bar
            if sim.has_open_trade:
                closed = sim.update(bar)
                if closed:
                    all_trades.append(closed)
                    print(f'  Trade closed: {closed.exit_reason} {closed.pnl_usd:+.0f} USD')

            recent_window.append(bar)
            if len(recent_window) > 20:
                recent_window.pop(0)

            # Skip if already in a trade or bar not a candidate
            if sim.has_open_trade:
                continue
            if not session.is_tradeable:
                continue
            if not is_candidate(bar, daily_vp, session.ib_high, session.ib_low):
                continue

            # Build context + call agents
            ctx = build_signal_context(bar, recent_window, daily_vp, session)

            if dry_run:
                continue  # skip API calls in dry-run mode

            andrea_sig = andrea.analyze(ctx)
            fabio_sig  = fabio.analyze(ctx)
            consensus  = build_consensus(andrea_sig, fabio_sig)

            if consensus.direction != 'none':
                trade = OpenTrade(
                    direction=consensus.direction,
                    entry=consensus.entry,
                    stop=consensus.stop,
                    target=consensus.target,
                    entry_time=bar.timestamp,
                    size=1,
                    andrea_reasoning=andrea_sig.reasoning,
                    fabio_reasoning=fabio_sig.reasoning,
                )
                sim.open_trade(trade)
                print(f'  Trade opened: {consensus.direction} @ {consensus.entry:.2f}')

        # EOD: close any open trade
        if sim.has_open_trade and bars_1min:
            eod_close = sim.close_eod(bars_1min[-1])
            if eod_close:
                all_trades.append(eod_close)

    metrics = compute_metrics(all_trades)
    report  = format_report(metrics, all_trades)

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(output_dir, 'reports', 'report.md').parent.mkdir(parents=True, exist_ok=True)
    Path(output_dir, 'reports', 'report.md').write_text(report, encoding='utf-8')
    save_reasoning_log(all_trades, str(Path(output_dir, 'reasoning_logs')))

    print(f'\nBacktest complete: {len(all_trades)} trades')
    print(report)
    return metrics
```

- [ ] **Step 8.5: Create `run_backtest.py` (CLI entry point)**

```python
# run_backtest.py
import argparse
from src.backtest_runner import run_backtest

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='NQ Multi-Agent Backtest')
    parser.add_argument('--data-dir', default=r'C:\Users\Mauro\Documents\databento-data',
                        help='Path to DataBento CSV directory')
    parser.add_argument('--output-dir', default='output', help='Output directory')
    parser.add_argument('--max-days', type=int, default=None, help='Limit to N days (for testing)')
    parser.add_argument('--dry-run', action='store_true', help='Skip Claude API calls')
    args = parser.parse_args()
    run_backtest(args.data_dir, args.output_dir, args.max_days, args.dry_run)
```

- [ ] **Step 8.6: Run tests — verify PASS**

```bash
pytest tests/test_metrics_reporter.py -v
```

- [ ] **Step 8.7: Run full dry-run integration test (1 day, no API calls)**

```bash
cd C:\Users\Mauro\Documents\nq-backtest
python run_backtest.py --max-days 1 --dry-run
```
Expected: no errors, output files created in `output/`

- [ ] **Step 8.8: Run full test suite**

```bash
pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 8.9: Commit**

```bash
git -C C:\Users\Mauro\Documents\nq-backtest add src/backtest_runner.py src/metrics_reporter.py run_backtest.py tests/test_metrics_reporter.py
git -C C:\Users\Mauro\Documents\nq-backtest commit -m "feat: backtest runner + metrics reporter — full system complete"
```

---

## Task 9: Live Run (Real Claude API, 3-Day Sample)

This task uses real API credits. Run after all tests pass.

- [ ] **Step 9.1: Set up `.env`**

```bash
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 9.2: Run 3-day sample backtest**

```bash
cd C:\Users\Mauro\Documents\nq-backtest
python run_backtest.py --max-days 3
```
Expected: trades logged with reasoning, report written to `output/reports/report.md`

- [ ] **Step 9.3: Review output**

Check `output/reasoning_logs/reasoning_log.jsonl` for sample trade reasoning.
Check `output/reports/report.md` for metrics.

Evaluate:
- Are agent signals coherent with the methodology?
- Do stop/target levels look reasonable?
- Is the candidate detector filtering correctly (not too many, not too few)?

- [ ] **Step 9.4: Tune candidate detector if needed**

If too many candidates (>100/day): tighten `VA_PROXIMITY_TICKS` from 4 to 2
If too few (<5/day): loosen to 6 ticks or reduce `MIN_VOLUME_PER_BAR`

- [ ] **Step 9.5: Run full 106-day backtest**

```bash
python run_backtest.py
```

This will take time (~10-30 min depending on API latency and candidate frequency).

---

## Estimated Cost

- Claude Haiku: ~$0.25/MTok input, ~$1.25/MTok output
- Avg context per call: ~2KB ≈ ~500 tokens input, ~150 tokens output
- Two agents per candidate: 1000 input + 300 output per candidate window
- Assume 30 candidates/day × 106 days = 3180 calls
- Cost estimate: ~$1-3 total for full 106-day run

---

## Quick Reference — Key Thresholds

| Parameter | Value | Source |
|-----------|-------|--------|
| VA percentage | 70% | Both traders |
| Big trades filter | ≥30 contracts | Fabio's "filter by 30" |
| Min volume per bar | 3,000 contracts | Andrea: "negligible" |
| Delta % initiative | ≥10% | Andrea: "at least 10%" |
| IB window | 30 min | Fabio: "first 30 minutes" |
| VA proximity (candidate) | 4 ticks = 1.0 pt | Design decision |
| NQ tick size | 0.25 pts | CME spec |
| NQ tick value | $5.00 | CME spec |
| Target R:R | 1:3 minimum | Both traders |

