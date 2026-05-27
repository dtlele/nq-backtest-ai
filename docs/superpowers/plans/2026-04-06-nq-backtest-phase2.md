# NQ Multi-Agent Backtest Phase 2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python backtesting engine that replays 106 days of DataBento NQ tick data through two AI agents (Fabio primary, Andrea confirmation), each consulting NotebookLM + their knowledge.json per candidate bar, producing per-trade reasoning logs and a final performance report.

**Architecture:** Raw MBP-1 CSVs → 1-min bars → Volume Profile + IB (15min) → candidate detector (big trade cluster near LVN/POC) → Fabio agent queries NLM → Andrea agent confirms or vetoes → trade simulator marks-to-market → reasoning_log.jsonl + equity curve.

**Tech Stack:** Python 3.11+, pandas, numpy, anthropic SDK, python-dotenv, matplotlib, pytest, subprocess (notebooklm CLI)

---

## Critical Data Facts

- **CSV timestamps**: ISO 8601 strings (`2025-04-30T00:00:00.005137585Z`) — parse with `pd.to_datetime()`
- **CSV prices**: already floats in NQ points (`19562.500000000`) — NO scaling needed
- **Side**: `A` = ask aggressor (buyer), `B` = bid aggressor (seller)
- **NQ tick**: 0.25 points = $5 USD
- **IVB (Initial Volume Breakout)** = Fabio's term for Initial Balance = first **15 min** of NY session
- **NY session**: 09:30 ET open; backtest window 09:25–11:30 ET
- **Fabio active from**: 09:40 ET (avoids first 10 min volatility)
- **Big trade threshold**: size ≥ 30 contracts
- **NotebookLM notebooks**: Fabio = `4c868e52`, Andrea = `5204f969`
- **Fabio min confidence**: 65 to take trade; Andrea veto if < 40

---

## File Map

```
nq-backtest/
├── src/
│   ├── __init__.py                  ← all dataclasses + constants
│   ├── data_loader.py               ← parse DataBento CSV → list[Trade]
│   ├── bar_aggregator.py            ← 1-min OHLCV + delta + big_trades
│   ├── volume_profile.py            ← POC, VA (70%), HVN/LVN
│   ├── session_context.py           ← IB 15min, NY window, day_type
│   ├── candidate_detector.py        ← wall + VP proximity → CandidateBar
│   ├── signal_context.py            ← fill NLM question templates
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── nlm_client.py            ← subprocess wrapper for notebooklm CLI
│   │   ├── fabio_agent.py           ← primary: knowledge + NLM → FabioSignal
│   │   └── andrea_agent.py          ← confirmation: knowledge + NLM → AndreaSignal
│   ├── consensus.py                 ← Fabio primary + Andrea veto logic
│   ├── trade_simulator.py           ← mark-to-market on subsequent bars
│   ├── agent_memory.py              ← session_state, pattern_memory, reasoning_log
│   └── metrics_reporter.py          ← win rate, profit factor, equity curve
├── tests/
│   ├── test_data_loader.py
│   ├── test_bar_aggregator.py
│   ├── test_volume_profile.py
│   ├── test_session_context.py
│   ├── test_candidate_detector.py
│   ├── test_signal_context.py
│   ├── test_nlm_client.py
│   ├── test_fabio_agent.py
│   ├── test_andrea_agent.py
│   ├── test_consensus.py
│   ├── test_trade_simulator.py
│   └── test_metrics_reporter.py
├── strategies/
│   └── fabio_andrea_hybrid.json     ← checklist with NLM question templates
├── agent_memory/
│   ├── session_state.json           ← daily reset (IB, VP, open trade)
│   ├── pattern_memory.json          ← cross-session accumulation
│   └── reasoning_log.jsonl          ← append-only audit trail
├── output/
│   ├── reasoning_logs/              ← per-day JSONL (one entry per candidate)
│   └── reports/                     ← metrics_YYYY-MM-DD.md + equity_curve.png
├── knowledge/
│   ├── fabio_knowledge.json         ← already built
│   └── andrea_knowledge.json        ← already built
├── .env.example
├── requirements.txt
└── run_backtest.py                  ← CLI: python run_backtest.py --days 5 --dry-run
```

---

## Core Data Structures (`src/__init__.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

# ── NQ constants ──────────────────────────────────────────────────────────────
NQ_TICK_SIZE            = 0.25
NQ_TICK_VALUE           = 5.0      # USD per tick
NQ_BIG_TRADE_THRESHOLD  = 30       # contracts (Fabio's filter)

# ── Volume Profile ────────────────────────────────────────────────────────────
VA_PERCENTAGE           = 0.70
TICK_BUCKET_SIZE        = 0.25

# ── Session / Timing (ET = America/New_York) ──────────────────────────────────
NY_WINDOW_START_H       = 9
NY_WINDOW_START_M       = 25
NY_WINDOW_END_H         = 11
NY_WINDOW_END_M         = 30
FABIO_ACTIVE_H          = 9
FABIO_ACTIVE_M          = 40
IB_DURATION_MIN         = 15       # Fabio's IVB = first 15 min

# ── Candidate detection ───────────────────────────────────────────────────────
MIN_VOLUME_PER_BAR      = 3000
VA_PROXIMITY_TICKS      = 4        # within 4 ticks of a VP level = "near"
BIG_TRADE_LOOKBACK_BARS = 3        # check current + prior 2 bars for wall

# ── Agent thresholds ──────────────────────────────────────────────────────────
FABIO_MIN_CONFIDENCE    = 65
ANDREA_VETO_THRESHOLD   = 40

# ── NotebookLM IDs ────────────────────────────────────────────────────────────
FABIO_NOTEBOOK_ID       = "4c868e52"
ANDREA_NOTEBOOK_ID      = "5204f969"


@dataclass
class Trade:
    ts_event: datetime   # UTC, parsed from ISO 8601
    side: str            # 'A' = buyer, 'B' = seller
    price: float         # NQ points (already scaled in CSV)
    size: int

@dataclass
class Bar:
    timestamp: datetime  # UTC, bar open time
    open: float
    high: float
    low: float
    close: float
    volume: int
    buy_volume: int      # sum size where side='A'
    sell_volume: int     # sum size where side='B'
    delta: int           # buy_volume - sell_volume
    delta_pct: float     # abs(delta)/volume*100
    cvd: int             # cumulative session delta (analytics only)
    vwap: float
    big_trades: list = field(default_factory=list)  # list[Trade] size >= threshold

@dataclass
class VolumeProfile:
    poc: float
    va_high: float
    va_low: float
    hvn_levels: list = field(default_factory=list)  # up to 5
    lvn_levels: list = field(default_factory=list)  # up to 5

@dataclass
class SessionContext:
    date: str
    ib_high: float
    ib_low: float
    ib_range: float
    ib_complete: bool
    vp: Optional[VolumeProfile]
    day_type: str  # 'trend_up'|'trend_down'|'balance'|'unknown'

@dataclass
class CandidateBar:
    bar: Bar
    session_ctx: SessionContext
    wall_level: float          # price of the big-trade cluster
    wall_side: str             # 'bid'|'ask'
    wall_trade_count: int      # number of big trades at this level
    wall_max_size: int         # largest single big trade
    proximity_to: str          # 'lvn'|'poc'|'va_high'|'va_low'|'ib_high'|'ib_low'
    proximity_level: float     # the exact VP level price
    bars_in_session: int       # how many bars so far today
    is_second_test: bool       # True = price already tested this level today

@dataclass
class FabioSignal:
    direction: str             # 'long'|'short'|'none'
    confidence: int            # 0-100
    entry: Optional[float]
    stop: Optional[float]
    target: Optional[float]
    setup_type: str            # 'squeeze'|'ivb_breakout'|'none'
    reasoning: str             # Claude's reasoning text
    nlm_answer: str            # raw NLM response

@dataclass
class AndreaSignal:
    confirmation: bool         # True = confirms Fabio direction
    confidence: int            # 0-100; below ANDREA_VETO_THRESHOLD = veto
    setup_type: str            # 'ibob'|'failed_auction'|'none'
    reasoning: str
    nlm_answer: str

@dataclass
class ConsensusSignal:
    direction: str
    entry: float
    stop: float
    target: float
    r_ratio: float
    final_confidence: int
    fabio: FabioSignal
    andrea: AndreaSignal
    decision: str              # 'trade'|'no_trade'
    no_trade_reason: str       # '' if decision=='trade'

@dataclass
class OpenTrade:
    direction: str
    entry: float
    stop: float
    target: float
    entry_bar: Bar
    consensus: ConsensusSignal

@dataclass
class ClosedTrade:
    direction: str
    entry: float
    stop: float
    target: float
    exit_price: float
    exit_reason: str           # 'target'|'stop'|'eod'
    pnl_ticks: float
    pnl_usd: float
    entry_time: datetime
    exit_time: datetime
    fabio_reasoning: str
    andrea_reasoning: str
    setup_type: str
    final_confidence: int
    r_ratio: float
```

---

## Task 1: Project Setup + Data Loader

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `src/__init__.py`
- Create: `src/data_loader.py`
- Create: `tests/__init__.py`
- Create: `tests/test_data_loader.py`

- [ ] **Step 1.1: Create `requirements.txt`**

```
pandas>=2.0
numpy>=1.25
anthropic>=0.25
python-dotenv>=1.0
matplotlib>=3.7
pytest>=7.4
pytest-mock>=3.11
pytz>=2024.1
```

Run: `pip install -r requirements.txt`

- [ ] **Step 1.2: Create `.env.example`**

```
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 1.3: Create `src/__init__.py`**

Copy the Core Data Structures block above verbatim.

- [ ] **Step 1.4: Create `tests/__init__.py`** (empty file)

- [ ] **Step 1.5: Write failing test `tests/test_data_loader.py`**

