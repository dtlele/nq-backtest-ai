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
