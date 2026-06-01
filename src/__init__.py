from dataclasses import dataclass, field
from typing import Optional, List
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
NY_WINDOW_END_H         = 12
NY_WINDOW_END_M         = 30
FABIO_ACTIVE_H          = 9
FABIO_ACTIVE_M          = 35
IB_DURATION_MIN         = 30       # Fabio's IVB = first 30 min (per recent videos)

# ── Candidate detection ───────────────────────────────────────────────────────
MIN_VOLUME_PER_BAR      = 3000     # Momentum Floor for NQ Full
MIN_REVERSAL_VOLUME     = 1500     # Reversal Floor (Requires Absorption)
VA_PROXIMITY_TICKS      = 12       # 12 ticks = 3 pts — "near" for M5 bar closes (expanded for 2025 volatility)
STOP_LOSS_BUFFER_TICKS = 4        # Institutional safety margin behind the wall
BIG_TRADE_LOOKBACK_BARS = 3        # 3 M5 bars = 15 min lookback for wall cluster
RECENT_BARS_CONTEXT     = 6        # M5 bars of context sent to agents (30 min)

# ── Agent thresholds ──────────────────────────────────────────────────────────
FABIO_MIN_CONFIDENCE       = 75
ANDREA_VETO_THRESHOLD      = 40
LIGHT_CONFIDENCE_THRESHOLD = 50   # two-pass: skip full analysis if light pass below this

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
class DailySummary:
    vp: VolumeProfile
    close_price: float
    date: str

@dataclass
class SessionContext:
    date: str
    ib_high: float
    ib_low: float
    ib_range: float
    ib_complete: bool
    vp: Optional[VolumeProfile]
    prev_day_vp: Optional[VolumeProfile] = None  # yesterday's session VP (legacy, keep for backward compat)
    historical_days: List[DailySummary] = field(default_factory=list) # [T-1, T-2, ...]
    day_type: str = 'unknown'  # 'trend_up'|'trend_down'|'balance'|'unknown'
    day_type_history: List[str] = field(default_factory=list)  # history of day_type over session

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
    setup_category: str = 'momentum'  # 'momentum'|'reversal'
    recent_bars: list = field(default_factory=list)  # last N M5 bars incl. candidate
    market_state: str = 'balance'  # 'balance'|'imbalance'
    poc_migration: str = 'flat'    # 'up'|'down'|'flat'
    auction_type: str = 'responsive' # 'responsive'|'initiative'
    upcoming_news: str = "No high-impact news in the vicinity."
    vwap: float = 0.0          # Current Intraday VWAP at this bar
    nav_alert: bool = False    # True if Volume > Mean + 2.33*StdDev

@dataclass
class FabioSignal:
    direction: str             # 'long'|'short'|'none'
    confidence: int            # 0-100
    entry: Optional[float]
    stop: Optional[float]
    target: Optional[float]
    setup_type: str            # 'squeeze'|'ivb_breakout'|'none'
    reasoning: str             # Claude's reasoning text
    market_narrative_update: str = "" # NEW: Continuous story update
    nlm_answer: str = ""            # raw NLM response

@dataclass
class AndreaSignal:
    confirmation: bool         # True = confirms Fabio direction
    confidence: int            # 0-100; below ANDREA_VETO_THRESHOLD = veto
    setup_type: str            # 'ibob'|'failed_auction'|'none'
    reasoning: str
    nlm_answer: str = ""
    structural_stop: Optional[float] = None # Added for V3.1 Structural SL

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
    news_flag: str = "none"    # NEW: Flag to track if trade was taken near a news event
    context_fingerprint: str = "" # To tie the trade to the statistical memory

@dataclass
class OpenTrade:
    direction: str
    entry: float
    stop: float
    target: float
    entry_bar: Bar
    consensus: ConsensusSignal
    contracts: int = 1         # NEW: Dynamic position size
    news_flag: str = "none"

@dataclass
class PendingTrade:
    direction: str
    limit_price: float
    stop: float
    target: float
    signal_bar: Bar
    consensus: ConsensusSignal
    contracts: int = 1
    expires_at: datetime = None
    last_eval_time: datetime = None

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
    contracts: int = 1         # NEW: Contracts used for this trade
    news_flag: str = "none"
    context_fingerprint: str = ""