```python
import pytest, textwrap, tempfile, os
from src.data_loader import load_day, list_data_files
from pathlib import Path

SAMPLE_CSV = textwrap.dedent("""\
    ts_recv,ts_event,rtype,publisher_id,instrument_id,action,side,depth,price,size,flags,ts_in_delta,sequence,symbol
    2025-04-30T13:30:05.000000000Z,2025-04-30T13:30:05.000000000Z,0,1,1,T,A,0,20000.000000000,5,0,1000,1,NQM5
    2025-04-30T13:30:10.000000000Z,2025-04-30T13:30:10.000000000Z,0,1,1,T,B,0,19999.750000000,10,0,1000,2,NQM5
    2025-04-30T13:30:15.000000000Z,2025-04-30T13:30:15.000000000Z,0,1,1,T,A,0,20000.000000000,35,0,1000,3,NQM5
    2025-04-30T13:30:20.000000000Z,2025-04-30T13:30:20.000000000Z,0,1,1,A,A,0,20000.000000000,5,0,1000,4,NQM5
""")

def _write_csv(content: str) -> str:
    f = tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False)
    f.write(content); f.close()
    return f.name

def test_load_day_parses_trades():
    path = _write_csv(SAMPLE_CSV)
    trades = load_day(path)
    os.unlink(path)
    assert len(trades) == 3  # action='A' row skipped
    assert trades[0].side == 'A'
    assert trades[0].price == pytest.approx(20000.0)
    assert trades[0].size == 5
    assert trades[1].side == 'B'
    assert trades[1].price == pytest.approx(19999.75)
    assert trades[2].size == 35

def test_load_day_skips_non_trade_actions():
    path = _write_csv(SAMPLE_CSV)
    trades = load_day(path)
    os.unlink(path)
    assert all(t.size != 5 or t.price == pytest.approx(20000.0) for t in trades)
    # Only 3 rows with action='T'
    assert len(trades) == 3

def test_load_day_timestamp_is_utc_datetime():
    path = _write_csv(SAMPLE_CSV)
    trades = load_day(path)
    os.unlink(path)
    from datetime import timezone
    assert trades[0].ts_event.tzinfo is not None
    assert trades[0].ts_event.hour == 13  # 13:30:05 UTC

def test_list_data_files():
    with tempfile.TemporaryDirectory() as d:
        Path(d, 'glbx-mdp3-20250401.trades.csv').touch()
        Path(d, 'glbx-mdp3-20250402.trades.csv').touch()
        Path(d, 'other.txt').touch()
        files = list_data_files(d)
        assert len(files) == 2
        assert all(f.endswith('.trades.csv') for f in files)
```

- [ ] **Step 1.6: Run — verify FAIL**

```bash
cd C:\Users\Mauro\Documents\nq-backtest
pytest tests/test_data_loader.py -v
```
Expected: `ModuleNotFoundError: No module named 'src.data_loader'`

- [ ] **Step 1.7: Implement `src/data_loader.py`**

```python
import glob, os
import pandas as pd
from datetime import timezone
from src import Trade

def load_day(filepath: str) -> list:
    """Parse one DataBento *.trades.csv. Returns action='T' rows only."""
    df = pd.read_csv(filepath,
                     usecols=['ts_event', 'action', 'side', 'price', 'size'])
    df = df[df['action'] == 'T'].copy()
    df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
    return [
        Trade(
            ts_event=row.ts_event.to_pydatetime().replace(tzinfo=timezone.utc),
            side=row.side,
            price=float(row.price),
            size=int(row.size),
        )
        for row in df.itertuples(index=False)
    ]

def list_data_files(directory: str) -> list:
    """Return sorted list of *.trades.csv paths."""
    return sorted(glob.glob(os.path.join(directory, '*.trades.csv')))
```

- [ ] **Step 1.8: Run — verify PASS**

```bash
pytest tests/test_data_loader.py -v
```
Expected: 4 tests PASS

- [ ] **Step 1.9: Commit**

```bash
cd C:\Users\Mauro\Documents\nq-backtest && git init && git add src/ tests/ requirements.txt .env.example && git commit -m "feat: project setup, data structures, DataBento loader"
```

---

## Task 2: Bar Aggregator

**Files:**
- Create: `src/bar_aggregator.py`
- Create: `tests/test_bar_aggregator.py`

Aggregates trades into 1-min OHLCV bars with delta, CVD, VWAP, and big_trades list.

- [ ] **Step 2.1: Write failing test `tests/test_bar_aggregator.py`**

```python
import pytest
from datetime import datetime, timezone
from src import Trade, NQ_BIG_TRADE_THRESHOLD
from src.bar_aggregator import aggregate_to_bars

def _t(hms: str, side: str, price: float, size: int) -> Trade:
    dt = datetime.strptime(f"2025-04-30 {hms}", "%Y-%m-%d %H:%M:%S")
    return Trade(ts_event=dt.replace(tzinfo=timezone.utc), side=side,
                 price=price, size=size)

def test_single_bar_ohlcv():
    trades = [
        _t("13:30:05", 'A', 20000.00, 10),
        _t("13:30:30", 'B', 19999.75, 20),
        _t("13:30:55", 'A', 20000.25, 5),
    ]
    bars = aggregate_to_bars(trades, freq='1min')
    assert len(bars) == 1
    b = bars[0]
    assert b.open  == pytest.approx(20000.00)
    assert b.high  == pytest.approx(20000.25)
    assert b.low   == pytest.approx(19999.75)
    assert b.close == pytest.approx(20000.25)
    assert b.volume == 35
    assert b.buy_volume == 15
    assert b.sell_volume == 20
    assert b.delta == -5
    assert b.delta_pct == pytest.approx(abs(-5) / 35 * 100)

def test_cvd_accumulates():
    trades = [
        _t("13:30:05", 'A', 20000.0, 30),  # bar1: delta +30
        _t("13:31:05", 'B', 20000.0, 10),  # bar2: delta -10
    ]
    bars = aggregate_to_bars(trades, freq='1min')
    assert len(bars) == 2
    assert bars[0].cvd == 30
    assert bars[1].cvd == 20

def test_big_trades_captured():
    trades = [
        _t("13:30:05", 'A', 20000.0, 29),   # not big
        _t("13:30:10", 'B', 20000.0, 30),   # threshold
        _t("13:30:15", 'A', 20000.0, 100),  # big
    ]
    bars = aggregate_to_bars(trades, freq='1min')
    big = bars[0].big_trades
    assert len(big) == 2
    assert all(t.size >= NQ_BIG_TRADE_THRESHOLD for t in big)

def test_vwap():
    trades = [
        _t("13:30:05", 'A', 100.0, 10),
        _t("13:30:10", 'A', 200.0, 10),
    ]
    bars = aggregate_to_bars(trades, freq='1min')
    assert bars[0].vwap == pytest.approx(150.0)

def test_empty_returns_empty():
    assert aggregate_to_bars([], freq='1min') == []
```

- [ ] **Step 2.2: Run — verify FAIL**

```bash
pytest tests/test_bar_aggregator.py -v
```

- [ ] **Step 2.3: Implement `src/bar_aggregator.py`**

```python
import pandas as pd
import numpy as np
from src import Trade, Bar, NQ_BIG_TRADE_THRESHOLD

def aggregate_to_bars(trades: list, freq: str = '1min') -> list:
    if not trades:
        return []
    records = [{
        'ts':       pd.Timestamp(t.ts_event, tz='UTC') if t.ts_event.tzinfo else pd.Timestamp(t.ts_event).tz_localize('UTC'),
        'side':     t.side,
        'price':    t.price,
        'size':     t.size,
    } for t in trades]

    df = pd.DataFrame(records).set_index('ts').sort_index()
    # Ensure tz-aware index
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')

    df['buy_vol']  = np.where(df['side'] == 'A', df['size'], 0)
    df['sell_vol'] = np.where(df['side'] == 'B', df['size'], 0)
    df['dollar']   = df['price'] * df['size']
    df['is_big']   = df['size'] >= NQ_BIG_TRADE_THRESHOLD

    g      = df.resample(freq)
    ohlcv  = g['price'].ohlc()
    vol    = g['size'].sum().rename('volume')
    buy    = g['buy_vol'].sum().rename('buy_volume')
    sell   = g['sell_vol'].sum().rename('sell_volume')
    dollar = g['dollar'].sum().rename('dollar')

    agg = pd.concat([ohlcv, vol, buy, sell, dollar], axis=1).dropna(subset=['open'])
    agg['delta']     = agg['buy_volume'] - agg['sell_volume']
    agg['delta_pct'] = np.where(agg['volume'] > 0,
                                agg['delta'].abs() / agg['volume'] * 100, 0.0)
    agg['vwap']      = np.where(agg['volume'] > 0,
                                agg['dollar'] / agg['volume'], agg['close'])
    agg['cvd']       = agg['delta'].cumsum()

    # Map big trades to their bar floor
    big_map: dict = {}
    for trade, rec in zip(trades, records):
        if trade.size >= NQ_BIG_TRADE_THRESHOLD:
            floor = rec['ts'].floor(freq)
            big_map.setdefault(floor, []).append(trade)

    bars = []
    for ts, row in agg.iterrows():
        bars.append(Bar(
            timestamp   = ts.to_pydatetime(),
            open        = float(row['open']),
            high        = float(row['high']),
            low         = float(row['low']),
            close       = float(row['close']),
            volume      = int(row['volume']),
            buy_volume  = int(row['buy_volume']),
            sell_volume = int(row['sell_volume']),
            delta       = int(row['delta']),
            delta_pct   = float(row['delta_pct']),
            cvd         = int(row['cvd']),
            vwap        = float(row['vwap']),
            big_trades  = big_map.get(ts, []),
        ))
    return bars
```

- [ ] **Step 2.4: Run — verify PASS**

```bash
pytest tests/test_bar_aggregator.py -v
```

- [ ] **Step 2.5: Commit**

```bash
git add src/bar_aggregator.py tests/test_bar_aggregator.py && git commit -m "feat: bar aggregator — OHLCV, delta, CVD, big trades"
```

---

## Task 3: Volume Profile

**Files:**
- Create: `src/volume_profile.py`
- Create: `tests/test_volume_profile.py`

- [ ] **Step 3.1: Write failing test**

```python
import pytest
from datetime import datetime, timezone
from src import Bar, VA_PERCENTAGE
from src.volume_profile import compute_volume_profile

def _bar(price: float, vol: int) -> Bar:
    return Bar(datetime(2025,4,30,14,0,tzinfo=timezone.utc),
               price, price+0.25, price-0.25, price,
               vol, vol//2, vol//2, 0, 0.0, 0, price)

def test_poc_highest_volume():
    bars = [_bar(100.00, 100), _bar(100.25, 200), _bar(100.50, 50)]
    vp = compute_volume_profile(bars)
    assert vp.poc == pytest.approx(100.25)

def test_va_contains_70pct():
    bars = [_bar(99.75, 10), _bar(100.00, 700), _bar(100.25, 10), _bar(100.50, 10)]
    vp = compute_volume_profile(bars)
    assert vp.va_low <= 100.00 <= vp.va_high

def test_empty_returns_none():
    assert compute_volume_profile([]) is None

def test_hvn_lvn_returned():
    bars = [_bar(99.75,10), _bar(100.00,500), _bar(100.25,10), _bar(100.50,400)]
    vp = compute_volume_profile(bars)
    assert len(vp.hvn_levels) >= 1
    assert len(vp.lvn_levels) >= 1
```

- [ ] **Step 3.2: Run — verify FAIL**

- [ ] **Step 3.3: Implement `src/volume_profile.py`**

