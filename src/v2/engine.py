"""V2.0 — BacktestEngine single-pass.

ORDINE PER BARRA (invariante causale):
  1. exec.on_bar(bar, state)   → gestione posizioni con stato PRE-barra
  2. state.update(bar)         → stato ora include la barra chiusa
  3. detectors.on_bar()        → segnali su informazione di chiusura barra
  4. gates → llm → risk        → filtri
  5. exec.submit()             → fill a open(t+1)

Non esiste alcun modo, per costruzione, di leggere barre future.
"""
from __future__ import annotations
from dataclasses import dataclass, field

from .models import Bar, DayContext, ClosedTrade
from .state import SessionState
from .detectors import (FailedAuctionDetector, IBSecondDriveDetector,
                        SqueezeWallDetector, SweepReclaimDetector)
from .gates import GatePipeline
from .risk import RiskManager
from .execution import ExecutionEngine
from .gex import GexOverlay
from .config import Config


@dataclass
class DayResult:
    date: str
    trades: list = field(default_factory=list)
    n_signals: int = 0
    reject_stats: dict = field(default_factory=dict)


class BacktestEngine:
    def __init__(self, cfg: Config, llm_policy=None, ib_extension_k: float = 1.0,
                 intrabar_policy: str = "stop_first", slippage_mult: float = 1.0):
        self.cfg = cfg
        self.llm = llm_policy
        self.k = ib_extension_k
        self.risk = RiskManager(cfg)
        self.intrabar_policy = intrabar_policy
        self.slippage_mult = slippage_mult

    def run_day(self, day: DayContext, bars: list) -> DayResult:
        """bars: M1 della finestra [window_start, window_end], ordinate per ts."""
        state = SessionState(day, self.cfg)
        gex_overlay = GexOverlay(self.cfg)
        gates = GatePipeline(self.cfg, self.risk, gex_overlay)
        execu = ExecutionEngine(self.cfg, intrabar_policy=self.intrabar_policy,
                                slippage_mult=self.slippage_mult)
        detectors = [
            IBSecondDriveDetector(self.cfg, ib_extension_k=self.k),
            FailedAuctionDetector(self.cfg),
            SqueezeWallDetector(self.cfg),
            SweepReclaimDetector(self.cfg),
        ]
        self.risk.new_day()
        if self.llm:
            self.llm.new_day()

        res = DayResult(date=day.date)

        for bar in bars:
            execu.on_bar(bar, state, day.date)     # 1) gestione (stato pre-barra)
            state.update(bar)                      # 2) stato += barra chiusa

            if execu.pos is not None or execu.pending is not None:
                continue                           # un trade alla volta

            for det in detectors:                  # 3) detection
                sig = det.on_bar(bar, state)
                if sig is None:
                    continue
                res.n_signals += 1
                sig.features["gex_regime"] = day.gex_regime

                g = gates.check(sig, state)        # 4) gates
                if not g.passed:
                    continue

                if self.llm:                       # 5) voto LLM (opzionale)
                    dec = self.llm.evaluate(sig, state)
                    if not dec["allow"]:
                   	    continue

                rd = self.risk.size(sig)           # 6) sizing con cap
                if not rd.allowed:
                    continue

                execu.submit(sig, rd.contracts)    # 7) fill a open(t+1)
                break                              # max 1 segnale per barra

        if bars:
            execu.force_eod_close(bars[-1], day.date)

        res.trades = list(execu.closed)
        res.reject_stats = dict(gates.reject_stats)
        return res
