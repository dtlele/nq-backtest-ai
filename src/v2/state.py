"""V2.0 — SessionState incrementale.

INVARIANTE DI CAUSALITÀ: update(bar) è chiamato con barre in ordine
strettamente crescente. Ogni accessor espone SOLO informazione calcolabile
dalle barre già viste. Non esiste alcun riferimento al futuro.

Profile ESATTO dai footprint (niente volume spalmato uniformemente —
era il bug #22: POC spostato al centro del range).
"""
from __future__ import annotations
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from .models import Bar, DayContext, TradeTick
from .config import Config


@dataclass
class Wall:
    price: float
    side: str            # 'buy' | 'sell'  — chi ha piazzato l'aggressione (unificato!)
    size: int
    ts_first: datetime
    ts_last: datetime
    n_punches: int = 1
    status: str = "active"     # active | defended | broken


class ExactProfile:
    """Volume profile esatto da footprint, incrementale."""

    def __init__(self, tick: float):
        self.tick = tick
        self.vol_at_price: dict = {}
        self.total: float = 0.0
        self.poc: float = 0.0
        self.va_high: float = 0.0
        self.va_low: float = 0.0
        self._dirty = False

    def add_bar(self, bar: Bar) -> None:
        fp = bar.footprint
        if fp:
            for p, v in fp.items():
                tot = v.get("bid", 0) + v.get("ask", 0)
                if tot:
                    self.vol_at_price[p] = self.vol_at_price.get(p, 0.0) + tot
                    self.total += tot
        else:
            # fallback dichiarato (loggato dal chiamante una volta)
            p = round(bar.low / self.tick) * self.tick
            n = max(1, round(bar.range / self.tick) + 1)
            per = bar.volume / n
            for _ in range(n):
                k = round(p / self.tick) * self.tick
                self.vol_at_price[k] = self.vol_at_price.get(k, 0.0) + per
                p += self.tick
            self.total += bar.volume
        self._dirty = True

    def refresh(self, va_pct: float = 0.70) -> None:
        if not self._dirty or not self.vol_at_price:
            return
        prices = sorted(self.vol_at_price)
        vols = [self.vol_at_price[p] for p in prices]
        tot = sum(vols)
        if tot <= 0:
            return
        i0 = max(range(len(vols)), key=lambda i: vols[i])
        self.poc = prices[i0]
        acc = vols[i0]
        lo = hi = i0
        while acc / tot < va_pct:
            can_lo = lo > 0
            can_hi = hi < len(vols) - 1
            if not can_lo and not can_hi:
                break
            add_lo = vols[lo - 1] if can_lo else -1
            add_hi = vols[hi + 1] if can_hi else -1
            if add_hi >= add_lo:
                hi += 1
                acc += add_hi
            else:
                lo -= 1
                acc += add_lo
        self.va_high = prices[hi]
        self.va_low = prices[lo]
        self._dirty = False