```python
import numpy as np
from src import Bar, VolumeProfile, VA_PERCENTAGE, TICK_BUCKET_SIZE

def compute_volume_profile(bars: list) -> 'VolumeProfile | None':
    if not bars:
        return None

    price_vol: dict = {}
    for bar in bars:
        # Distribute bar volume proportionally across price range
        p_low  = round(bar.low  / TICK_BUCKET_SIZE) * TICK_BUCKET_SIZE
        p_high = round(bar.high / TICK_BUCKET_SIZE) * TICK_BUCKET_SIZE
        ticks  = max(1, round((p_high - p_low) / TICK_BUCKET_SIZE) + 1)
        vol_per_tick = bar.volume / ticks
        price = p_low
        while price <= p_high + 1e-9:
            key = round(price / TICK_BUCKET_SIZE) * TICK_BUCKET_SIZE
            price_vol[key] = price_vol.get(key, 0) + vol_per_tick
            price += TICK_BUCKET_SIZE

    if not price_vol:
        return None

    sorted_prices = sorted(price_vol.keys())
    volumes       = [price_vol[p] for p in sorted_prices]
    total_vol     = sum(volumes)
    poc_idx       = int(np.argmax(volumes))
    poc           = sorted_prices[poc_idx]

    # Value Area: expand from POC until 70% captured
    va_vol = volumes[poc_idx]
    lo_idx = hi_idx = poc_idx
    while va_vol / total_vol < VA_PERCENTAGE:
        add_lo = volumes[lo_idx - 1] if lo_idx > 0 else 0
        add_hi = volumes[hi_idx + 1] if hi_idx < len(volumes) - 1 else 0
        if add_hi >= add_lo and hi_idx < len(volumes) - 1:
            hi_idx += 1; va_vol += add_hi
        elif lo_idx > 0:
            lo_idx -= 1; va_vol += add_lo
        else:
            break

    va_high = sorted_prices[hi_idx]
    va_low  = sorted_prices[lo_idx]

    # HVN = local maxima, LVN = local minima (simple peak detection)
    hvn, lvn = [], []
    for i in range(1, len(volumes) - 1):
        if volumes[i] > volumes[i-1] and volumes[i] > volumes[i+1]:
            hvn.append(sorted_prices[i])
        elif volumes[i] < volumes[i-1] and volumes[i] < volumes[i+1]:
            lvn.append(sorted_prices[i])

    # Sort HVN by volume desc, LVN by volume asc (lowest volume = strongest LVN)
    hvn = sorted(hvn, key=lambda p: -price_vol[p])[:5]
    lvn = sorted(lvn, key=lambda p: price_vol[p])[:5]

    return VolumeProfile(poc=poc, va_high=va_high, va_low=va_low,
                         hvn_levels=hvn, lvn_levels=lvn)
```

- [ ] **Step 3.4: Run — verify PASS**

```bash
pytest tests/test_volume_profile.py -v
```

- [ ] **Step 3.5: Commit**

```bash
git add src/volume_profile.py tests/test_volume_profile.py && git commit -m "feat: volume profile — POC, VA 70%, HVN/LVN"
```

---

## Task 4: Session Context

**Files:**
- Create: `src/session_context.py`
- Create: `tests/test_session_context.py`

Computes IB (first 15 min of NY open = 09:30–09:45 ET), filters bars to NY window, classifies day type.

- [ ] **Step 4.1: Write failing test**

```python
import pytest
from datetime import datetime, timezone
import pytz
from src import Bar, IB_DURATION_MIN
from src.session_context import (
    filter_ny_window, compute_ib, classify_day_type,
    build_session_context, is_fabio_active
)

ET = pytz.timezone('America/New_York')

def _bar_et(h: int, m: int, price: float, vol: int = 5000) -> Bar:
    """Create a bar at given ET time."""
    dt_et = ET.localize(datetime(2025, 4, 30, h, m, 0))
    dt_utc = dt_et.astimezone(timezone.utc)
    return Bar(dt_utc, price, price+1, price-1, price,
               vol, vol//2, vol//2, 0, 0.0, 0, price)

def test_filter_ny_window_keeps_09_25_to_11_30():
    bars = [
        _bar_et(9, 20, 20000.0),   # before → excluded
        _bar_et(9, 25, 20000.0),   # start  → included
        _bar_et(11, 29, 20000.0),  # inside → included
        _bar_et(11, 30, 20000.0),  # end    → excluded (strict <)
        _bar_et(12, 0,  20000.0),  # after  → excluded
    ]
    result = filter_ny_window(bars)
    assert len(result) == 2

def test_compute_ib_uses_first_15min():
    # 09:30 to 09:44 = IB window
    bars = [
        _bar_et(9, 30, 20000.0),
        _bar_et(9, 35, 20050.0),
        _bar_et(9, 40, 19980.0),
        _bar_et(9, 44, 20020.0),
        _bar_et(9, 45, 20100.0),  # outside IB
    ]
    ib_high, ib_low = compute_ib(bars)
    assert ib_high == pytest.approx(20050.0)
    assert ib_low  == pytest.approx(19980.0)

def test_is_fabio_active_after_09_40():
    bar_before = _bar_et(9, 39, 20000.0)
    bar_after  = _bar_et(9, 40, 20000.0)
    assert is_fabio_active(bar_before) is False
    assert is_fabio_active(bar_after)  is True

def test_classify_day_type_trend_up():
    bars = [_bar_et(9, 30 + i, 20000.0 + i * 10, 5000) for i in range(10)]
    assert classify_day_type(bars) == 'trend_up'
```

- [ ] **Step 4.2: Run — verify FAIL**

- [ ] **Step 4.3: Implement `src/session_context.py`**

```python
import pytz
from datetime import datetime, timezone, timedelta
from src import (Bar, SessionContext, VolumeProfile,
                 NY_WINDOW_START_H, NY_WINDOW_START_M,
                 NY_WINDOW_END_H, NY_WINDOW_END_M,
                 FABIO_ACTIVE_H, FABIO_ACTIVE_M, IB_DURATION_MIN)

ET = pytz.timezone('America/New_York')

def _to_et(bar: Bar) -> datetime:
    return bar.timestamp.astimezone(ET)

def filter_ny_window(bars: list) -> list:
    """Keep bars strictly within [09:25, 11:30) ET."""
    result = []
    for b in bars:
        t = _to_et(b)
        start = t.replace(hour=NY_WINDOW_START_H, minute=NY_WINDOW_START_M,
                          second=0, microsecond=0)
        end   = t.replace(hour=NY_WINDOW_END_H,   minute=NY_WINDOW_END_M,
                          second=0, microsecond=0)
        if start <= t < end:
            result.append(b)
    return result

def compute_ib(bars: list) -> tuple:
    """Return (ib_high, ib_low) from bars in NY open to NY_open+IB_DURATION_MIN."""
    ib_bars = []
    for b in bars:
        t = _to_et(b)
        ny_open = t.replace(hour=9, minute=30, second=0, microsecond=0)
        ib_end  = ny_open + timedelta(minutes=IB_DURATION_MIN)
        if ny_open <= t < ib_end:
            ib_bars.append(b)
    if not ib_bars:
        return (0.0, 0.0)
    return (max(b.high for b in ib_bars), min(b.low for b in ib_bars))

def is_fabio_active(bar: Bar) -> bool:
    t = _to_et(bar)
    active_time = t.replace(hour=FABIO_ACTIVE_H, minute=FABIO_ACTIVE_M,
                             second=0, microsecond=0)
    return t >= active_time

def classify_day_type(bars: list) -> str:
    """Simple classification from close slope over session bars."""
    if len(bars) < 3:
        return 'unknown'
    closes = [b.close for b in bars]
    slope = closes[-1] - closes[0]
    spread = max(closes) - min(closes)
    if spread == 0:
        return 'balance'
    ratio = abs(slope) / spread
    if ratio > 0.6 and slope > 0:
        return 'trend_up'
    if ratio > 0.6 and slope < 0:
        return 'trend_down'
    return 'balance'

def build_session_context(date_str: str, bars: list,
                           vp: 'VolumeProfile | None') -> SessionContext:
    ib_high, ib_low = compute_ib(bars)
    return SessionContext(
        date=date_str,
        ib_high=ib_high,
        ib_low=ib_low,
        ib_range=round(ib_high - ib_low, 2),
        ib_complete=ib_high > 0,
        vp=vp,
        day_type=classify_day_type(bars),
    )
```

- [ ] **Step 4.4: Run — verify PASS**

```bash
pytest tests/test_session_context.py -v
```

- [ ] **Step 4.5: Commit**

```bash
git add src/session_context.py tests/test_session_context.py && git commit -m "feat: session context — IB 15min, NY window, day type"
```

---

## Task 5: Candidate Detector

**Files:**
- Create: `src/candidate_detector.py`
- Create: `tests/test_candidate_detector.py`

A bar is a candidate when ALL of:
1. Fabio active (bar time ≥ 09:40 ET)
2. Volume ≥ MIN_VOLUME_PER_BAR (3000)
3. ≥1 big trade (size ≥ 30) in current bar or prior BIG_TRADE_LOOKBACK_BARS bars
4. Price (close) within VA_PROXIMITY_TICKS of any VP level (LVN, POC, va_high, va_low, ib_high, ib_low)

- [ ] **Step 5.1: Write failing test**

```python
import pytest
from datetime import datetime, timezone
import pytz
from src import Bar, VolumeProfile, SessionContext, NQ_BIG_TRADE_THRESHOLD, Trade
from src.candidate_detector import detect_candidates

ET = pytz.timezone('America/New_York')

def _bar_et(h, m, close, vol=5000, big_size=0) -> Bar:
    dt = ET.localize(datetime(2025,4,30,h,m)).astimezone(timezone.utc)
    big = [Trade(dt, 'A', close, big_size)] if big_size >= NQ_BIG_TRADE_THRESHOLD else []
    return Bar(dt, close-1, close+1, close-1, close,
               vol, vol//2, vol//2, 0, 0.0, 0, close, big)

def _ctx(poc=20000.0, va_high=20050.0, va_low=19950.0,
         ib_high=20020.0, ib_low=19980.0) -> SessionContext:
    vp = VolumeProfile(poc=poc, va_high=va_high, va_low=va_low,
                       hvn_levels=[20030.0], lvn_levels=[20000.0])
    return SessionContext('2025-04-30', ib_high, ib_low,
                          ib_high-ib_low, True, vp, 'balance')

def test_detects_candidate_at_lvn():
    ctx = _ctx()
    # Bar at POC (20000) with big trade, after 09:40
    bars = [_bar_et(9, 41, 20000.0, vol=4000, big_size=45)]
    candidates = detect_candidates(bars, ctx)
    assert len(candidates) == 1
    assert candidates[0].proximity_to in ('lvn', 'poc')

def test_no_candidate_before_fabio_active():
    ctx = _ctx()
    bars = [_bar_et(9, 35, 20000.0, vol=4000, big_size=45)]
    assert detect_candidates(bars, ctx) == []

def test_no_candidate_low_volume():
    ctx = _ctx()
    bars = [_bar_et(9, 41, 20000.0, vol=100, big_size=45)]
    assert detect_candidates(bars, ctx) == []

def test_no_candidate_no_big_trade():
    ctx = _ctx()
    bars = [_bar_et(9, 41, 20000.0, vol=4000, big_size=0)]
    assert detect_candidates(bars, ctx) == []

def test_no_candidate_far_from_levels():
    ctx = _ctx(poc=20000.0)
    bars = [_bar_et(9, 41, 20200.0, vol=4000, big_size=45)]  # 200 pts away
    assert detect_candidates(bars, ctx) == []
```

