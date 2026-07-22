"""V2.0 — Detector deterministici. Ognuno implementa ESATTAMENTE le condizioni
dei file rule_fabio_*.md verificati. Niente LLM, niente statistiche in-sample.

Ogni detector: on_bar(bar, state) -> SignalEvent | None.
Ricevono solo la barra corrente e lo stato incrementale → causalità garantita.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional

from .models import Bar, SignalEvent, Side
from .state import SessionState
from .config import Config


class FailedAuctionDetector:
    """rule_fabio_failed_auction_is_the_setup + balance_day_exceptions:
    - probe oltre livello (IB edge / prev VAH-VAL / ON H-L) con WICK, no body close fuori
    - big trades SUI WICKS (assorbimento) — benchmark 150+, 300+ = A+
    - effort vs result: delta di segno opposto al risultato della barra
    - participation: >= 3500 (REFINE soft) / 4000 (FABIO)
    - entry al reclaim; stop 1-2 tick oltre l'estremo del wick (stop_placement)
    - target: developing POC (target_selection_hierarchy)
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._cooldown: dict = {}   # level_name -> ts ultimo segnale

    def _levels(self, state: SessionState) -> list:
        lv = []
        if state.ib_complete:
            lv += [(state.ib_high, "ib_high"), (state.ib_low, "ib_low")]
        for name, v in (("prev_vah", state.day.prev_vah), ("prev_val", state.day.prev_val),
                        ("on_high", state.day.on_high), ("on_low", state.day.on_low)):
            if v:
                lv.append((v, name))
        return lv

    def on_bar(self, bar: Bar, state: SessionState) -> Optional[SignalEvent]:
        d = self.cfg.detection
        if not state.is_trade_time(bar.ts) or state.is_lunch(bar.ts):
            return None
        if bar.volume < d.participation_m1_reversal or bar.range <= 0:
            return None

        for level, name in self._levels(state):
            # cooldown per livello: un segnale ogni 15 min
            last = self._cooldown.get(name)
            if last and (bar.ts - last) < timedelta(minutes=15):
                continue

            tick = self.cfg.instrument.tick_size
            buf = 2 * tick

            # SHORT: probe sopra, chiusura sotto, buyers trapped
            if bar.high > level and bar.close < level and bar.wick_top_ratio() >= d.wick_ratio_min:
                big_buy_wick = sum(t.size for t in bar.big_trades
                                   if t.side == "A" and t.price > level - buf)
                # effort vs result: delta >= 0 (sforzo buy) con close < open (risultato giù)
                if big_buy_wick >= d.wall_cluster_min_total and bar.delta >= 0 and bar.close < bar.open:
                    stop = bar.high + buf
                    entry_ref = bar.close
                    target1 = state.rth.poc if state.rth.poc and state.rth.poc < entry_ref else state.vwap
                    if not target1 or target1 >= entry_ref:
                        continue
                    sig = SignalEvent(
                        setup="failed_auction", direction=Side.SHORT, ts_signal=bar.ts,
                        entry_ref=entry_ref, stop=stop, target1=target1, target2=None,
                        wall_price=level, wall_size=big_buy_wick, level_name=name,
                        features={"wick_ratio": bar.wick_top_ratio(), "delta": bar.delta,
                                  "volume": bar.volume, "wall_a_plus": big_buy_wick >= d.wall_a_plus_total},
                        reasons=[f"probe {name} {level:.2f} + wick {bar.wick_top_ratio():.0%} "
                                 f"+ buy wall {big_buy_wick} sui wicks + delta {bar.delta:+d}"])
                    self._cooldown[name] = bar.ts
                    return sig

            # LONG: probe sotto, chiusura sopra, sellers trapped
            if bar.low < level and bar.close > level and bar.wick_bottom_ratio() >= d.wick_ratio_min:
                big_sell_wick = sum(t.size for t in bar.big_trades
                                    if t.side == "B" and t.price < level + buf)
                if big_sell_wick >= d.wall_cluster_min_total and bar.delta <= 0 and bar.close > bar.open:
                    stop = bar.low - buf
                    entry_ref = bar.close
                    target1 = state.rth.poc if state.rth.poc and state.rth.poc > entry_ref else state.vwap
                    if not target1 or target1 <= entry_ref:
                        continue
                    sig = SignalEvent(
                        setup="failed_auction", direction=Side.LONG, ts_signal=bar.ts,
                        entry_ref=entry_ref, stop=stop, target1=target1, target2=None,
                        wall_price=level, wall_size=big_sell_wick, level_name=name,
                        features={"wick_ratio": bar.wick_bottom_ratio(), "delta": bar.delta,
                                  "volume": bar.volume, "wall_a_plus": big_sell_wick >= d.wall_a_plus_total},
                        reasons=[f"probe {name} {level:.2f} + wick {bar.wick_bottom_ratio():.0%} "
                                 f"+ sell wall {big_sell_wick} sui wicks + delta {bar.delta:+d}"])
                    self._cooldown[name] = bar.ts
                    return sig
        return None


