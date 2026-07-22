"""V2.0 — Data model. SignalEvent valida se stesso: livelli backward = eccezione.
   Elimina alla radice il bug consensus (livelli inventati)."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"

    @property
    def sign(self) -> int:
        return 1 if self is Side.LONG else -1


@dataclass
class TradeTick:
    ts: datetime
    side: str          # 'A' = buy aggressor (lifted ask), 'B' = sell aggressor (hit bid)
    price: float
    size: int


@dataclass
class Bar:
    ts: datetime       # bar OPEN time, tz-aware
    open: float
    high: float
    low: float
    close: float
    volume: int
    buy_volume: int
    sell_volume: int
    delta: int
    footprint: dict = field(default_factory=dict)   # price -> {'bid': int, 'ask': int}
    big_trades: list = field(default_factory=list)  # list[TradeTick] già filtrati

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def body(self) -> float:
        return self.close - self.open

    def wick_top_ratio(self) -> float:
        return (self.high - max(self.open, self.close)) / self.range if self.range > 0 else 0.0

    def wick_bottom_ratio(self) -> float:
        return (min(self.open, self.close) - self.low) / self.range if self.range > 0 else 0.0


@dataclass
class DayContext:
    """Tutto ciò che è noto PRIMA dell'apertura: legale per costruzione."""
    date: str
    prev_poc: Optional[float] = None
    prev_vah: Optional[float] = None
    prev_val: Optional[float] = None
    prev_high: Optional[float] = None
    prev_low: Optional[float] = None
    prev_close: Optional[float] = None
    on_high: Optional[float] = None
    on_low: Optional[float] = None
    atr5: float = 180.0
    gex_regime: str = "unknown"          # 'positive' | 'negative' | 'unknown'
    gex_flip: float = 0.0
    gex_call_wall: float = 0.0
    gex_put_wall: float = 0.0

    def key_levels(self) -> list:
        """Livelli pre-market. Bounded — niente level spam."""
        lv = []
        for name, v in (("prev_poc", self.prev_poc), ("prev_vah", self.prev_vah),
                        ("prev_val", self.prev_val), ("prev_high", self.prev_high),
                        ("prev_low", self.prev_low), ("on_high", self.on_high),
                        ("on_low", self.on_low)):
            if v:
                lv.append((v, name))
        if self.gex_call_wall:
            lv.append((self.gex_call_wall, "gex_call_wall"))
        if self.gex_put_wall:
            lv.append((self.gex_put_wall, "gex_put_wall"))
        if self.gex_flip:
            lv.append((self.gex_flip, "gex_flip"))
        return lv


@dataclass
class SignalEvent:
    setup: str                 # 'failed_auction' | 'ib_second_drive' | 'squeeze_wall' | 'sweep_reclaim'
    direction: Side
    ts_signal: datetime        # close della barra di segnale
    entry_ref: float           # prezzo di riferimento (per RR/chase check)
    stop: float
    target1: float             # target strutturale primario (POC / Protection Level)
    target2: Optional[float]
    wall_price: float          # muro protettivo di riferimento
    wall_size: int
    level_name: str            # livello testato
    features: dict = field(default_factory=dict)
    reasons: list = field(default_factory=list)

    def __post_init__(self):
        if self.direction is Side.LONG:
            if not (self.stop < self.entry_ref):
                raise ValueError(f"LONG backward stop: {self.stop} >= {self.entry_ref}")
            if not (self.target1 > self.entry_ref):
                raise ValueError(f"LONG backward target: {self.target1} <= {self.entry_ref}")
        else:
            if not (self.stop > self.entry_ref):
                raise ValueError(f"SHORT backward stop: {self.stop} >= {self.entry_ref}")
            if not (self.target1 < self.entry_ref):
                raise ValueError(f"SHORT backward target: {self.target1} >= {self.entry_ref}")

    @property
    def risk_points(self) -> float:
        return abs(self.entry_ref - self.stop)

    @property
    def rr1(self) -> float:
        return abs(self.target1 - self.entry_ref) / self.risk_points if self.risk_points > 0 else 0.0


@dataclass
class Position:
    direction: Side
    entry: float
    stop: float
    target1: float
    target2: Optional[float]
    contracts: float
    contracts_open: float
    wall_ref: float
    setup: str
    ts_entry: datetime
    signal: SignalEvent
    partial_done: bool = False
    be_done: bool = False
    bars_in_trade: int = 0
    trail_anchor: float = 0.0


@dataclass
class PendingEntry:
    signal: SignalEvent
    contracts: float
    kind: str = "market_on_open"     # v2 usa solo questo: fill a open(t+1)


@dataclass
class ClosedTrade:
    setup: str
    direction: Side
    entry: float
    exit_price: float
    stop_initial: float
    target1: float
    contracts: float
    pnl_usd: float
    pnl_points: float
    r_multiple: float
    exit_reason: str             # 'stop'|'target1_partial'|'target2'|'trail'|'invalidation'|'stall'|'eod'|'time_stop'
    ts_entry: datetime
    ts_exit: datetime
    date: str
    confidence: int = 0
    calibrated_prob: float = 0.0
    llm_vote: str = "na"
    gex_regime: str = "unknown"
    features: dict = field(default_factory=dict)