- [ ] **Step 5.2: Run — verify FAIL**

- [ ] **Step 5.3: Implement `src/candidate_detector.py`**

```python
from src import (Bar, SessionContext, CandidateBar, Trade,
                 NQ_BIG_TRADE_THRESHOLD, MIN_VOLUME_PER_BAR,
                 VA_PROXIMITY_TICKS, BIG_TRADE_LOOKBACK_BARS, NQ_TICK_SIZE)
from src.session_context import is_fabio_active

def _near(price: float, level: float, ticks: int) -> bool:
    return abs(price - level) <= ticks * NQ_TICK_SIZE

def _get_vp_levels(ctx: SessionContext) -> list:
    """Return (level_price, level_name) pairs from VP + IB."""
    levels = [
        (ctx.ib_high, 'ib_high'),
        (ctx.ib_low,  'ib_low'),
    ]
    if ctx.vp:
        levels += [
            (ctx.vp.poc,      'poc'),
            (ctx.vp.va_high,  'va_high'),
            (ctx.vp.va_low,   'va_low'),
        ]
        for p in ctx.vp.lvn_levels:
            levels.append((p, 'lvn'))
        for p in ctx.vp.hvn_levels:
            levels.append((p, 'hvn'))
    return levels

def detect_candidates(bars: list, ctx: SessionContext) -> list:
    candidates = []
    for i, bar in enumerate(bars):
        # 1. Fabio active
        if not is_fabio_active(bar):
            continue
        # 2. Volume filter
        if bar.volume < MIN_VOLUME_PER_BAR:
            continue
        # 3. Big trade in lookback window
        window = bars[max(0, i - BIG_TRADE_LOOKBACK_BARS + 1): i + 1]
        all_big = [t for b in window for t in b.big_trades]
        if not all_big:
            continue
        # 4. Price near VP level
        price = bar.close
        levels = _get_vp_levels(ctx)
        nearby = [(lvl, name) for lvl, name in levels
                  if _near(price, lvl, VA_PROXIMITY_TICKS)]
        if not nearby:
            continue
        # Use closest level
        nearby.sort(key=lambda x: abs(price - x[0]))
        prox_level, prox_name = nearby[0]
        # Determine wall side: majority side of big trades
        buy_big  = sum(t.size for t in all_big if t.side == 'A')
        sell_big = sum(t.size for t in all_big if t.side == 'B')
        wall_side = 'ask' if buy_big >= sell_big else 'bid'
        # Wall level = close price of bar with most big trade volume
        wall_level = max(window, key=lambda b: sum(t.size for t in b.big_trades)).close
        candidates.append(CandidateBar(
            bar=bar,
            session_ctx=ctx,
            wall_level=wall_level,
            wall_side=wall_side,
            wall_trade_count=len(all_big),
            wall_max_size=max(t.size for t in all_big),
            proximity_to=prox_name,
            proximity_level=prox_level,
            bars_in_session=i,
            is_second_test=False,  # TODO: track level visits
        ))
    return candidates
```

- [ ] **Step 5.4: Run — verify PASS**

```bash
pytest tests/test_candidate_detector.py -v
```

- [ ] **Step 5.5: Commit**

```bash
git add src/candidate_detector.py tests/test_candidate_detector.py && git commit -m "feat: candidate detector — wall + VP proximity filter"
```

---

## Task 6: Strategy File + Signal Context Builder

**Files:**
- Create: `strategies/fabio_andrea_hybrid.json`
- Create: `src/signal_context.py`
- Create: `tests/test_signal_context.py`

- [ ] **Step 6.1: Create `strategies/fabio_andrea_hybrid.json`**

```json
{
  "strategy_id": "fabio_andrea_hybrid_v1",
  "fabio_nlm_question_template": "Bar at {bar_time_et} ET. Price: {close}. IVB high: {ib_high}, IVB low: {ib_low}. IVB range: {ib_range} points. Volume Profile POC: {poc}, VA high: {va_high}, VA low: {va_low}. LVNs: {lvn_levels}. Big trades in last {lookback} bars: {wall_trade_count} trades totaling {wall_total_size} contracts at price ~{wall_level}, side: {wall_side}. Largest single trade: {wall_max_size} contracts. Bar volume: {bar_volume}, delta: {bar_delta}, close relative to IVB: {ib_position}. Day type so far: {day_type}. Is this a valid squeeze/second-drive setup to go {suggested_direction}? What is your confidence 0-100? Provide entry, stop, and target in NQ points.",
  "andrea_nlm_question_template": "Bar at {bar_time_et} ET on NQ. Price: {close}. IB high: {ib_high}, IB low: {ib_low}. Fabio sees a {fabio_setup} setup going {fabio_direction} with confidence {fabio_confidence}. Big trade cluster at {wall_level} ({wall_side} side, {wall_trade_count} trades). Bar candle: open={open}, high={high}, low={low}, close={close}. Does this bar show an IBOB (Initial Balance Outside Bar) confirmation pattern? Is the close outside the IB? Are big trades in the candle body (not wick)? Does it confirm Fabio's {fabio_direction} bias? Confidence 0-100?",
  "no_trade_conditions": [
    "bar volume < 3000",
    "bar time < 09:40 ET",
    "no big trades in last 3 bars",
    "price not near any VP level within 4 ticks",
    "already in open trade"
  ]
}
```

- [ ] **Step 6.2: Write failing test `tests/test_signal_context.py`**

```python
import pytest, json
from datetime import datetime, timezone
import pytz
from src import Bar, SessionContext, VolumeProfile, CandidateBar, Trade
from src.signal_context import build_fabio_question, build_andrea_question

ET = pytz.timezone('America/New_York')

def _candidate() -> CandidateBar:
    dt = ET.localize(datetime(2025,4,30,9,45)).astimezone(timezone.utc)
    big = [Trade(dt, 'A', 20000.0, 50)]
    bar = Bar(dt, 19998, 20002, 19995, 20000, 4500, 2500, 2000,
              500, 11.1, 500, 19999.5, big)
    vp = VolumeProfile(poc=20000.0, va_high=20050.0, va_low=19950.0,
                       hvn_levels=[20030.0], lvn_levels=[20000.0])
    ctx = SessionContext('2025-04-30', 20020.0, 19980.0, 40.0, True, vp, 'balance')
    return CandidateBar(bar, ctx, 20000.0, 'ask', 1, 50, 'lvn', 20000.0, 15, False)

def test_fabio_question_contains_key_data():
    q = build_fabio_question(_candidate())
    assert '20000' in q
    assert '20020' in q or 'IVB' in q  # ib_high
    assert 'squeeze' in q.lower() or 'drive' in q.lower()

def test_andrea_question_requires_fabio_signal():
    from src import FabioSignal
    fab = FabioSignal('long', 75, 20002.0, 19990.0, 20040.0, 'squeeze', 'reasoning', 'nlm')
    q = build_andrea_question(_candidate(), fab)
    assert 'long' in q
    assert 'IBOB' in q or 'ibob' in q.lower()
```

- [ ] **Step 6.3: Run — verify FAIL**

- [ ] **Step 6.4: Implement `src/signal_context.py`**

```python
import json
from pathlib import Path
from datetime import timezone
import pytz
from src import CandidateBar, FabioSignal

ET = pytz.timezone('America/New_York')
STRATEGY_FILE = Path(__file__).parent.parent / 'strategies' / 'fabio_andrea_hybrid.json'

def _load_templates() -> dict:
    with open(STRATEGY_FILE, encoding='utf-8') as f:
        return json.load(f)

def build_fabio_question(candidate: CandidateBar) -> str:
    templates = _load_templates()
    bar = candidate.bar
    ctx = candidate.session_ctx
    t_et = bar.timestamp.astimezone(ET)
    ib_pos = 'above IVB' if bar.close > ctx.ib_high else \
             'below IVB' if bar.close < ctx.ib_low  else 'inside IVB'
    suggested = 'long' if candidate.wall_side == 'ask' else 'short'
    tpl = templates['fabio_nlm_question_template']
    return tpl.format(
        bar_time_et     = t_et.strftime('%H:%M'),
        close           = bar.close,
        ib_high         = ctx.ib_high,
        ib_low          = ctx.ib_low,
        ib_range        = ctx.ib_range,
        poc             = ctx.vp.poc if ctx.vp else 'N/A',
        va_high         = ctx.vp.va_high if ctx.vp else 'N/A',
        va_low          = ctx.vp.va_low if ctx.vp else 'N/A',
        lvn_levels      = str(ctx.vp.lvn_levels if ctx.vp else []),
        lookback        = 3,
        wall_trade_count= candidate.wall_trade_count,
        wall_total_size = sum(t.size for t in bar.big_trades),
        wall_level      = candidate.wall_level,
        wall_side       = candidate.wall_side,
        wall_max_size   = candidate.wall_max_size,
        bar_volume      = bar.volume,
        bar_delta       = bar.delta,
        ib_position     = ib_pos,
        day_type        = ctx.day_type,
        suggested_direction = suggested,
    )

def build_andrea_question(candidate: CandidateBar,
                           fabio_signal: FabioSignal) -> str:
    templates = _load_templates()
    bar = candidate.bar
    ctx = candidate.session_ctx
    t_et = bar.timestamp.astimezone(ET)
    tpl = templates['andrea_nlm_question_template']
    return tpl.format(
        bar_time_et     = t_et.strftime('%H:%M'),
        close           = bar.close,
        open            = bar.open,
        high            = bar.high,
        low             = bar.low,
        ib_high         = ctx.ib_high,
        ib_low          = ctx.ib_low,
        fabio_setup     = fabio_signal.setup_type,
        fabio_direction = fabio_signal.direction,
        fabio_confidence= fabio_signal.confidence,
        wall_level      = candidate.wall_level,
        wall_side       = candidate.wall_side,
        wall_trade_count= candidate.wall_trade_count,
    )
```