class IBSecondDriveDetector:
    """rule_fabio_second_drive + trend_day_second_drive_confirmation + acceptance_definition_exact:
    Macchina a stati per lato:
      IDLE → BREAKOUT (full-body close fuori IB + big trades NEL BODY + delta allineato
                       + volume >= 4000) 
           → RETEST (ritorno sull'edge entro timeout, senza invalidazione)
           → SECOND DRIVE (close oltre l'estremo del drive 1 con delta allineato)
    Mai il primo drive. Stop dietro l'estremo del retest / wall del retest.
    Target: Protection Level = edge ± k × IB range (k stimato WALK-FORWARD su train,
    mai su tutto il dataset — vedi walkforward.py).
    """
    IDLE, BROKE, RETESTED = range(3)

    def __init__(self, cfg: Config, ib_extension_k: float = 1.0):
        self.cfg = cfg
        self.k = ib_extension_k      # STIMATO OUT-OF-SAMPLE. Default prudente 1.0.
        self._reset()

    def _reset(self):
        self.state_up = self.IDLE
        self.state_dn = self.IDLE
        self.drive1_high = 0.0
        self.drive1_low = float("inf")
        self.retest_low = float("inf")
        self.retest_high = 0.0
        self.ts_break: Optional[datetime] = None
        self.retest_wall_size = 0
        self.retest_wall_price = 0.0
        self.fired = False

    def _body_outside(self, bar: Bar, level: float, side: Side) -> bool:
        """full-body close outside: body sostanzialmente oltre il livello."""
        tol = self.cfg.detection.body_tolerance_ticks * self.cfg.instrument.tick_size
        if side is Side.LONG:
            return bar.close > level and min(bar.open, bar.close) > level - tol
        return bar.close < level and max(bar.open, bar.close) < level + tol

    def on_bar(self, bar: Bar, state: SessionState) -> Optional[SignalEvent]:
        d = self.cfg.detection
        if not state.ib_complete or self.fired:
            return None
        if not state.is_trade_time(bar.ts) or state.is_lunch(bar.ts):
            return None

        ib_h, ib_l, ib_r = state.ib_high, state.ib_low, state.ib_range
        if ib_r <= 0:
            return None
        tick = self.cfg.instrument.tick_size

        for side, broke_state in ((Side.LONG, "state_up"), (Side.SHORT, "state_dn")):
            st = getattr(self, broke_state)
            edge = ib_h if side is Side.LONG else ib_l

            if st == self.IDLE:
                if (self._body_outside(bar, edge, side)
                        and bar.volume >= d.participation_m1_trend
                        and bar.delta * side.sign > 0):
                    body_big = sum(t.size for t in bar.big_trades
                                   if min(bar.open, bar.close) <= t.price <= max(bar.open, bar.close)
                                   and (t.side == "A") == (side is Side.LONG))
                    if body_big >= 2 * d.big_trade_min_contracts:  # cluster nel body (FABIO: initiative)
                        setattr(self, broke_state, self.BROKE)
                        self.ts_break = bar.ts
                        if side is Side.LONG:
                            self.drive1_high = bar.high
                        else:
                            self.drive1_low = bar.low

            elif st == self.BROKE:
                # timeout
                if bar.ts - self.ts_break > timedelta(minutes=d.second_drive_timeout_min):
                    setattr(self, broke_state, self.IDLE)
                    continue
                if side is Side.LONG:
                    self.drive1_high = max(self.drive1_high, bar.high)
                    # invalidazione: close sotto meta IB
                    if bar.close < ib_h - 0.5 * ib_r:
                        setattr(self, broke_state, self.IDLE)
                        continue
                    # retest: tocca l'edge dall'alto
                    if bar.low <= ib_h + d.retest_tolerance_ticks * tick:
                        setattr(self, broke_state, self.RETESTED)
                        self.retest_low = bar.low
                        w = self._wall_near(state, ib_h, "buy")
                        self.retest_wall_size = w.size if w else 0
                        self.retest_wall_price = w.price if w else ib_h
                else:
                    self.drive1_low = min(self.drive1_low, bar.low)
                    if bar.close > ib_l + 0.5 * ib_r:
                        setattr(self, broke_state, self.IDLE)
                        continue
                    if bar.high >= ib_l - d.retest_tolerance_ticks * tick:
                        setattr(self, broke_state, self.RETESTED)
                        self.retest_high = bar.high
                        w = self._wall_near(state, ib_l, "sell")
                        self.retest_wall_size = w.size if w else 0
                        self.retest_wall_price = w.price if w else ib_l

            elif st == self.RETESTED:
                if bar.ts - self.ts_break > timedelta(minutes=d.second_drive_timeout_min):
                    setattr(self, broke_state, self.IDLE)
                    continue
                if side is Side.LONG:
                    self.retest_low = min(self.retest_low, bar.low)
                    if bar.close < ib_h - 0.5 * ib_r:
                        setattr(self, broke_state, self.IDLE)
                        continue
                    # SECOND DRIVE: close oltre l'estremo del drive 1, delta allineato
                    if bar.close > self.drive1_high and bar.delta > 0:
                        stop = min(self.retest_low, self.retest_wall_price) - 2 * tick
                        entry_ref = bar.close
                        target1 = entry_ref + self.k * ib_r
                        self.fired = True
                        return SignalEvent(
                            setup="ib_second_drive", direction=Side.LONG, ts_signal=bar.ts,
                            entry_ref=entry_ref, stop=stop, target1=target1,
                            target2=state.day.prev_high,
                            wall_price=self.retest_wall_price, wall_size=self.retest_wall_size,
                            level_name="ib_high",
                            features={"ib_range": ib_r, "retest_wall": self.retest_wall_size,
                                      "cvd_slope": state.cvd_slope(),
                                      "k_ext": self.k},
                            reasons=[f"IB breakout → retest {self.retest_low:.2f} → second drive "
                                     f"close {bar.close:.2f} > drive1 {self.drive1_high:.2f}"])
                else:
                    self.retest_high = max(self.retest_high, bar.high)
                    if bar.close > ib_l + 0.5 * ib_r:
                        setattr(self, broke_state, self.IDLE)
                        continue
                    if bar.close < self.drive1_low and bar.delta < 0:
                        stop = max(self.retest_high, self.retest_wall_price) + 2 * tick
                        entry_ref = bar.close
                        target1 = entry_ref - self.k * ib_r
                        self.fired = True
                        return SignalEvent(
                            setup="ib_second_drive", direction=Side.SHORT, ts_signal=bar.ts,
                            entry_ref=entry_ref, stop=stop, target1=target1,
                            target2=state.day.prev_low,
                            wall_price=self.retest_wall_price, wall_size=self.retest_wall_size,
                            level_name="ib_low",
                            features={"ib_range": ib_r, "retest_wall": self.retest_wall_size,
                                      "cvd_slope": state.cvd_slope(),
                                      "k_ext": self.k},
                            reasons=[f"IB breakout → retest {self.retest_high:.2f} → second drive "
                                     f"close {bar.close:.2f} < drive1 {self.drive1_low:.2f}"])
        return None

    def _wall_near(self, state: SessionState, price: float, side: str):
        tol = self.cfg.detection.wall_merge_tolerance_pts
        best = None
        for w in state.active_walls(side=side):
            if abs(w.price - price) <= tol and (best is None or w.size > best.size):
                best = w
        return best


