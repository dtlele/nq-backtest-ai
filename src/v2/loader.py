"""V2.0 — Data Loader.

Adatta i dati DataBento esistenti all'interfaccia DayContext + Bar richiesta da engine.py.

Usa il pipeline esistente:
  data_loader.load_day()  →  raw tick list
  bar_aggregator.aggregate_to_bars()  →  Bar v1 (con footprint, big_trades, delta)

Poi converte Bar v1 → Bar v2 (stesso contenuto, dataclass diversa).

Interfaccia pubblica:
    loader = DayLoader(trades_dir)
    day_ctx, bars_m1 = loader.load(date_str)

Dipendenze esterne richieste: pandas (già presente nel progetto).
"""
from __future__ import annotations

import glob
import os
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from .models import Bar, DayContext, TradeTick

# ── Import pipeline esistente ──────────────────────────────────────────────
import sys
_BASE = Path(__file__).parent.parent.parent   # nq-backtest-clean/
sys.path.insert(0, str(_BASE))

from src.data_loader import load_day as _load_day_raw
from src.bar_aggregator import aggregate_to_bars as _aggregate


# ── Costanti ───────────────────────────────────────────────────────────────
# RTH: 09:30–16:00 ET = 13:30–20:00 UTC (no DST handling — i dati DataBento
# sono già in UTC, filtriamo su ora UTC)
RTH_START_UTC_H = 13   # 09:30 ET (EST = UTC-5, ma DataBento usa UTC)
RTH_START_UTC_M = 30
RTH_END_UTC_H   = 20
RTH_END_UTC_M   = 0

# Pre-market per DayContext: usa ON (00:00–09:25 ET = 05:00–14:25 UTC)
# per prev_vah/val/poc del giorno precedente
SESSION_WINDOW_START_H = 13   # 09:30 ET

BIG_TRADE_MIN = 30  # FABIO: rule_fabio_big_trades_filter (30 contratti NQ NY)


def _v1_to_v2_bar(b1) -> Bar:
    """Converte Bar v1 (src/__init__.py) → Bar v2 (src/v2/models.py).
    I campi sono identici nel contenuto — solo la dataclass cambia.
    big_trades in v1 sono Trade objects, in v2 diventano TradeTick.
    """
    big_trades_v2 = [
        TradeTick(
            ts=t.ts_event,
            side=t.side,   # 'A' = buy aggressor, 'B' = sell aggressor
            price=t.price,
            size=t.size,
        )
        for t in (b1.big_trades or [])
        if t.size >= BIG_TRADE_MIN   # filtra soglia Fabio (già filtrato in aggregator ma sicurezza)
    ]

    # footprint: {price -> {'bid': int, 'ask': int}} — identico tra v1 e v2
    footprint = b1.footprint if hasattr(b1, 'footprint') else {}

    return Bar(
        ts=b1.timestamp,
        open=float(b1.open),
        high=float(b1.high),
        low=float(b1.low),
        close=float(b1.close),
        volume=int(b1.volume),
        buy_volume=int(b1.buy_volume),
        sell_volume=int(b1.sell_volume),
        delta=int(b1.delta),
        footprint=footprint,
        big_trades=big_trades_v2,
    )


def _filter_rth(bars: list[Bar]) -> list[Bar]:
    """Filtra barre dentro la finestra RTH (09:25–16:05 ET = 13:25–20:05 UTC).
    Lasciamo 5 min di buffer all'apertura per pre-market bar.
    """
    out = []
    for b in bars:
        h, m = b.ts.hour, b.ts.minute
        in_session = (
            (h == RTH_START_UTC_H - 1 and m >= 55) or   # 13:25 UTC = pre-open
            (h == RTH_START_UTC_H and m >= 25) or         # 13:25 UTC
            (RTH_START_UTC_H < h < RTH_END_UTC_H) or
            (h == RTH_END_UTC_H and m <= 5)               # buffer post-close
        )
        if in_session:
            out.append(b)
    return out


def _build_day_context(
    date_str: str,
    prev_bars: Optional[list] = None,
    gex_data: Optional[dict] = None,
    atr5d: float = 180.0,
) -> DayContext:
    """Costruisce DayContext dal giorno precedente (se disponibile).

    - prev_poc/vah/val: da profilo RTH del giorno precedente
    - prev_high/low/close: dai bar RTH del giorno precedente
    - on_high/on_low: da barre overnight (00:00–09:30 ET UTC)
    - GEX: da gex_data se presente, altrimenti fallback
    """
    ctx = DayContext(date=date_str, atr5=atr5d)

    # Dati del giorno precedente
    if prev_bars:
        rth_prev = [b for b in prev_bars if _is_rth(b)]
        if rth_prev:
            ctx.prev_high = max(b.high for b in rth_prev)
            ctx.prev_low  = min(b.low  for b in rth_prev)
            ctx.prev_close = rth_prev[-1].close

            # Volume profile semplice per prev poc/vah/val
            from .state import ExactProfile
            prof = ExactProfile(0.25)
            for b in rth_prev:
                prof.add_bar(b)
            prof.refresh()
            ctx.prev_poc = prof.poc
            ctx.prev_vah = prof.va_high
            ctx.prev_val = prof.va_low

        # ON: barre prima delle 13:30 UTC (= prima delle 09:30 ET)
        on_bars = [b for b in prev_bars if b.ts.hour < RTH_START_UTC_H or
                   (b.ts.hour == RTH_START_UTC_H and b.ts.minute < 25)]
        if on_bars:
            ctx.on_high = max(b.high for b in on_bars)
            ctx.on_low  = min(b.low  for b in on_bars)

    # GEX
    if gex_data:
        ctx.gex_regime    = gex_data.get("gex_regime", "unknown")
        ctx.gex_flip      = float(gex_data.get("zero_gamma_level", 0.0))
        ctx.gex_call_wall = float(gex_data.get("call_wall", 0.0))
        ctx.gex_put_wall  = float(gex_data.get("put_wall", 0.0))

    return ctx