- [ ] **Step 6.5: Run — verify PASS**

```bash
pytest tests/test_signal_context.py -v
```

- [ ] **Step 6.6: Commit**

```bash
git add strategies/ src/signal_context.py tests/test_signal_context.py && git commit -m "feat: strategy template + signal context builder"
```

---

## Task 7: NLM Client + Agent Memory

**Files:**
- Create: `src/agents/__init__.py`
- Create: `src/agents/nlm_client.py`
- Create: `src/agent_memory.py`
- Create: `tests/test_nlm_client.py`
- Create: `tests/test_agent_memory.py`
- Create: `agent_memory/session_state.json`
- Create: `agent_memory/pattern_memory.json`

- [ ] **Step 7.1: Write failing test `tests/test_nlm_client.py`**

```python
import pytest
from unittest.mock import patch, MagicMock
from src.agents.nlm_client import nlm_ask, nlm_use_notebook

def test_nlm_ask_returns_stdout(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "The wall forms when big trades cluster at LVN.\n"
    mock_result.stderr = ""
    with patch('subprocess.run', return_value=mock_result) as mock_run:
        answer = nlm_ask("What is a wall?", "4c868e52")
    assert "wall" in answer.lower()
    # Verify CLI was called with correct notebook
    call_args = mock_run.call_args[0][0]
    assert "ask" in call_args
    assert "What is a wall?" in call_args

def test_nlm_ask_raises_on_auth_error():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Authentication expired. Run notebooklm login"
    with patch('subprocess.run', return_value=mock_result):
        with pytest.raises(RuntimeError, match="AUTH EXPIRED"):
            nlm_ask("question", "4c868e52")
```

- [ ] **Step 7.2: Run — verify FAIL**

- [ ] **Step 7.3: Implement `src/agents/nlm_client.py`**

```python
import subprocess, sys, time

def nlm_use_notebook(notebook_id: str) -> None:
    """Switch active NLM notebook."""
    subprocess.run(
        [sys.executable, '-m', 'notebooklm', 'use', notebook_id],
        capture_output=True, text=True, timeout=60
    )

def nlm_ask(question: str, notebook_id: str, retry: int = 0) -> str:
    """Ask a question to a NLM notebook. Returns answer string."""
    # Switch notebook first
    nlm_use_notebook(notebook_id)
    time.sleep(1)
    result = subprocess.run(
        [sys.executable, '-m', 'notebooklm', 'ask', question],
        capture_output=True, text=True, timeout=180
    )
    combined = result.stdout + result.stderr
    if 'Authentication expired' in combined or 'notebooklm login' in combined:
        raise RuntimeError("[AUTH EXPIRED] Run 'python -m notebooklm login' then retry.")
    if result.returncode != 0 and retry < 2:
        time.sleep(5)
        return nlm_ask(question, notebook_id, retry + 1)
    return result.stdout.strip()
```

- [ ] **Step 7.4: Create initial `agent_memory/session_state.json`**

```json
{
  "date": null,
  "ib_high": null,
  "ib_low": null,
  "poc": null,
  "day_type": "unknown",
  "open_trade": null,
  "daily_pnl_usd": 0.0,
  "trade_count_today": 0,
  "session_stopped": false
}
```

- [ ] **Step 7.5: Create initial `agent_memory/pattern_memory.json`**

```json
{
  "total_trades": 0,
  "wins": 0,
  "losses": 0,
  "win_rate": 0.0,
  "avg_r": 0.0,
  "best_setups": [],
  "worst_setups": [],
  "notes": []
}
```

- [ ] **Step 7.5b: Write failing test `tests/test_agent_memory.py`**

```python
import pytest, json, os, tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
from src import ClosedTrade

def _trade(pnl_usd, direction='long'):
    sign = 1 if pnl_usd >= 0 else -1
    entry, stop = 20000.0, 19990.0 if direction == 'long' else 20010.0
    exit_p = entry + sign * abs(pnl_usd) / 5
    return ClosedTrade(direction, entry, stop, entry+sign*20, exit_p,
                       'target', pnl_usd/5, pnl_usd,
                       datetime(2025,4,30,9,45,tzinfo=timezone.utc),
                       datetime(2025,4,30,10, 0,tzinfo=timezone.utc),
                       'fabio', 'andrea', 'squeeze', 75, 2.0)

def test_reset_session_writes_file(tmp_path):
    with patch('src.agent_memory.SESSION_FILE', tmp_path / 'session_state.json'):
        import src.agent_memory as am
        am.SESSION_FILE = tmp_path / 'session_state.json'
        state = am.reset_session('2025-04-30')
        assert state['date'] == '2025-04-30'
        assert state['daily_pnl_usd'] == 0.0
        with open(tmp_path / 'session_state.json') as f:
            saved = json.load(f)
        assert saved['date'] == '2025-04-30'

def test_log_reasoning_appends_jsonl(tmp_path):
    import src.agent_memory as am
    log = tmp_path / 'reasoning_log.jsonl'
    am.LOG_FILE = log
    am.log_reasoning({'bar_time': '09:45', 'decision': 'trade'})
    am.log_reasoning({'bar_time': '10:00', 'decision': 'no_trade'})
    lines = log.read_text().strip().split('\n')
    assert len(lines) == 2
    assert json.loads(lines[0])['decision'] == 'trade'

def test_update_pattern_memory_win_rate(tmp_path):
    import src.agent_memory as am
    pm_file = tmp_path / 'pattern_memory.json'
    pm_file.write_text(json.dumps({'total_trades':0,'wins':0,'losses':0,
                                   'win_rate':0.0,'avg_r':0.0,
                                   'best_setups':[],'worst_setups':[],'notes':[]}))
    am.PATTERN_FILE = pm_file
    am.update_pattern_memory(_trade(500, 'long'))
    am.update_pattern_memory(_trade(-250, 'short'))
    pm = json.loads(pm_file.read_text())
    assert pm['total_trades'] == 2
    assert pm['wins'] == 1
    assert pm['win_rate'] == pytest.approx(0.5)

def test_update_pattern_memory_r_positive_for_short_winner(tmp_path):
    """Short trade winner must produce positive R."""
    import src.agent_memory as am
    pm_file = tmp_path / 'pattern_memory.json'
    pm_file.write_text(json.dumps({'total_trades':0,'wins':0,'losses':0,
                                   'win_rate':0.0,'avg_r':0.0,
                                   'best_setups':[],'worst_setups':[],'notes':[]}))
    am.PATTERN_FILE = pm_file
    # Short: entry=20000, stop=20010, target=19980, exit at target → pnl_ticks=+80
    t = ClosedTrade('short', 20000.0, 20010.0, 19980.0, 19980.0, 'target',
                    80.0, 400.0,
                    datetime(2025,4,30,9,45,tzinfo=timezone.utc),
                    datetime(2025,4,30,10, 0,tzinfo=timezone.utc),
                    'fabio', 'andrea', 'squeeze', 75, 2.0)
    am.update_pattern_memory(t)
    pm = json.loads(pm_file.read_text())
    assert pm['avg_r'] > 0  # winner must have positive R
```

- [ ] **Step 7.5c: Run — verify FAIL**

```bash
pytest tests/test_agent_memory.py -v
```

- [ ] **Step 7.6: Implement `src/agent_memory.py`**

```python
import json
from pathlib import Path
from datetime import datetime, timezone

MEMORY_DIR = Path(__file__).parent.parent / 'agent_memory'
SESSION_FILE  = MEMORY_DIR / 'session_state.json'
PATTERN_FILE  = MEMORY_DIR / 'pattern_memory.json'
LOG_FILE      = MEMORY_DIR / 'reasoning_log.jsonl'

def load_session() -> dict:
    with open(SESSION_FILE, encoding='utf-8') as f:
        return json.load(f)

def save_session(state: dict) -> None:
    with open(SESSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def reset_session(date_str: str) -> dict:
    state = {
        'date': date_str,
        'ib_high': None, 'ib_low': None, 'poc': None,
        'day_type': 'unknown',
        'open_trade': None,
        'daily_pnl_usd': 0.0,
        'trade_count_today': 0,
        'session_stopped': False,
    }
    save_session(state)
    return state

def log_reasoning(entry: dict) -> None:
    """Append one reasoning entry to the JSONL log."""
    entry['logged_at'] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def update_pattern_memory(closed_trade) -> None:
    """Update cross-session pattern stats after closing a trade."""
    with open(PATTERN_FILE, encoding='utf-8') as f:
        pm = json.load(f)
    pm['total_trades'] += 1
    if closed_trade.pnl_usd > 0:
        pm['wins'] += 1
    else:
        pm['losses'] += 1
    pm['win_rate'] = pm['wins'] / pm['total_trades'] if pm['total_trades'] else 0.0
    # Rolling avg R
    risk_ticks = abs(closed_trade.entry - closed_trade.stop) / 0.25
    r = closed_trade.pnl_ticks / risk_ticks if risk_ticks > 0 else 0.0
    pm['avg_r'] = (pm['avg_r'] * (pm['total_trades'] - 1) + r) / pm['total_trades']
    with open(PATTERN_FILE, 'w', encoding='utf-8') as f:
        json.dump(pm, f, indent=2)
```

- [ ] **Step 7.7: Run tests — verify PASS**

```bash
pytest tests/test_nlm_client.py -v
```

- [ ] **Step 7.8: Commit**

```bash
git add src/agents/ src/agent_memory.py agent_memory/ tests/test_nlm_client.py tests/test_agent_memory.py && git commit -m "feat: NLM client + agent memory (session, pattern, reasoning log)"
```

---

## Task 8: Fabio Agent (Primary)

**Files:**
- Create: `src/agents/fabio_agent.py`
- Create: `tests/test_fabio_agent.py`

Reads relevant simplified_strategy topics from `knowledge/fabio_knowledge.json`, builds prompt, calls Claude API, parses FabioSignal.

- [ ] **Step 8.1: Write failing test `tests/test_fabio_agent.py`**

