import json
from pathlib import Path
from datetime import timezone
import pytz
from src import CandidateBar, FabioSignal

ET = pytz.timezone('America/New_York')
STRATEGY_FILE = Path(__file__).parent.parent / 'strategies' / 'fabio_andrea_hybrid.json'

def _load_templates() -> dict:
    try:
        with open(STRATEGY_FILE, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Strategy file not found: {STRATEGY_FILE}") from None
    except json.JSONDecodeError as e:
        raise ValueError(f"Strategy file is invalid JSON ({STRATEGY_FILE}): {e}") from e

def build_fabio_question(candidate: CandidateBar) -> str:
    templates = _load_templates()
    bar = candidate.bar
    ctx = candidate.session_ctx
    t_et = bar.timestamp.astimezone(ET)
    ib_pos = 'above IVB' if bar.close > ctx.ib_high else \
             'below IVB' if bar.close < ctx.ib_low  else 'inside IVB'
    suggested = 'long' if candidate.wall_side == 'ask' else 'short'
    tpl = templates['fabio_nlm_question_template']
    return tpl.format(
        bar_time_et     = t_et.strftime('%H:%M'),
        close           = bar.close,
        ib_high         = ctx.ib_high,
        ib_low          = ctx.ib_low,
        ib_range        = ctx.ib_range,
        poc             = ctx.vp.poc if ctx.vp else 'N/A',
        va_high         = ctx.vp.va_high if ctx.vp else 'N/A',
        va_low          = ctx.vp.va_low if ctx.vp else 'N/A',
        lvn_levels      = str(ctx.vp.lvn_levels if ctx.vp else []),
        lookback        = 3,
        wall_trade_count= candidate.wall_trade_count,
        wall_total_size = sum(t.size for t in bar.big_trades),
        wall_level      = candidate.wall_level,
        wall_side       = candidate.wall_side,
        wall_max_size   = candidate.wall_max_size,
        bar_volume      = bar.volume,
        bar_delta       = bar.delta,
        ib_position     = ib_pos,
        day_type        = ctx.day_type,
        suggested_direction = suggested,
    )

def build_andrea_question(candidate: CandidateBar,
                           fabio_signal: FabioSignal) -> str:
    templates = _load_templates()
    bar = candidate.bar
    ctx = candidate.session_ctx
    t_et = bar.timestamp.astimezone(ET)
    tpl = templates['andrea_nlm_question_template']
    return tpl.format(
        bar_time_et     = t_et.strftime('%H:%M'),
        close           = bar.close,
        open            = bar.open,
        high            = bar.high,
        low             = bar.low,
        ib_high         = ctx.ib_high,
        ib_low          = ctx.ib_low,
        fabio_setup     = fabio_signal.setup_type,
        fabio_direction = fabio_signal.direction,
        fabio_confidence= fabio_signal.confidence,
        wall_level      = candidate.wall_level,
        wall_side       = candidate.wall_side,
        wall_trade_count= candidate.wall_trade_count,
    )
