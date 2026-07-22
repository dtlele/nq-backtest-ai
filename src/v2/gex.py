"""V2.0 — GEX overlay.

REGOLE DI INGAGGIO (dichiarate SYSTEM, non Fabio):
1. Il GEX non genera MAI direzione. Modifica size e confidence-threshold.
2. Regime negative → continuation favorito; reversal solo con mega-wall (300+).
3. Regime positive → mean-reversion ai wall favorito; breakout richiede acceptance piena.
4. Call/Put wall e flip = livelli strutturali aggiuntivi (già in DayContext).
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path

from .models import SignalEvent, Side, DayContext
from .config import Config


def load_gex(date_str: str, cfg: Config) -> dict:
    p = Path(cfg.gex.data_file)
    if not p.exists():
        return {}
    try:
        all_gex = json.loads(p.read_text(encoding="utf-8"))
        return all_gex.get(date_str, {})
    except Exception:
        return {}


@dataclass
class GexAdjustment:
    size_mult: float = 1.0
    conf_delta: int = 0
    veto: bool = False
    reasons: list = None

    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []


class GexOverlay:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def adjust(self, sig: SignalEvent, day: DayContext) -> GexAdjustment:
        adj = GexAdjustment()
        if not self.cfg.gex.enabled or day.gex_regime not in ("positive", "negative"):
            return adj

        g = self.cfg.gex
        is_continuation = sig.setup in ("ib_second_drive",)
        is_reversal = sig.setup in ("failed_auction", "squeeze_wall", "sweep_reclaim")

        if day.gex_regime == "negative":
            # Dealer amplificano: trend/expansion. Reversal solo con mega-wall.
            if is_reversal and sig.wall_size < g.counter_regime_wall_override:
                adj.size_mult *= g.counter_regime_size_mult
                adj.conf_delta -= 10
                adj.reasons.append(
                    f"GEX negative: reversal size×{g.counter_regime_size_mult} "
                    f"(wall {sig.wall_size} < {g.counter_regime_wall_override} A+ benchmark)")
            if is_continuation:
                adj.conf_delta += 5
                adj.reasons.append("GEX negative: continuation favorito")
        else:
            # Dealer sopprimono: mean reversion. Breakout declassato.
            if is_continuation:
                adj.conf_delta -= 10
                adj.reasons.append("GEX positive: breakout richiede acceptance piena")
            if is_reversal:
                adj.conf_delta += 5
                adj.reasons.append("GEX positive: mean reversion favorito")

        # Vicinanza ai wall opzioni: boost mean-reversion verso l'interno
        for wall, name in ((day.gex_call_wall, "call_wall"), (day.gex_put_wall, "put_wall")):
            if wall and abs(sig.entry_ref - wall) <= g.wall_level_proximity_pts:
                if is_reversal:
                    adj.conf_delta += 5
                    adj.reasons.append(f"Confluenza GEX {name} @ {wall:.2f}")
                else:
                    adj.conf_delta -= 5
                    adj.reasons.append(f"Breakout dentro GEX {name} @ {wall:.2f}: speed bump")

        return adj