```python
import pytest, json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import pytz
from src import Bar, SessionContext, VolumeProfile, CandidateBar, Trade, FabioSignal
from src.agents.fabio_agent import analyze

ET = pytz.timezone('America/New_York')

def _candidate():
    dt = ET.localize(datetime(2025,4,30,9,45)).astimezone(timezone.utc)
    big = [Trade(dt, 'A', 20000.0, 50)]
    bar = Bar(dt, 19998, 20002, 19995, 20000, 4500, 2500, 2000,
              500, 11.1, 500, 19999.5, big)
    vp = VolumeProfile(poc=20000.0, va_high=20050.0, va_low=19950.0,
                       hvn_levels=[20030.0], lvn_levels=[20000.0])
    ctx = SessionContext('2025-04-30', 20020.0, 19980.0, 40.0, True, vp, 'balance')
    return CandidateBar(bar, ctx, 20000.0, 'ask', 1, 50, 'lvn', 20000.0, 15, True)

MOCK_CLAUDE_RESPONSE = json.dumps({
    "direction": "long",
    "confidence": 78,
    "entry": 20002.0,
    "stop": 19990.0,
    "target": 20040.0,
    "setup_type": "squeeze",
    "reasoning": "Big buy cluster at LVN + second test = squeeze setup long."
})

def test_analyze_returns_fabio_signal(tmp_path):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=MOCK_CLAUDE_RESPONSE)]
    with patch('src.agents.fabio_agent.nlm_ask', return_value="NLM context here"):
        with patch('anthropic.Anthropic') as MockClaude:
            MockClaude.return_value.messages.create.return_value = mock_msg
            signal = analyze(_candidate())
    assert isinstance(signal, FabioSignal)
    assert signal.direction == 'long'
    assert signal.confidence == 78
    assert signal.entry == pytest.approx(20002.0)

def test_analyze_returns_none_signal_on_no_trade():
    no_trade_response = json.dumps({
        "direction": "none", "confidence": 30,
        "entry": None, "stop": None, "target": None,
        "setup_type": "none",
        "reasoning": "No clear setup."
    })
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=no_trade_response)]
    with patch('src.agents.fabio_agent.nlm_ask', return_value="context"):
        with patch('anthropic.Anthropic') as MockClaude:
            MockClaude.return_value.messages.create.return_value = mock_msg
            signal = analyze(_candidate())
    assert signal.direction == 'none'
    assert signal.confidence == 30
```

- [ ] **Step 8.2: Run — verify FAIL**

- [ ] **Step 8.3: Implement `src/agents/fabio_agent.py`**

```python
import json, os
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from src import CandidateBar, FabioSignal, FABIO_NOTEBOOK_ID
from src.agents.nlm_client import nlm_ask
from src.signal_context import build_fabio_question

load_dotenv()

KNOWLEDGE_FILE = Path(__file__).parent.parent.parent / 'knowledge' / 'fabio_knowledge.json'

# Topics from simplified_strategy that are most relevant per candidate type
RELEVANT_TOPICS = [
    'simplified_model_overview',
    'simplified_wall_definition',
    'simplified_second_drive_exact',
    'simplified_entry_trigger',
    'simplified_stop_exact',
    'simplified_target_exact',
    'simplified_ivb_formation',
    'simplified_no_trade_top3',
    'myisto_pattern',
]

def _load_knowledge() -> str:
    with open(KNOWLEDGE_FILE, encoding='utf-8') as f:
        data = json.load(f)
    simplified = data.get('simplified_strategy', {})
    parts = []
    for topic in RELEVANT_TOPICS:
        if topic in simplified:
            parts.append(f"### {topic}\n{simplified[topic]}\n")
    return '\n'.join(parts)

SYSTEM_PROMPT = """You are Fabio Valentini's trading methodology agent analyzing NQ futures.
You follow the simplified Chart Fanatics approach: Big Trades (≥30 contracts) clustering at LVN/POC + IVB breakout direction + second drive = high probability squeeze.
NO CVD analysis. NO multi-timeframe. Keep it simple and mechanical.

Respond ONLY with valid JSON matching this schema:
{
  "direction": "long" | "short" | "none",
  "confidence": <int 0-100>,
  "entry": <float or null>,
  "stop": <float or null>,
  "target": <float or null>,
  "setup_type": "squeeze" | "ivb_breakout" | "none",
  "reasoning": "<2-3 sentence explanation>"
}
"""

def analyze(candidate: CandidateBar) -> FabioSignal:
    knowledge = _load_knowledge()
    nlm_question = build_fabio_question(candidate)
    nlm_answer = nlm_ask(nlm_question, FABIO_NOTEBOOK_ID)

    user_msg = f"""## Fabio's Knowledge (Simplified Strategy)
{knowledge}

## NotebookLM Context
{nlm_answer}

## Current Bar Data
{build_fabio_question(candidate)}

Analyze this setup and respond with JSON only."""

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    response = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_msg}],
    )
    raw = response.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()

    data = json.loads(raw)
    return FabioSignal(
        direction   = data.get('direction', 'none'),
        confidence  = int(data.get('confidence', 0)),
        entry       = data.get('entry'),
        stop        = data.get('stop'),
        target      = data.get('target'),
        setup_type  = data.get('setup_type', 'none'),
        reasoning   = data.get('reasoning', ''),
        nlm_answer  = nlm_answer,
    )
```

- [ ] **Step 8.4: Run — verify PASS**

```bash
pytest tests/test_fabio_agent.py -v
```

- [ ] **Step 8.5: Commit**

```bash
git add src/agents/fabio_agent.py tests/test_fabio_agent.py && git commit -m "feat: Fabio agent — NLM + Claude → FabioSignal"
```

---

## Task 9: Andrea Agent (Confirmation)

**Files:**
- Create: `src/agents/andrea_agent.py`
- Create: `tests/test_andrea_agent.py`

Only called when Fabio confidence ≥ FABIO_MIN_CONFIDENCE. Checks IBOB conditions.

- [ ] **Step 9.1: Write failing test `tests/test_andrea_agent.py`**

```python
import pytest, json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import pytz
from src import Bar, SessionContext, VolumeProfile, CandidateBar, Trade, FabioSignal, AndreaSignal
from src.agents.andrea_agent import confirm

ET = pytz.timezone('America/New_York')

def _candidate_and_fabio():
    dt = ET.localize(datetime(2025,4,30,9,45)).astimezone(timezone.utc)
    big = [Trade(dt, 'A', 20000.0, 50)]
    bar = Bar(dt, 19998, 20002, 19995, 20000, 4500, 2500, 2000,
              500, 11.1, 500, 19999.5, big)
    vp = VolumeProfile(poc=20000.0, va_high=20050.0, va_low=19950.0,
                       hvn_levels=[], lvn_levels=[20000.0])
    ctx = SessionContext('2025-04-30', 20020.0, 19980.0, 40.0, True, vp, 'balance')
    cand = CandidateBar(bar, ctx, 20000.0, 'ask', 1, 50, 'lvn', 20000.0, 15, True)
    fab = FabioSignal('long', 75, 20002.0, 19990.0, 20040.0, 'squeeze', 'reasoning', 'nlm')
    return cand, fab

MOCK_ANDREA = json.dumps({
    "confirmation": True,
    "confidence": 70,
    "setup_type": "ibob",
    "reasoning": "Close outside IB high, big trade in body, confirms long."
})

def test_confirm_returns_andrea_signal():
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=MOCK_ANDREA)]
    cand, fab = _candidate_and_fabio()
    with patch('src.agents.andrea_agent.nlm_ask', return_value="Andrea NLM context"):
        with patch('anthropic.Anthropic') as MockClaude:
            MockClaude.return_value.messages.create.return_value = mock_msg
            signal = confirm(cand, fab)
    assert isinstance(signal, AndreaSignal)
    assert signal.confirmation is True
    assert signal.confidence == 70
```

- [ ] **Step 9.2: Run — verify FAIL**

- [ ] **Step 9.3: Implement `src/agents/andrea_agent.py`**

```python
import json, os
from pathlib import Path
import anthropic
from dotenv import load_dotenv
from src import CandidateBar, FabioSignal, AndreaSignal, ANDREA_NOTEBOOK_ID
from src.agents.nlm_client import nlm_ask
from src.signal_context import build_andrea_question

load_dotenv()

KNOWLEDGE_FILE = Path(__file__).parent.parent.parent / 'knowledge' / 'andrea_knowledge.json'
RELEVANT_TOPICS = [
    'ibob_overview', 'ibob_candle_close',
    'ibob_bubble_body_vs_wick', 'ibob_diagonal_imbalances',
    'ibob_stop_target', 'ibob_invalidation',
    'simplified_entry_mechanical',
]

def _load_knowledge() -> str:
    with open(KNOWLEDGE_FILE, encoding='utf-8') as f:
        data = json.load(f)
    simplified = data.get('simplified_strategy', {})
    return '\n'.join(
        f"### {t}\n{simplified[t]}\n"
        for t in RELEVANT_TOPICS if t in simplified
    )

SYSTEM_PROMPT = """You are Andrea Cimi's methodology agent providing confirmation analysis for NQ futures.
You check IBOB (Initial Balance Outside Bar) conditions: candle close outside IB, big bubble in candle body (not wick), 2-3 diagonal imbalances in footprint.
You confirm or veto Fabio Valentini's primary signal.

Respond ONLY with valid JSON:
{
  "confirmation": true | false,
  "confidence": <int 0-100>,
  "setup_type": "ibob" | "failed_auction" | "none",
  "reasoning": "<2 sentence explanation>"
}
"""

def confirm(candidate: CandidateBar, fabio_signal: FabioSignal) -> AndreaSignal:
    knowledge = _load_knowledge()
    nlm_question = build_andrea_question(candidate, fabio_signal)
    nlm_answer = nlm_ask(nlm_question, ANDREA_NOTEBOOK_ID)

    user_msg = f"""## Andrea's Knowledge (IBOB Simplified)
{knowledge}

## NotebookLM Context
{nlm_answer}

## Bar Context + Fabio's Signal
{build_andrea_question(candidate, fabio_signal)}

Does this bar confirm Fabio's signal? Respond with JSON only."""

    client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    response = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{'role': 'user', 'content': user_msg}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()
    data = json.loads(raw)
    return AndreaSignal(
        confirmation = bool(data.get('confirmation', False)),
        confidence   = int(data.get('confidence', 0)),
        setup_type   = data.get('setup_type', 'none'),
        reasoning    = data.get('reasoning', ''),
        nlm_answer   = nlm_answer,
    )
```

- [ ] **Step 9.4: Run — verify PASS**

```bash
pytest tests/test_andrea_agent.py -v
```

- [ ] **Step 9.5: Commit**

```bash
git add src/agents/andrea_agent.py tests/test_andrea_agent.py && git commit -m "feat: Andrea confirmation agent — IBOB check → AndreaSignal"
```

---

## Task 10: Consensus

**Files:**
- Create: `src/consensus.py`
- Create: `tests/test_consensus.py`

Logic:
- Fabio confidence < 65 → no_trade ("fabio_below_threshold")
- Andrea confirmation == False AND confidence < 40 → no_trade ("andrea_veto")
- Otherwise → trade; final_confidence = fabio * 1.1 if andrea confirms, else fabio * 0.85