class SqueezeWallDetector:
    """rule_fabio_squeeze_definition + punches_to_wall + trapped_buyers/sellers:
    - zona trap: cluster big trades aggressivi >= 150 totali entro 2 pts, ultimi 15 min,
      NESSUN progresso oltre il cluster (high effort, zero result)
    - trigger: close rompe il lato opposto della zona trap → liquidazione forzata
    - stop dietro il cluster (1-2 tick), target dev POC
    """

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._fired_zones: list = []

    def on_bar(self, bar: Bar, state: SessionState) -> Optional[SignalEvent]:
        d = self.cfg.detection
        if not state.is_trade_time(bar.ts) or state.is_lunch(bar.ts):
            return None
        tick = self.cfg.instrument.tick_size
        window_start = bar.ts - timedelta(minutes=d.wall_lookback_min)

        recent = [b for b in state.bars if b.ts >= window_start]
        if len(recent) < 5:
            return None

        for trap_side, sig_side in (("A", Side.SHORT), ("B", Side.LONG)):
            bigs = [t for b in recent for t in b.big_trades if t.side == trap_side]
            if not bigs:
                continue
            # cluster entro 2 pts
            bigs.sort(key=lambda t: t.price)
            best_cluster, best_total = None, 0
            i = 0
            while i < len(bigs):
                j = i
                cluster = []
                while j < len(bigs) and bigs[j].price - bigs[i].price <= d.wall_merge_tolerance_pts:
                    cluster.append(bigs[j])
                    j += 1
                tot = sum(t.size for t in cluster)
                if tot > best_total:
                    best_total, best_cluster = tot, cluster
                i = j
            if best_total < d.wall_cluster_min_total or not best_cluster:
                continue

            c_hi = max(t.price for t in best_cluster)
            c_lo = min(t.price for t in best_cluster)
            c_mid = (c_hi + c_lo) / 2
            # dedup zona
            if any(abs(z - c_mid) <= 2 * d.wall_merge_tolerance_pts for z in self._fired_zones):
                continue

            # nessun progresso oltre il cluster = effort senza result
            if trap_side == "A":   # buyers punciano, prezzo non sale
                no_progress = max(b.high for b in recent) <= c_hi + 4 * tick
                trap_floor = min(b.low for b in recent)
                trigger = bar.close < trap_floor - tick
                if no_progress and trigger and bar.delta < 0:
                    stop = c_hi + 2 * tick
                    entry_ref = bar.close
                    target1 = state.rth.poc if state.rth.poc and state.rth.poc < entry_ref else None
                    if not target1:
                        continue
                    self._fired_zones.append(c_mid)
                    return SignalEvent(
                        setup="squeeze_wall", direction=Side.SHORT, ts_signal=bar.ts,
                        entry_ref=entry_ref, stop=stop, target1=target1, target2=None,
                        wall_price=c_hi, wall_size=best_total, level_name="trap_zone",
                        features={"wall_a_plus": best_total >= d.wall_a_plus_total,
                                  "n_punches": len(best_cluster)},
                        reasons=[f"buyers trapped {best_total}ct @ {c_lo:.2f}-{c_hi:.2f}, "
                                 f"break sotto {trap_floor:.2f} → liquidazione"])
            else:                   # sellers punciano, prezzo non scende
                no_progress = min(b.low for b in recent) >= c_lo - 4 * tick
                trap_cap = max(b.high for b in recent)
                trigger = bar.close > trap_cap + tick
                if no_progress and trigger and bar.delta > 0:
                    stop = c_lo - 2 * tick
                    entry_ref = bar.close
                    target1 = state.rth.poc if state.rth.poc and state.rth.poc > entry_ref else None
                    if not target1:
                        continue
                    self._fired_zones.append(c_mid)
                    return SignalEvent(
                        setup="squeeze_wall", direction=Side.LONG, ts_signal=bar.ts,
                        entry_ref=entry_ref, stop=stop, target1=target1, target2=None,
                        wall_price=c_lo, wall_size=best_total, level_name="trap_zone",
                        features={"wall_a_plus": best_total >= d.wall_a_plus_total,
                                  "n_punches": len(best_cluster)},
                        reasons=[f"sellers trapped {best_total}ct @ {c_lo:.2f}-{c_hi:.2f}, "
                                 f"break sopra {trap_cap:.2f} → liquidazione"])
        return None