def _is_rth(b: Bar) -> bool:
    h, m = b.ts.hour, b.ts.minute
    return (
        (h == RTH_START_UTC_H and m >= 30) or
        (RTH_START_UTC_H < h < RTH_END_UTC_H) or
        (h == RTH_END_UTC_H and m == 0)
    )


def _load_gex(date_str: str, data_dir: Path) -> Optional[dict]:
    """Carica GEX per la data. Fallback silenzioso se il file non esiste."""
    gex_file = data_dir / "gex_data.json"
    if not gex_file.exists():
        return None
    try:
        all_gex = json.loads(gex_file.read_text(encoding="utf-8"))
        return all_gex.get(date_str)
    except Exception:
        return None


class DayLoader:
    """
    Carica una giornata di dati DataBento e la restituisce come (DayContext, list[Bar]).

    Uso:
        loader = DayLoader(trades_dir="C:/Users/Mauro/Documents/databento-data")
        day_ctx, bars = loader.load("2025-04-30")

        # poi:
        from src.v2.engine import BacktestEngine
        from src.v2.config import Config
        eng = BacktestEngine(Config())
        result = eng.run_day(day_ctx, bars)
    """

    def __init__(self, trades_dir: str, data_dir: str = None):
        self.trades_dir = Path(trades_dir)
        self.data_dir   = Path(data_dir) if data_dir else Path(_BASE) / "data"
        self._cache: dict = {}   # date_str → bars (per prev_day)

    def _find_file(self, date_str: str) -> Optional[Path]:
        """Trova il file .trades.csv per la data (formato DataBento: YYYYMMDD)."""
        compact = date_str.replace("-", "")   # "2025-04-30" → "20250430"
        # Prova vari pattern di nome file DataBento
        patterns = [
            f"*{compact}*.trades.csv",
            f"*{compact}*.csv",
        ]
        for pattern in patterns:
            found = sorted(self.trades_dir.glob(pattern))
            if found:
                return found[0]
        return None

    def _load_bars_for_date(self, date_str: str) -> list[Bar]:
        """Carica e converte le barre per una data. Usa cache in memoria."""
        if date_str in self._cache:
            return self._cache[date_str]

        filepath = self._find_file(date_str)
        if filepath is None:
            return []

        try:
            raw = _load_day_raw(str(filepath))
            if not raw:
                return []
            bars_v1 = _aggregate(raw, freq="1min")
            bars_v2 = [_v1_to_v2_bar(b) for b in bars_v1]
            self._cache[date_str] = bars_v2
            return bars_v2
        except Exception as e:
            print(f"  [LOADER WARN] {date_str}: {e}")
            return []

    def load(self, date_str: str, atr_lookback_days: int = 5) -> tuple[DayContext, list[Bar]]:
        """
        Carica il giorno richiesto.

        Returns:
            (DayContext, bars_rth_m1)
            - DayContext: livelli pre-market + GEX
            - bars_rth_m1: barre 1min RTH (09:25–16:05 ET), ordinate per ts
        """
        # Giorno precedente per livelli pre-market
        dt = date.fromisoformat(date_str)
        prev_date = (dt - timedelta(days=1)).isoformat()
        # Salta weekend (venerdì precedente per lunedì)
        days_back = 1
        while True:
            prev_dt = dt - timedelta(days=days_back)
            if prev_dt.weekday() < 5:   # 0-4 = lun-ven
                prev_date = prev_dt.isoformat()
                break
            days_back += 1

        prev_bars = self._load_bars_for_date(prev_date)

        # ATR5 semplice da ultimi 5 giorni di dati
        atr5 = self._estimate_atr5(dt, atr_lookback_days)

        # GEX (se esiste il file)
        gex = _load_gex(date_str, self.data_dir)

        day_ctx = _build_day_context(date_str, prev_bars, gex, atr5d=atr5)

        # Barre del giorno corrente — RTH only
        today_bars_all = self._load_bars_for_date(date_str)
        bars_rth = _filter_rth(today_bars_all)

        if not bars_rth:
            print(f"  [LOADER WARN] {date_str}: nessuna barra RTH trovata")

        return day_ctx, bars_rth

    def _estimate_atr5(self, dt: date, n: int = 5) -> float:
        """ATR medio degli ultimi n giorni (High-Low giornaliero, media semplice)."""
        atrs = []
        d = dt
        attempts = 0
        while len(atrs) < n and attempts < 20:
            d -= timedelta(days=1)
            attempts += 1
            if d.weekday() >= 5:
                continue
            bars = self._load_bars_for_date(d.isoformat())
            rth = [b for b in bars if _is_rth(b)]
            if rth:
                atrs.append(max(b.high for b in rth) - min(b.low for b in rth))
        return round(sum(atrs) / len(atrs), 1) if atrs else 180.0

    def list_dates(self) -> list[str]:
        """Ritorna lista di date disponibili (ordinate)."""
        files = sorted(self.trades_dir.glob("*.trades.csv"))
        dates = []
        for f in files:
            name = f.name
            # Cerca un pattern YYYYMMDD nel nome
            import re
            m = re.search(r"(\d{8})", name)
            if m:
                raw = m.group(1)
                dates.append(f"{raw[:4]}-{raw[4:6]}-{raw[6:]}")
        return dates
