"""V2.0 — ExecutionEngine causale.

FIX RISPETTO A v1:
- entry a open(t+1) ± slippage (niente fill retrodatati)
- intrabar_policy='stop_first' di default (conservativa); 'target_first' per sensitivity
- slippage su stop proporzionale al range della barra
- nessun falso target sulla barra di ingresso: la gestione parte dalla barra
  SUCCESSIVA al fill (il fill avviene all'open, tutto il range della barra è post-entry)
- partial 50% a target1 STRUTTURALE (POC/Protection Level — non 1R meccanico)
- BE dopo partial (be_offset copre commissioni)
- trail dietro swing/wall formati DOPO l'entry, solo a favore
- invalidazione strutturale: body close oltre il wall_ref contro → exit al close
- time stop EOD
"""
from __future__ import annotations
from typing import Optional

from .models import Bar, Position, PendingEntry, ClosedTrade, Side, SignalEvent
from .state import SessionState
from .config import Config


class ExecutionEngine:
    def __init__(self, cfg: Config, intrabar_policy: str = "stop_first",
                 slippage_mult: float = 1.0):
        self.cfg = cfg
        assert intrabar_policy in ("stop_first", "target_first")
        self.policy = intrabar_policy
        self.slippage_mult = slippage_mult
        self.pending: Optional[PendingEntry] = None
        self.pos: Optional[Position] = None
        self.closed: list[ClosedTrade] = []

    # ── helpers ─────────────────────────────────────────────────────
    def _slip_ticks(self, kind: str, bar: Optional[Bar] = None) -> float:
        i = self.cfg.instrument
        if kind == "entry":
            return i.slippage_ticks_entry * self.slippage_mult
        if kind == "stop":
            rng_ticks = (bar.range / i.tick_size) if bar else 0.0
            return min(i.slippage_ticks_stop_max,
                       i.slippage_ticks_stop_base + i.slippage_stop_range_coef * rng_ticks
                       ) * self.slippage_mult
        return i.slippage_ticks_market_close * self.slippage_mult

    def _fill_buy(self, price: float, ticks: float) -> float:
        return price + ticks * self.cfg.instrument.tick_size

    def _fill_sell(self, price: float, ticks: float) -> float:
        return price - ticks * self.cfg.instrument.tick_size

    def _mk_close(self, pos: Position, exit_price: float, reason: str,
                  bar: Bar, contracts: float, date: str) -> ClosedTrade:
        i = self.cfg.instrument
        sign = pos.direction.sign
        pnl_points = sign * (exit_price - pos.entry)
        gross = pnl_points / i.tick_size * i.tick_value_usd * contracts
        comm = contracts * i.commission_per_side * 2
        pnl = gross - comm
        risk = abs(pos.entry - pos.stop_initial) if hasattr(pos, "stop_initial") else 1.0
        return ClosedTrade(
            setup=pos.setup, direction=pos.direction, entry=pos.entry,
            exit_price=exit_price, stop_initial=pos.signal.stop, target1=pos.target1,
            contracts=contracts, pnl_usd=round(pnl, 2), pnl_points=round(pnl_points, 2),
            r_multiple=round(pnl_points / risk, 2) if risk > 0 else 0.0,
            exit_reason=reason, ts_entry=pos.ts_entry, ts_exit=bar.ts, date=date,
            confidence=int(pos.signal.features.get("llm_confidence", 0)),
            calibrated_prob=float(pos.signal.features.get("calibrated_prob", 0.0)),
            llm_vote=str(pos.signal.features.get("llm_vote", "na")),
            gex_regime=str(pos.signal.features.get("gex_regime", "unknown")),
            features=pos.signal.features)

    # ── main: chiamato PRIMA di state.update(bar) ───────────────────
    def on_bar(self, bar: Bar, state: SessionState, date: str) -> None:
        i = self.cfg.instrument

        # 1) Fill pending market-on-open: tutto il range della barra è post-entry
        if self.pending is not None and self.pos is None:
            sig = self.pending.signal
            if sig.direction is Side.LONG:
                fill = self._fill_buy(bar.open, self._slip_ticks("entry"))
            else:
                fill = self._fill_sell(bar.open, self._slip_ticks("entry"))
            self.pos = Position(
                direction=sig.direction, entry=fill, stop=sig.stop,
                target1=sig.target1, target2=sig.target2,
                contracts=self.pending.contracts, contracts_open=self.pending.contracts,
                wall_ref=sig.wall_price, setup=sig.setup, ts_entry=bar.ts, signal=sig)
            self.pending = None

        if self.pos is None:
            return

        pos = self.pos
        sign = pos.direction.sign
        tick = i.tick_size

        def stopped_out() -> bool:
            return (bar.low <= pos.stop) if pos.direction is Side.LONG else (bar.high >= pos.stop)

        def do_stop():
            slip = self._slip_ticks("stop", bar)
            fill = self._fill_sell(pos.stop, slip) if pos.direction is Side.LONG \
                else self._fill_buy(pos.stop, slip)
            reason = "trail" if (sign * (pos.stop - pos.entry) > 0) else "stop"
            self.closed.append(self._mk_close(pos, fill, reason, bar, pos.contracts_open, date))
            self.pos = None

        def do_target(px: float, frac: float, reason: str) -> None:
            qty = round(pos.contracts_open * frac, 2) if frac < 1.0 else pos.contracts_open
            qty = min(qty, pos.contracts_open)
            if qty <= 0:
                return
            self.closed.append(self._mk_close(pos, px, reason, bar, qty, date))
            pos.contracts_open = round(pos.contracts_open - qty, 2)
            if frac < 1.0 and pos.contracts_open > 0:
                pos.partial_done = True
                # BE + 1 tick a favore (copre commissioni — FABIO: zero the risk)
                be = pos.entry + sign * 1 * tick
                if sign * (be - pos.stop) > 0:
                    pos.stop = be
                    pos.be_done = True

        def hit(px: float) -> bool:
            return (bar.high >= px) if pos.direction is Side.LONG else (bar.low <= px)

        # 2) Exits — ordine secondo policy
        checks = [("stop", stopped_out, do_stop)]
        t1 = lambda: hit(pos.target1)
        t2 = lambda: pos.target2 and hit(pos.target2)

        if self.policy == "stop_first":
            if stopped_out():
                do_stop()
                return
            if not pos.partial_done and t1():
                do_target(pos.target1, 0.5, "target1_partial")
                if self.pos is None:
                    return
            if pos.target2 and t2():
                do_target(pos.target2, 1.0, "target2")
                self.pos = None
                return
        else:  # target_first (sensitivity)
            if not pos.partial_done and t1():
                do_target(pos.target1, 0.5, "target1_partial")
            if pos.target2 and t2():
                do_target(pos.target2, 1.0, "target2")
                self.pos = None
                return
            if stopped_out():
                do_stop()
                return

        if self.pos is None:
            return

        # 3) Target1 come uscita finale se non c'è target2 e partial già fatto
        if pos.partial_done and pos.target2 is None and hit(pos.target1):
            do_target(pos.target1, 1.0, "target1_final")
            self.pos = None
            return

        # 4) Invalidazione strutturale (FABIO: "must have reason or be out"):
        #    body close oltre il wall di riferimento, contro il trade
        buf = 2 * tick
        if pos.direction is Side.LONG and bar.close < pos.wall_ref - buf and not pos.be_done:
            fill = self._fill_sell(bar.close, self._slip_ticks("close"))
            self.closed.append(self._mk_close(pos, fill, "invalidation", bar, pos.contracts_open, date))
            self.pos = None
            return
        if pos.direction is Side.SHORT and bar.close > pos.wall_ref + buf and not pos.be_done:
            fill = self._fill_buy(bar.close, self._slip_ticks("close"))
            self.closed.append(self._mk_close(pos, fill, "invalidation", bar, pos.contracts_open, date))
            self.pos = None
            return

        # 5) Trailing: dietro swing/wall formati DOPO l'entry, solo a favore
        trail_buf = 4 * tick
        if pos.direction is Side.LONG:
            anchors = [p for p, ts in state.swing_lows if ts > pos.ts_entry]
            anchors += [w.price for w in state.active_walls(side="buy") if w.ts_first > pos.ts_entry]
            if anchors:
                new_stop = max(anchors) - trail_buf
                if new_stop > pos.stop and new_stop < bar.close:
                    pos.stop = new_stop
        else:
            anchors = [p for p, ts in state.swing_highs if ts > pos.ts_entry]
            anchors += [w.price for w in state.active_walls(side="sell") if w.ts_first > pos.ts_entry]
            if anchors:
                new_stop = min(anchors) + trail_buf
                if new_stop < pos.stop and new_stop > bar.close:
                    pos.stop = new_stop

        # 6) Stall exit (FABIO: "struggling auction"): dopo 20 barre senza 0.5R
        #    e CVD che flippa contro → exit al close
        pos.bars_in_trade += 1
        if pos.bars_in_trade >= 20 and not pos.partial_done:
            pnl_points = sign * (bar.close - pos.entry)
            if pnl_points < 0.5 * abs(pos.entry - pos.signal.stop):
                if state.cvd_slope() * sign < 0:
                    fill = self._fill_sell(bar.close, self._slip_ticks("close")) if pos.direction is Side.LONG \
                        else self._fill_buy(bar.close, self._slip_ticks("close"))
                    self.closed.append(self._mk_close(pos, fill, "stall", bar, pos.contracts_open, date))
                    self.pos = None
                    return

        # 7) Time stop EOD
        if state.et_time(bar.ts) >= state._hm(self.cfg.session.eod_flat):
            fill = self._fill_sell(bar.close, self._slip_ticks("close")) if pos.direction is Side.LONG \
                else self._fill_buy(bar.close, self._slip_ticks("close"))
            self.closed.append(self._mk_close(pos, fill, "time_stop", bar, pos.contracts_open, date))
            self.pos = None
            return

    def submit(self, sig: SignalEvent, contracts: float) -> None:
        """Accodato: fill a open(t+1). Un solo trade alla volta (disciplina prop)."""
        if self.pending is None and self.pos is None:
            self.pending = PendingEntry(signal=sig, contracts=contracts)

    def force_eod_close(self, last_bar: Bar, date: str) -> None:
        if self.pos is not None:
            self.closed.append(self._mk_close(self.pos, last_bar.close, "eod",
                                              last_bar, self.pos.contracts_open, date))
            self.pos = None
        self.pending = None