- [ ] **Step 10.1: Write failing test**

```python
import pytest
from src import FabioSignal, AndreaSignal, ConsensusSignal
from src.consensus import build_consensus

def _fab(conf, direction='long'):
    return FabioSignal(direction, conf, 20002.0, 19990.0, 20040.0,
                       'squeeze', 'reasoning', 'nlm')
def _and(confirm, conf):
    return AndreaSignal(confirm, conf, 'ibob' if confirm else 'none', 'r', 'nlm')

def test_fabio_below_threshold_no_trade():
    c = build_consensus(_fab(60), _and(True, 70))
    assert c.decision == 'no_trade'
    assert 'fabio' in c.no_trade_reason

def test_andrea_veto_no_trade():
    c = build_consensus(_fab(75), _and(False, 35))
    assert c.decision == 'no_trade'
    assert 'andrea' in c.no_trade_reason

def test_andrea_confirms_trade():
    c = build_consensus(_fab(75), _and(True, 65))
    assert c.decision == 'trade'
    assert c.final_confidence > 75  # boosted

def test_andrea_no_confirm_but_not_veto_still_trades():
    c = build_consensus(_fab(75), _and(False, 50))  # 50 >= veto threshold
    assert c.decision == 'trade'
    assert c.final_confidence < 75  # penalized

def test_r_ratio_calculated():
    c = build_consensus(_fab(75), _and(True, 65))
    # entry=20002, stop=19990, target=20040 → R = (20040-20002)/(20002-19990) = 38/12 ≈ 3.17
    assert c.r_ratio == pytest.approx(38/12, rel=0.01)
```

- [ ] **Step 10.2: Run — verify FAIL**

- [ ] **Step 10.3: Implement `src/consensus.py`**

```python
from src import (FabioSignal, AndreaSignal, ConsensusSignal,
                 FABIO_MIN_CONFIDENCE, ANDREA_VETO_THRESHOLD)

def build_consensus(fabio: FabioSignal, andrea: AndreaSignal) -> ConsensusSignal:
    # Gate 1: Fabio confidence
    if fabio.confidence < FABIO_MIN_CONFIDENCE or fabio.direction == 'none':
        return ConsensusSignal(
            direction='none', entry=0, stop=0, target=0,
            r_ratio=0, final_confidence=fabio.confidence,
            fabio=fabio, andrea=andrea,
            decision='no_trade',
            no_trade_reason=f'fabio_below_threshold ({fabio.confidence} < {FABIO_MIN_CONFIDENCE})',
        )
    # Gate 2: Andrea veto
    if not andrea.confirmation and andrea.confidence < ANDREA_VETO_THRESHOLD:
        return ConsensusSignal(
            direction='none', entry=0, stop=0, target=0,
            r_ratio=0, final_confidence=fabio.confidence,
            fabio=fabio, andrea=andrea,
            decision='no_trade',
            no_trade_reason=f'andrea_veto (confidence={andrea.confidence})',
        )
    # Trade approved
    boost = 1.1 if andrea.confirmation else 0.85
    final_conf = min(100, int(fabio.confidence * boost))
    entry  = fabio.entry  or 0.0
    stop   = fabio.stop   or 0.0
    target = fabio.target or 0.0
    risk   = abs(entry - stop)
    reward = abs(target - entry)
    r_ratio = round(reward / risk, 2) if risk > 0 else 0.0
    return ConsensusSignal(
        direction        = fabio.direction,
        entry            = entry,
        stop             = stop,
        target           = target,
        r_ratio          = r_ratio,
        final_confidence = final_conf,
        fabio            = fabio,
        andrea           = andrea,
        decision         = 'trade',
        no_trade_reason  = '',
    )
```

- [ ] **Step 10.4: Run — verify PASS**

```bash
pytest tests/test_consensus.py -v
```

- [ ] **Step 10.5: Commit**

```bash
git add src/consensus.py tests/test_consensus.py && git commit -m "feat: consensus — Fabio primary + Andrea veto logic"
```

---

## Task 11: Trade Simulator

**Files:**
- Create: `src/trade_simulator.py`
- Create: `tests/test_trade_simulator.py`

Walks forward through subsequent bars. Closes trade when: high ≥ target (long), low ≤ stop (long), or session ends.

- [ ] **Step 11.1: Write failing test**

```python
import pytest
from datetime import datetime, timezone
from src import Bar, ConsensusSignal, FabioSignal, AndreaSignal, OpenTrade, ClosedTrade
from src.trade_simulator import open_trade, step_trade, close_eod

def _bar(h, m, hi, lo, vol=4000):
    dt = datetime(2025,4,30,h,m,tzinfo=timezone.utc)
    return Bar(dt, (hi+lo)/2, hi, lo, (hi+lo)/2, vol,
               vol//2, vol//2, 0, 0.0, 0, (hi+lo)/2)

def _consensus(direction='long', entry=20000.0, stop=19990.0, target=20020.0):
    fab = FabioSignal(direction, 75, entry, stop, target, 'squeeze', 'r', 'nlm')
    and_ = AndreaSignal(True, 70, 'ibob', 'r', 'nlm')
    from src.consensus import build_consensus
    return build_consensus(fab, and_)

def test_long_hits_target():
    trade = open_trade(_consensus('long', 20000, 19990, 20020), _bar(13,30,20001,19999))
    bars = [_bar(13,31,20025,20010)]  # high exceeds target
    closed = step_trade(trade, bars)
    assert closed is not None
    assert closed.exit_reason == 'target'
    assert closed.pnl_usd > 0

def test_long_hits_stop():
    trade = open_trade(_consensus('long', 20000, 19990, 20020), _bar(13,30,20001,19999))
    bars = [_bar(13,31,20005,19985)]  # low below stop
    closed = step_trade(trade, bars)
    assert closed is not None
    assert closed.exit_reason == 'stop'
    assert closed.pnl_usd < 0

def test_short_hits_target():
    trade = open_trade(_consensus('short', 20000, 20010, 19980), _bar(13,30,20001,19999))
    bars = [_bar(13,31,19990,19975)]  # low below target 19980
    closed = step_trade(trade, bars)
    assert closed is not None
    assert closed.exit_reason == 'target'
    assert closed.pnl_usd > 0

def test_short_hits_stop():
    trade = open_trade(_consensus('short', 20000, 20010, 19980), _bar(13,30,20001,19999))
    bars = [_bar(13,31,20015,20005)]  # high above stop 20010
    closed = step_trade(trade, bars)
    assert closed is not None
    assert closed.exit_reason == 'stop'
    assert closed.pnl_usd < 0

def test_eod_close():
    trade = open_trade(_consensus('long', 20000, 19990, 20020), _bar(13,30,20001,19999))
    closed = close_eod(trade, _bar(15,59,20010,19995))
    assert closed.exit_reason == 'eod'
```

- [ ] **Step 11.2: Run — verify FAIL**

- [ ] **Step 11.3: Implement `src/trade_simulator.py`**

```python
from src import (Bar, ConsensusSignal, OpenTrade, ClosedTrade,
                 NQ_TICK_SIZE, NQ_TICK_VALUE)

def open_trade(consensus: ConsensusSignal, entry_bar: Bar) -> OpenTrade:
    return OpenTrade(
        direction  = consensus.direction,
        entry      = consensus.entry,
        stop       = consensus.stop,
        target     = consensus.target,
        entry_bar  = entry_bar,
        consensus  = consensus,
    )

def _close(trade: OpenTrade, exit_price: float,
           exit_reason: str, exit_bar: Bar) -> ClosedTrade:
    sign = 1 if trade.direction == 'long' else -1
    pnl_ticks = sign * (exit_price - trade.entry) / NQ_TICK_SIZE
    pnl_usd   = pnl_ticks * NQ_TICK_VALUE
    risk_ticks = abs(trade.entry - trade.stop) / NQ_TICK_SIZE
    r_actual   = pnl_ticks / risk_ticks if risk_ticks > 0 else 0.0
    return ClosedTrade(
        direction        = trade.direction,
        entry            = trade.entry,
        stop             = trade.stop,
        target           = trade.target,
        exit_price       = exit_price,
        exit_reason      = exit_reason,
        pnl_ticks        = pnl_ticks,
        pnl_usd          = pnl_usd,
        entry_time       = trade.entry_bar.timestamp,
        exit_time        = exit_bar.timestamp,
        fabio_reasoning  = trade.consensus.fabio.reasoning,
        andrea_reasoning = trade.consensus.andrea.reasoning,
        setup_type       = trade.consensus.fabio.setup_type,
        final_confidence = trade.consensus.final_confidence,
        r_ratio          = trade.consensus.r_ratio,
    )

def step_trade(trade: OpenTrade, bars: list) -> 'ClosedTrade | None':
    """Walk forward through bars. Return ClosedTrade if exited, else None."""
    for bar in bars:
        if trade.direction == 'long':
            if bar.high >= trade.target:
                return _close(trade, trade.target, 'target', bar)
            if bar.low <= trade.stop:
                return _close(trade, trade.stop, 'stop', bar)
        else:  # short
            if bar.low <= trade.target:
                return _close(trade, trade.target, 'target', bar)
            if bar.high >= trade.stop:
                return _close(trade, trade.stop, 'stop', bar)
    return None

def close_eod(trade: OpenTrade, last_bar: Bar) -> ClosedTrade:
    return _close(trade, last_bar.close, 'eod', last_bar)
```

- [ ] **Step 11.4: Run — verify PASS**

```bash
pytest tests/test_trade_simulator.py -v
```

- [ ] **Step 11.5: Commit**

```bash
git add src/trade_simulator.py tests/test_trade_simulator.py && git commit -m "feat: trade simulator — mark-to-market, target/stop/eod exits"
```

---

## Task 12: Backtest Runner + Metrics + CLI

**Files:**
- Create: `src/backtest_runner.py`
- Create: `src/metrics_reporter.py`
- Create: `run_backtest.py`
- Create: `tests/test_metrics_reporter.py`

- [ ] **Step 12.1: Write failing test `tests/test_metrics_reporter.py`**

```python
import pytest
from datetime import datetime, timezone
from src import ClosedTrade
from src.metrics_reporter import compute_metrics

def _trade(pnl_usd, setup='squeeze', conf=75):
    sign = 1 if pnl_usd >= 0 else -1
    exit_p = 20000 + sign * abs(pnl_usd) / 5  # rough
    return ClosedTrade(
        'long', 20000.0, 19990.0, 20020.0, exit_p,
        'target' if pnl_usd > 0 else 'stop',
        pnl_usd/5, pnl_usd,
        datetime(2025,4,30,9,45,tzinfo=timezone.utc),
        datetime(2025,4,30,10, 0,tzinfo=timezone.utc),
        'fabio reasoning', 'andrea reasoning', setup, conf, 2.0
    )

def test_win_rate():
    trades = [_trade(500), _trade(500), _trade(-250)]
    m = compute_metrics(trades)
    assert m['win_rate'] == pytest.approx(2/3)

def test_profit_factor():
    trades = [_trade(500), _trade(500), _trade(-250)]
    m = compute_metrics(trades)
    assert m['profit_factor'] == pytest.approx(1000/250)

def test_empty_trades():
    m = compute_metrics([])
    assert m['total_trades'] == 0
```

