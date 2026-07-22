"""V2.0 — Gate pipeline. Ogni gate logga il motivo del reject:
saprai SEMPRE cosa ha ucciso quanti segnali (analytics anti-overfit)."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from .models import SignalEvent
from .state import SessionState
from .config import Config


@dataclass
class GateResult:
    passed: bool
    reason: str = ""


class NewsCalendar:
    """data/news_calendar.json: {"YYYY-MM-DD": [{"time": "14:00", "impact": "high", "name": "FOMC"}]}"""

    def __init__(self, cfg: Config):
        p = Path(cfg.data_dir) / "news_calendar.json"
        self.events: dict = {}
        if p.exists():
            try:
                self.events = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                self.events = {}
        self.et = ZoneInfo(cfg.session.tz)

    def in_embargo(self, ts: datetime, date_str: str, embargo_min: int) -> bool:
        for ev in self.events.get(date_str, []):
            if ev.get("impact") != "high":
                continue
            h, m = ev["time"].split(":")
            ev_dt = datetime.combine(ts.astimezone(self.et).date(),
                                     time(int(h), int(m)), tzinfo=self.et)
            delta = abs((ts.astimezone(self.et) - ev_dt).total_seconds()) / 60.0
            if delta <= embargo_min:
                return True
        return False


class GatePipeline:
    def __init__(self, cfg: Config, risk, gex_overlay):
        self.cfg = cfg
        self.risk = risk
        self.gex = gex_overlay
        self.news = NewsCalendar(cfg)
        self.reject_stats: dict = {}

    def _reject(self, reason: str) -> GateResult:
        self.reject_stats[reason] = self.reject_stats.get(reason, 0) + 1
        return GateResult(False, reason)

    def check(self, sig: SignalEvent, state: SessionState) -> GateResult:
        c = self.cfg

        # 1) vincoli di rischio prop — PRIMA di tutto (non bypassabili)
        if not self.risk.day_allows_new_trade():
            return self._reject("risk_day_gate")

        # 2) time gates (FABIO: avoid_times, setup_time_cutoff)
        if state.is_lunch(sig.ts_signal):
            return self._reject("lunch_lull")
        et_t = state.et_time(sig.ts_signal)
        if et_t >= time(15, 0):
            return self._reject("after_15pm")
        if c.session.skip_friday and sig.ts_signal.astimezone(state.et).weekday() == 4:
            return self._reject("friday")

        # 3) news embargo (FABIO: no trade attorno a high-impact)
        if self.news.in_embargo(sig.ts_signal, state.day.date, c.session.news_embargo_min):
            return self._reject("news_embargo")

        # 4) min RR strutturale
        if sig.rr1 < c.detection.min_rr:
            return self._reject(f"min_rr({sig.rr1:.2f}<{c.detection.min_rr})")

        # 5) stop distance sana (mai sizing esplosivo — bug R2)
        if not (c.risk.min_stop_points <= sig.risk_points <= c.risk.max_stop_points):
            return self._reject(f"stop_distance({sig.risk_points:.1f}pts)")

        # 6) anti-chase / anti-FOMO: entry troppo lontano dal wall
        if abs(sig.entry_ref - sig.wall_price) > c.detection.max_chase_points:
            return self._reject("chase_too_far")

        # 7) GEX overlay (modificatore — registrato sul segnale)
        adj = self.gex.adjust(sig, state.day)
        if adj.veto:
            return self._reject("gex_veto")
        sig.features["gex_size_mult"] = adj.size_mult
        sig.features["gex_conf_delta"] = adj.conf_delta
        sig.reasons.extend(adj.reasons)

        return GateResult(True)
