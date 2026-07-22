"""V2.0 — Configurazione unificata. Ogni parametro dichiara la sua provenienza:
   FABIO    = da file rule_fabio_*.md verificati (trascrizioni)
   REFINE   = da note [Inquiry 2026] / [Methodology Refinement 2026] — ipotesi da validare
   SYSTEM   = scelta ingegneristica/quantitativa, da validare walk-forward
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class InstrumentSpec:
    name: str = "NQ"
    tick_size: float = 0.25
    tick_value_usd: float = 5.0          # NQ: $5/tick ($20/punto). MNQ = 0.50
    commission_per_side: float = 2.50    # SYSTEM: NQ ~$5 round turn
    slippage_ticks_entry: float = 2.0    # SYSTEM: market on open
    slippage_ticks_stop_base: float = 2.0
    slippage_stop_range_coef: float = 0.15   # slippage_stop = base + coef * bar_range_ticks
    slippage_ticks_stop_max: float = 6.0
    slippage_ticks_market_close: float = 1.0
    allow_fractional: bool = True        # SYSTEM: CFD-style; in live futures usare MNQ per granularità


@dataclass(frozen=True)
class SessionSpec:
    tz: str = "America/New_York"
    window_start: str = "09:25"
    ny_open: str = "09:30"
    window_end: str = "16:00"
    ib_duration_min: int = 30            # FABIO: rule_fabio_ib_definition (30 = standard per bias)
    trade_start: str = "09:55"           # FABIO: attende stabilizzazione/IVB quasi completa
    lunch_start: str = "11:30"           # FABIO: rule_fabio_avoid_times "banks are lunching"
    lunch_end: str = "13:30"
    last_entry: str = "15:00"            # FABIO: no new trades PM tardo
    eod_flat: str = "15:45"              # SYSTEM: flat prima del close
    skip_friday: bool = True             # FABIO: rule_fabio_avoid_times (3/4 Fridays in perdita)
    news_embargo_min: int = 5            # FABIO: no trade attorno a NFP/CPI/FOMC


@dataclass(frozen=True)
class RiskSpec:
    """FundedNext 50k — vincoli HARD."""
    account_size: float = 50_000.0
    daily_loss_limit_usd: float = 2_500.0       # vincolo prop
    daily_soft_stop_usd: float = 1_800.0        # SYSTEM: stop operativo al 72%
    max_total_dd_usd: float = 2_500.0           # SYSTEM: trailing da high-water mark
    risk_per_trade_pct: float = 0.0020          # FABIO: 0.25%-0.5% personale; su prop dimezziamo
    max_risk_per_trade_usd: float = 100.0
    max_contracts: float = 5.0                  # SYSTEM: cap assoluto prop 50k
    min_stop_points: float = 8.0                # SYSTEM: sotto = rumore bid/ask, sizing esplode
    max_stop_points: float = 80.0
    max_consecutive_stops: int = 2              # SYSTEM su prop (Fabio: 3-5 su personale)
    max_trades_per_day: int = 4
    house_money_enabled: bool = False           # FABIO (position_building) ma OFF su prop
    house_money_fraction: float = 0.5


@dataclass(frozen=True)
class DetectionSpec:
    big_trade_min_contracts: int = 30        # FABIO: rule_fabio_big_trades_filter (NQ NY)
    wall_cluster_min_total: int = 150        # SYSTEM: wall minimo; 300+ = A+ (FABIO benchmark)
    wall_a_plus_total: int = 300             # FABIO: "perfect example" punches_to_wall
    wall_merge_tolerance_pts: float = 2.0    # SYSTEM
    wall_lookback_min: int = 15              # SYSTEM
    participation_m1_trend: int = 4000       # FABIO: 4k-5k baseline
    participation_m1_reversal: int = 3500    # REFINE: soft threshold failed auction
    wick_ratio_min: float = 0.35             # SYSTEM (usato in tutto il knowledge su wicks)
    retest_tolerance_ticks: int = 8          # SYSTEM
    second_drive_timeout_min: int = 45       # SYSTEM
    body_tolerance_ticks: int = 2            # SYSTEM: "full body close outside"
    min_rr: float = 1.5                      # SYSTEM (Fabio: 1:2.5 preferito — testato in WF)
    max_chase_points: float = 6.0            # SYSTEM: anti-FOMO, entry vicino al wall
    sweep_max_ticks: int = 8                 # SYSTEM
    sweep_reclaim_bars: int = 3              # SYSTEM
    cvd_slope_bars: int = 15                 # SYSTEM
    stacked_imb_ratio: float = 3.0           # AMT standard
    stacked_imb_min_cells: int = 3           # AMT standard


@dataclass(frozen=True)
class GexSpec:
    """GEX = layer quantitativo dichiarato NON-Fabio. Mai fonte di direzione,
    solo modificatore di size/confidenza e livelli aggiuntivi."""
    enabled: bool = True
    data_file: str = "data/gex_data.json"
    counter_regime_size_mult: float = 0.5     # SYSTEM
    counter_regime_wall_override: int = 300   # controtrend ok solo con mega-wall (FABIO benchmark)
    wall_level_proximity_pts: float = 5.0


@dataclass(frozen=True)
class LLMSpec:
    enabled: bool = True
    provider: str = "openrouter"
    model: str = "deepseek/deepseek-chat"
    daily_budget: int = 40
    timeout_s: int = 60
    cache_db: str = "agent_memory/llm_cache_v2.sqlite"
    prompt_version: str = "fabio_v2.0"       # nel cache key → invalidazione esplicita
    min_calibrated_prob: float = 0.50        # SYSTEM: soglia su probabilità calibrata
    veto_only_until_n_trades: int = 80       # sotto N trade loggati, LLM può solo vetare


@dataclass(frozen=True)
class Config:
    instrument: InstrumentSpec = field(default_factory=InstrumentSpec)
    session: SessionSpec = field(default_factory=SessionSpec)
    risk: RiskSpec = field(default_factory=RiskSpec)
    detection: DetectionSpec = field(default_factory=DetectionSpec)
    gex: GexSpec = field(default_factory=GexSpec)
    llm: LLMSpec = field(default_factory=LLMSpec)
    data_dir: str = "data"
    output_dir: str = "output"

    @staticmethod
    def load(path: Optional[str] = None) -> "Config":
        cfg = Config()
        if path and Path(path).exists():
            ov = json.loads(Path(path).read_text(encoding="utf-8"))
            kw = {}
            for section in ("instrument", "session", "risk", "detection", "gex", "llm"):
                base = asdict(getattr(cfg, section))
                base.update(ov.get(section, {}))
                kw[section] = type(getattr(cfg, section))(**base)
            cfg = Config(**kw)
        return cfg
