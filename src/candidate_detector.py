from src import (Bar, SessionContext, CandidateBar, Trade,
                 NQ_BIG_TRADE_THRESHOLD, MIN_VOLUME_PER_BAR,
                 VA_PROXIMITY_TICKS, BIG_TRADE_LOOKBACK_BARS, NQ_TICK_SIZE)
from src.session_context import is_fabio_active

def _near(price: float, level: float, ticks: int) -> bool:
    return abs(price - level) <= ticks * NQ_TICK_SIZE

def _get_vp_levels(ctx: SessionContext) -> list:
    levels = [
        (ctx.ib_high, 'ib_high'),
        (ctx.ib_low,  'ib_low'),
    ]
    if ctx.vp:
        levels += [
            (ctx.vp.poc,      'poc'),
            (ctx.vp.va_high,  'va_high'),
            (ctx.vp.va_low,   'va_low'),
        ]
        for p in ctx.vp.lvn_levels:
            levels.append((p, 'lvn'))
        for p in ctx.vp.hvn_levels:
            levels.append((p, 'hvn'))
    return levels

def detect_candidates(bars: list, ctx: SessionContext) -> list:
    candidates = []
    for i, bar in enumerate(bars):
        if not is_fabio_active(bar):
            continue
        if bar.volume < MIN_VOLUME_PER_BAR:
            continue
        window   = bars[max(0, i - BIG_TRADE_LOOKBACK_BARS + 1): i + 1]
        all_big  = [t for b in window for t in b.big_trades]
        if not all_big:
            continue
        price  = bar.close
        levels = _get_vp_levels(ctx)
        nearby = [(lvl, name) for lvl, name in levels
                  if _near(price, lvl, VA_PROXIMITY_TICKS)]
        if not nearby:
            continue
        nearby.sort(key=lambda x: abs(price - x[0]))
        prox_level, prox_name = nearby[0]
        buy_big  = sum(t.size for t in all_big if t.side == 'A')
        sell_big = sum(t.size for t in all_big if t.side == 'B')
        wall_side  = 'ask' if buy_big >= sell_big else 'bid'
        wall_level = max(window, key=lambda b: sum(t.size for t in b.big_trades)).close
        candidates.append(CandidateBar(
            bar=bar,
            session_ctx=ctx,
            wall_level=wall_level,
            wall_side=wall_side,
            wall_trade_count=len(all_big),
            wall_max_size=max(t.size for t in all_big),
            proximity_to=prox_name,
            proximity_level=prox_level,
            bars_in_session=i,
            is_second_test=False,
        ))
    return candidates