class SessionState:
    """Un'istanza per giornata. Update barra-per-barra, strettamente causale."""

    def __init__(self, day: DayContext, cfg: Config):
        self.day = day
        self.cfg = cfg
        self.et = ZoneInfo(cfg.session.tz)
        self.tick = cfg.instrument.tick_size

        # Profili: FABIO (vp_includes_overnight) — session VP = SOLO RTH.
        # ON profile tenuto SEPARATO per livelli (on_high/on_low sono in DayContext).
        self.rth = ExactProfile(self.tick)

        # IB (rule_fabio_ib_definition: 30 min default)
        self.ib_high: float = 0.0
        self.ib_low: float = float("inf")
        self.ib_complete: bool = False
        self.ib_breakouts: list = []       # [(ts, 'up'|'down')] — VERE rotture su close

        # VWAP cumulativo
        self._cum_pv = 0.0
        self._cum_v = 0.0
        self.vwap = 0.0

        # Struttura
        self.open_price: Optional[float] = None
        self.session_high = 0.0
        self.session_low = float("inf")
        self.bars: deque = deque(maxlen=390)     # una giornata RTH M1
        self.cvd: int = 0
        self.cvd_hist: deque = deque(maxlen=390)

        # Walls causal registry
        self.walls: list[Wall] = []

        # Swings (frattale k=2, confermato con delay — dichiarato)
        self.swing_highs: deque = deque(maxlen=50)   # (price, ts)
        self.swing_lows: deque = deque(maxlen=50)
        self._recent: deque = deque(maxlen=5)

        self.last_bar: Optional[Bar] = None
        self._fallback_logged = False

    # ── time helpers ────────────────────────────────────────────────
    def _hm(self, s: str) -> time:
        h, m = s.split(":")
        return time(int(h), int(m))

    def et_time(self, ts: datetime) -> time:
        return ts.astimezone(self.et).time()

    def is_trade_time(self, ts: datetime) -> bool:
        t = self.et_time(ts)
        return self._hm(self.cfg.session.trade_start) <= t < self._hm(self.cfg.session.last_entry)

    def is_lunch(self, ts: datetime) -> bool:
        t = self.et_time(ts)
        return self._hm(self.cfg.session.lunch_start) <= t < self._hm(self.cfg.session.lunch_end)

    # ── main update ─────────────────────────────────────────────────
    def update(self, bar: Bar) -> None:
        d = self.cfg.detection
        ts_et_t = self.et_time(bar.ts)

        if self.open_price is None:
            self.open_price = bar.open

        # IB accumulation
        ny_open_t = self._hm(self.cfg.session.ny_open)
        ib_end = (datetime.combine(bar.ts.astimezone(self.et).date(), ny_open_t)
                  + timedelta(minutes=self.cfg.session.ib_duration_min)).time()
        if ny_open_t <= ts_et_t < ib_end:
            self.ib_high = max(self.ib_high, bar.high)
            self.ib_low = min(self.ib_low, bar.low)
        elif not self.ib_complete and ts_et_t >= ib_end and self.ib_high > 0:
            self.ib_complete = True

        # VERO tracking breakout IB (close-based — non day-type flips, bug C4)
        if self.ib_complete:
            if bar.close > self.ib_high:
                if not self.ib_breakouts or self.ib_breakouts[-1][1] != "up":
                    self.ib_breakouts.append((bar.ts, "up"))
            elif bar.close < self.ib_low:
                if not self.ib_breakouts or self.ib_breakouts[-1][1] != "down":
                    self.ib_breakouts.append((bar.ts, "down"))

        # Profilo RTH esatto (FABIO: solo cash session)
        if not bar.footprint and not self._fallback_logged:
            self._fallback_logged = True
            print("  [WARN] footprint mancante: VP in fallback uniforme")
        self.rth.add_bar(bar)
        self.rth.refresh()

        # VWAP
        hlc3 = (bar.high + bar.low + bar.close) / 3.0
        self._cum_pv += hlc3 * bar.volume
        self._cum_v += bar.volume
        self.vwap = self._cum_pv / self._cum_v if self._cum_v else bar.close

        # CVD
        self.cvd += bar.delta
        self.cvd_hist.append(self.cvd)

        # Struttura
        self.session_high = max(self.session_high, bar.high)
        self.session_low = min(self.session_low, bar.low)

        # Walls da big trades (causale: solo trade già avvenuti)
        tol = self.cfg.detection.wall_merge_tolerance_pts
        for t in bar.big_trades:
            side = "buy" if t.side == "A" else "sell"
            merged = False
            for w in self.walls:
                if w.status == "active" and w.side == side and abs(w.price - t.price) <= tol:
                    w.size += t.size
                    w.ts_last = bar.ts
                    w.n_punches += 1
                    merged = True
                    break
            if not merged:
                self.walls.append(Wall(price=t.price, side=side, size=t.size,
                                       ts_first=bar.ts, ts_last=bar.ts))

        # Wall lifecycle: defended/broken su close (causale)
        for w in self.walls:
            if w.status != "active":
                continue
            if w.side == "buy":
                if bar.close < w.price - 2 * self.tick:
                    w.status = "broken"
                elif bar.low <= w.price + self.tick and bar.close >= w.price:
                    w.status = "defended"
            else:
                if bar.close > w.price + 2 * self.tick:
                    w.status = "broken"
                elif bar.high >= w.price - self.tick and bar.close <= w.price:
                    w.status = "defended"

        # Swing fractals k=2 (conferma ritardata di 2 barre — dichiarato)
        self._recent.append(bar)
        if len(self._recent) == 5:
            b = list(self._recent)
            mid = b[2]
            if mid.high > b[0].high and mid.high > b[1].high and mid.high > b[3].high and mid.high > b[4].high:
                self.swing_highs.append((mid.high, mid.ts))
            if mid.low < b[0].low and mid.low < b[1].low and mid.low < b[3].low and mid.low < b[4].low:
                self.swing_lows.append((mid.low, mid.ts))

        self.bars.append(bar)
        self.last_bar = bar

    # ── derived, tutto causale ──────────────────────────────────────
    @property
    def ib_range(self) -> float:
        return self.ib_high - self.ib_low if self.ib_high > 0 and self.ib_low < float("inf") else 0.0

    def gap_points(self) -> Optional[float]:
        if self.day.prev_close is None or self.open_price is None:
            return None
        return self.open_price - self.day.prev_close

    def cvd_slope(self, n: Optional[int] = None) -> float:
        n = n or self.cfg.detection.cvd_slope_bars
        if len(self.cvd_hist) < n + 1:
            return 0.0
        h = list(self.cvd_hist)
        return h[-1] - h[-1 - n]

    def price_range(self, n: int) -> float:
        if len(self.bars) < n:
            return 0.0
        bs = list(self.bars)[-n:]
        return max(b.high for b in bs) - min(b.low for b in bs)

    def active_walls(self, side: Optional[str] = None, min_size: int = 0) -> list:
        return [w for w in self.walls if w.status in ("active", "defended")
                and (side is None or w.side == side) and w.size >= min_size]

    def stacked_imbalances(self, bar: Bar) -> tuple:
        """Stacked imbalances diagonali (buy: ask[p] vs bid[p-tick]).
        Ritorna (buy_stack_prices, sell_stack_prices). AMT standard — i footprint
        esistevano dal giorno 1 e non erano mai stati usati."""
        d = self.cfg.detection
        fp = bar.footprint
        if not fp:
            return [], []
        prices = sorted(fp)
        buy_rows, sell_rows = [], []
        for p in prices:
            ask_v = fp[p].get("ask", 0)
            bid_v = fp[p].get("bid", 0)
            p_dn = round(p - self.tick, 2)
            p_up = round(p + self.tick, 2)
            bid_dn = fp.get(p_dn, {}).get("bid", 0)
            ask_up = fp.get(p_up, {}).get("ask", 0)
            if bid_dn > 0 and ask_v / max(bid_dn, 1) >= d.stacked_imb_ratio:
                buy_rows.append(p)
            if ask_up > 0 and bid_v / max(ask_up, 1) >= d.stacked_imb_ratio:
                sell_rows.append(p)

        def stacks(rows):
            out, run = [], []
            for p in rows:
                if run and abs(p - run[-1] - self.tick) > 1e-9:
                    if len(run) >= d.stacked_imb_min_cells:
                        out.append((run[0], run[-1]))
                    run = []
                run.append(p)
            if len(run) >= d.stacked_imb_min_cells:
                out.append((run[0], run[-1]))
            return out

        return stacks(buy_rows), stacks(sell_rows)

    def key_levels(self) -> list:
        """Bounded: IB + profilo RTH developing + livelli pre-market. ~12 max."""
        lv = []
        if self.ib_complete:
            lv += [(self.ib_high, "ib_high"), (self.ib_low, "ib_low")]
        if self.rth.poc:
            lv += [(self.rth.poc, "dev_poc"), (self.rth.va_high, "dev_vah"),
                   (self.rth.va_low, "dev_val")]
        lv += self.day.key_levels()
        lv.append((self.session_high, "sess_high"))
        lv.append((self.session_low, "sess_low"))
        if self.vwap:
            lv.append((self.vwap, "vwap"))
        return lv
