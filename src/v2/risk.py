"""V2.0 — RiskManager. Autorità finale, non consultabile, non bypassabile.
FundedNext 50k: daily soft stop -$1.800, hard limit -$2.500, kill-switch 2 stop,
max 4 trade/giorno, cap contratti, min stop distance (niente sizing esplosivo)."""
from __future__ import annotations
from dataclasses import dataclass

from .models import SignalEvent, ClosedTrade, Side
from .config import Config


@dataclass
class RiskDecision:
    allowed: bool
    contracts: float = 0.0
    reason: str = ""


class RiskManager:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.equity = cfg.risk.account_size
        self.hwm = cfg.risk.account_size
        self.daily_pnl = 0.0
        self.consecutive_stops = 0
        self.trades_today = 0
        self.halted_day = False
        self.halted_total = False

    def new_day(self) -> None:
        self.daily_pnl = 0.0
        self.consecutive_stops = 0
        self.trades_today = 0
        self.halted_day = False

    def day_allows_new_trade(self) -> bool:
        r = self.cfg.risk
        if self.halted_total or self.halted_day:
            return False
        if self.daily_pnl <= -r.daily_soft_stop_usd:
            self.halted_day = True
            return False
        if self.equity <= self.hwm - r.max_total_dd_usd:
            self.halted_total = True
            return False
        if self.consecutive_stops >= r.max_consecutive_stops:
            self.halted_day = True
            return False
        if self.trades_today >= r.max_trades_per_day:
            return False
        return True

    def size(self, sig: SignalEvent) -> RiskDecision:
        r = self.cfg.risk
        inst = self.cfg.instrument
        if not self.day_allows_new_trade():
            return RiskDecision(False, 0.0, "day_gate")

        risk_usd = min(self.equity * r.risk_per_trade_pct, r.max_risk_per_trade_usd)
        # FABIO position_building: rischia i profitti del giorno (OFF di default su prop)
        if r.house_money_enabled and self.daily_pnl > 0:
            risk_usd += self.daily_pnl * r.house_money_fraction
            risk_usd = min(risk_usd, 2 * r.max_risk_per_trade_usd)

        # GEX size modifier
        risk_usd *= sig.features.get("gex_size_mult", 1.0)

        stop_ticks = sig.risk_points / inst.tick_size
        if stop_ticks <= 0:
            return RiskDecision(False, 0.0, "zero_stop")
        contracts = risk_usd / (stop_ticks * inst.tick_value_usd)
        contracts = min(contracts, r.max_contracts)
        if not inst.allow_fractional:
            contracts = float(int(contracts))
        contracts = round(contracts, 2)
        if contracts < (0.1 if inst.allow_fractional else 1.0):
            return RiskDecision(False, 0.0, f"size_too_small({contracts})")

        # hard check: worst case giornaliero non deve avvicinarsi al limite prop
        worst_case = stop_ticks * inst.tick_value_usd * contracts * 1.3  # +slippage
        if self.daily_pnl - worst_case <= -r.daily_loss_limit_usd * 0.95:
            return RiskDecision(False, 0.0, "prop_buffer_breach")

        return RiskDecision(True, contracts, "")

    def on_trade_closed(self, t: ClosedTrade) -> None:
        self.daily_pnl += t.pnl_usd
        self.equity += t.pnl_usd
        self.hwm = max(self.hwm, self.equity)
        self.trades_today += 1
        if t.exit_reason == "stop" and t.pnl_usd < 0:
            self.consecutive_stops += 1
        else:
            self.consecutive_stops = 0