- [ ] **Step 12.2: Run — verify FAIL**

- [ ] **Step 12.3: Implement `src/metrics_reporter.py`**

```python
import json
from pathlib import Path
from src import ClosedTrade

def compute_metrics(trades: list) -> dict:
    if not trades:
        return {'total_trades': 0, 'wins': 0, 'losses': 0,
                'win_rate': 0.0, 'profit_factor': 0.0,
                'total_pnl_usd': 0.0, 'avg_r': 0.0}
    wins   = [t for t in trades if t.pnl_usd > 0]
    losses = [t for t in trades if t.pnl_usd <= 0]
    gross_profit = sum(t.pnl_usd for t in wins)
    gross_loss   = abs(sum(t.pnl_usd for t in losses))
    avg_r = sum(t.pnl_ticks / ((abs(t.entry - t.stop) / 0.25) or 1)
                for t in trades) / len(trades)
    return {
        'total_trades':   len(trades),
        'wins':           len(wins),
        'losses':         len(losses),
        'win_rate':       len(wins) / len(trades),
        'profit_factor':  round(gross_profit / gross_loss, 2) if gross_loss else 0.0,
        'total_pnl_usd':  round(sum(t.pnl_usd for t in trades), 2),
        'avg_pnl_usd':    round(sum(t.pnl_usd for t in trades) / len(trades), 2),
        'avg_r':          round(avg_r, 2),
        'by_setup':       _by_setup(trades),
    }

def _by_setup(trades: list) -> dict:
    result = {}
    for t in trades:
        s = t.setup_type
        result.setdefault(s, {'count': 0, 'pnl_usd': 0.0, 'wins': 0})
        result[s]['count']   += 1
        result[s]['pnl_usd'] += t.pnl_usd
        if t.pnl_usd > 0:
            result[s]['wins'] += 1
    return result

def save_report(metrics: dict, trades: list, output_dir: str, date_str: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    # JSON metrics
    with open(out / f'metrics_{date_str}.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    # Reasoning log (per day)
    log_path = out / f'trades_{date_str}.jsonl'
    with open(log_path, 'w', encoding='utf-8') as f:
        for t in trades:
            f.write(json.dumps({
                'entry_time':   t.entry_time.isoformat(),
                'exit_time':    t.exit_time.isoformat(),
                'direction':    t.direction,
                'entry':        t.entry,
                'exit_price':   t.exit_price,
                'exit_reason':  t.exit_reason,
                'pnl_usd':      t.pnl_usd,
                'setup_type':   t.setup_type,
                'confidence':   t.final_confidence,
                'r_ratio':      t.r_ratio,
                'fabio':        t.fabio_reasoning,
                'andrea':       t.andrea_reasoning,
            }) + '\n')
```

- [ ] **Step 12.4: Implement `src/backtest_runner.py`**

```python
"""
Main backtest loop.
For each day:
  1. Load trades from CSV
  2. Aggregate to 1-min bars
  3. Filter NY window
  4. Build Volume Profile (from all session bars)
  5. Build SessionContext (IB, day_type)
  6. Detect candidates
  7. For each candidate: Fabio → Andrea → Consensus → TradeSimulator
  8. Log to agent_memory, collect ClosedTrades
"""
import json
from pathlib import Path
from src.data_loader import load_day, list_data_files
from src.bar_aggregator import aggregate_to_bars
from src.volume_profile import compute_volume_profile
from src.session_context import filter_ny_window, build_session_context
from src.candidate_detector import detect_candidates
from src.agents.fabio_agent import analyze as fabio_analyze
from src.agents.andrea_agent import confirm as andrea_confirm
from src.consensus import build_consensus
from src.trade_simulator import open_trade, step_trade, close_eod
from src.agent_memory import reset_session, log_reasoning, update_pattern_memory
from src import FABIO_MIN_CONFIDENCE

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'

def run_day(csv_path: str, dry_run: bool = False) -> list:
    """Run backtest for one day. Returns list[ClosedTrade]."""
    from pathlib import Path
    date_str = Path(csv_path).name.split('-')[2].split('.')[0]  # e.g. 20250430
    date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    state = reset_session(date_str)
    trades_raw = load_day(csv_path)
    bars_all   = aggregate_to_bars(trades_raw, freq='1min')
    bars_ny    = filter_ny_window(bars_all)
    if not bars_ny:
        return []

    vp  = compute_volume_profile(bars_ny)
    ctx = build_session_context(date_str, bars_ny, vp)
    candidates = detect_candidates(bars_ny, ctx)

    closed_trades = []
    open_t        = None
    trade_start_i = None   # index in bars_ny where current trade was opened

    # Build a mapping from bar timestamp → index for O(1) lookup
    bar_ts_to_idx = {b.timestamp: i for i, b in enumerate(bars_ny)}

    for candidate in candidates:
        bar_idx = bar_ts_to_idx.get(candidate.bar.timestamp)
        if bar_idx is None:
            continue

        # If a trade is open, try to advance it up to this bar
        if open_t is not None:
            check_bars = bars_ny[trade_start_i + 1: bar_idx + 1]
            result = step_trade(open_t, check_bars)
            if result:
                closed_trades.append(result)
                update_pattern_memory(result)
                open_t = None
                trade_start_i = None
            else:
                continue  # still open, skip new candidate

        if dry_run:
            print(f"  [DRY RUN] {candidate.bar.timestamp} "
                  f"| wall={candidate.wall_level} | near={candidate.proximity_to}")
            continue

        # Fabio primary analysis
        fabio_signal = fabio_analyze(candidate)
        log_entry = {
            'date': date_str,
            'bar_time': candidate.bar.timestamp.isoformat(),
            'wall_level': candidate.wall_level,
            'proximity_to': candidate.proximity_to,
            'fabio_direction': fabio_signal.direction,
            'fabio_confidence': fabio_signal.confidence,
        }

        if fabio_signal.confidence < FABIO_MIN_CONFIDENCE:
            log_entry['decision'] = 'no_trade'
            log_entry['reason'] = f'fabio_confidence={fabio_signal.confidence}'
            log_reasoning(log_entry)
            continue

        # Andrea confirmation
        andrea_signal = andrea_confirm(candidate, fabio_signal)
        log_entry['andrea_confirmation'] = andrea_signal.confirmation
        log_entry['andrea_confidence']   = andrea_signal.confidence

        consensus = build_consensus(fabio_signal, andrea_signal)
        log_entry['decision']          = consensus.decision
        log_entry['final_confidence']  = consensus.final_confidence

        if consensus.decision == 'trade':
            open_t        = open_trade(consensus, candidate.bar)
            trade_start_i = bar_idx

        log_reasoning(log_entry)

    # EOD: close any trade still open after all candidates processed
    if open_t is not None and bars_ny:
        remaining = bars_ny[trade_start_i + 1:]
        result    = step_trade(open_t, remaining) or close_eod(open_t, bars_ny[-1])
        closed_trades.append(result)
        update_pattern_memory(result)

    return closed_trades


def run_backtest(data_dir: str, max_days: int = 0, dry_run: bool = False) -> list:
    """Run all days. Returns all ClosedTrades."""
    files = list_data_files(data_dir)
    if max_days:
        files = files[:max_days]
    all_trades = []
    for f in files:
        print(f"Processing {Path(f).name}...")
        day_trades = run_day(f, dry_run=dry_run)
        all_trades.extend(day_trades)
        print(f"  → {len(day_trades)} trades")
    return all_trades
```

- [ ] **Step 12.5: Create `run_backtest.py` CLI**

```python
#!/usr/bin/env python
"""
CLI entry point.
Usage:
  python run_backtest.py                     # run all 106 days
  python run_backtest.py --days 5            # first 5 days
  python run_backtest.py --days 1 --dry-run  # no API calls, just detect candidates
"""
import argparse
from src.backtest_runner import run_backtest, DATA_DIR
from src.metrics_reporter import compute_metrics, save_report

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--days',    type=int, default=0, help='0=all')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--data-dir', default=DATA_DIR)
    p.add_argument('--output',   default='output/reports')
    args = p.parse_args()

    trades = run_backtest(args.data_dir, args.days, args.dry_run)
    if not trades:
        print("No trades generated.")
        return
    metrics = compute_metrics(trades)
    print("\n=== BACKTEST RESULTS ===")
    print(f"Total trades:   {metrics['total_trades']}")
    print(f"Win rate:       {metrics['win_rate']:.1%}")
    print(f"Profit factor:  {metrics['profit_factor']:.2f}")
    print(f"Total P&L:      ${metrics['total_pnl_usd']:,.2f}")
    print(f"Avg R:          {metrics['avg_r']:.2f}")
    if not args.dry_run:
        save_report(metrics, trades, args.output, 'full')

if __name__ == '__main__':
    main()
```

- [ ] **Step 12.6: Run metrics test — verify PASS**

```bash
pytest tests/test_metrics_reporter.py -v
```

- [ ] **Step 12.7: Smoke test dry-run (no API calls)**

```bash
cd C:\Users\Mauro\Documents\nq-backtest
python run_backtest.py --days 1 --dry-run
```
Expected: prints candidate bars found, 0 API calls, no errors.

- [ ] **Step 12.8: Run all tests**

```bash
pytest tests/ -v
```
Expected: all tests PASS

- [ ] **Step 12.9: Final commit**

```bash
git add src/backtest_runner.py src/metrics_reporter.py run_backtest.py tests/test_metrics_reporter.py && git commit -m "feat: backtest runner, metrics reporter, CLI — system complete"
```

---

## Running the Full Backtest

After all tasks pass:

```bash
# Dry run 5 days (verify candidate detection, no API cost)
python run_backtest.py --days 5 --dry-run

# Live run 5 days (~100 NLM queries + ~100 Claude API calls)
python run_backtest.py --days 5

# Full 106-day run
python run_backtest.py
```

Output files:
- `output/reports/metrics_full.json` — win rate, profit factor, avg R, by-setup breakdown
- `output/reports/trades_full.jsonl` — per-trade reasoning log
- `agent_memory/reasoning_log.jsonl` — full audit trail with NLM answers
- `agent_memory/pattern_memory.json` — updated cross-session stats