class SweepReclaimDetector:
    """Stop-hunt / liquidity sweep: violazione di un estremo di sessione o ON H/L
    di pochi tick + reclaim rapido con delta flip. (rule_fabio_entry_mechanics
    'Sweep Wait Protocol' — REFINE, da validare.)"""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._pending: list = []   # {'extreme': float, 'side': Side, 'ts': datetime, 'delta_sweep': int}

    def on_bar(self, bar: Bar, state: SessionState) -> Optional[SignalEvent]:
        d = self.cfg.detection
        if not state.is_trade_time(bar.ts) or state.is_lunch(bar.ts):
            return None
        tick = self.cfg.instrument.tick_size
        max_sweep = d.sweep_max_ticks * tick

        # 1) registra nuovi sweep
        prev_high = max((b.high for b in list(state.bars)[:-1]), default=0.0)
        prev_low = min((b.low for b in list(state.bars)[:-1]), default=float("inf"))
        refs_hi = [x for x in (prev_high, state.day.on_high) if x]
        refs_lo = [x for x in (prev_low, state.day.on_low) if x < float("inf")]

        for ref in refs_hi:
            if ref < bar.high <= ref + max_sweep and bar.close < ref:
                self._pending.append({"extreme": ref, "side": Side.SHORT,
                                      "ts": bar.ts, "bar_low": bar.low})
        for ref in refs_lo:
            if ref - max_sweep <= bar.low < ref and bar.close > ref:
                self._pending.append({"extreme": ref, "side": Side.LONG,
                                      "ts": bar.ts, "bar_high": bar.high})

        # 2) reclaim entro N barre con delta flip
        for p in list(self._pending):
            age = sum(1 for b in state.bars if b.ts > p["ts"])
            if age > d.sweep_reclaim_bars:
                self._pending.remove(p)
                continue
            if age < 1:
                continue
            if p["side"] is Side.SHORT:
                # reclaim: close sotto il minimo della barra di sweep con delta negativo
                if bar.close < p["bar_low"] and bar.delta < 0:
                    self._pending.remove(p)
                    stop = p["extreme"] + 2 * tick
                    entry_ref = bar.close
                    target1 = state.rth.poc if state.rth.poc and state.rth.poc < entry_ref else state.vwap
                    if not target1 or target1 >= entry_ref:
                        continue
                    return SignalEvent(
                        setup="sweep_reclaim", direction=Side.SHORT, ts_signal=bar.ts,
                        entry_ref=entry_ref, stop=stop, target1=target1, target2=None,
                        wall_price=p["extreme"], wall_size=0, level_name="sweep",
                        features={}, reasons=[f"sweep di {p['extreme']:.2f} + reclaim delta flip"])
            else:
                if bar.close > p["bar_high"] and bar.delta > 0:
                    self._pending.remove(p)
                    stop = p["extreme"] - 2 * tick
                    entry_ref = bar.close
                    target1 = state.rth.poc if state.rth.poc and state.rth.poc > entry_ref else state.vwap
                    if not target1 or target1 <= entry_ref:
                        continue
                    return SignalEvent(
                        setup="sweep_reclaim", direction=Side.LONG, ts_signal=bar.ts,
                        entry_ref=entry_ref, stop=stop, target1=target1, target2=None,
                        wall_price=p["extreme"], wall_size=0, level_name="sweep",
                        features={}, reasons=[f"sweep di {p['extreme']:.2f} + reclaim delta flip"])
        return None
