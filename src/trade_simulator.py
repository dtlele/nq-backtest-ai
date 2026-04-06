from src import (Bar, ConsensusSignal, OpenTrade, ClosedTrade,
                 NQ_TICK_SIZE, NQ_TICK_VALUE)

def open_trade(consensus: ConsensusSignal, entry_bar: Bar) -> OpenTrade:
    return OpenTrade(
        direction  = consensus.direction,
        entry      = consensus.entry,
        stop       = consensus.stop,
        target     = consensus.target,
        entry_bar  = entry_bar,
        consensus  = consensus,
    )

def _close(trade: OpenTrade, exit_price: float,
           exit_reason: str, exit_bar: Bar) -> ClosedTrade:
    sign = 1 if trade.direction == 'long' else -1
    pnl_ticks = sign * (exit_price - trade.entry) / NQ_TICK_SIZE
    pnl_usd   = pnl_ticks * NQ_TICK_VALUE
    # r_ratio stores the PLANNED R from consensus (target distance / stop distance)
    # Realized R can be derived from pnl_ticks and (entry - stop) / tick_size
    return ClosedTrade(
        direction        = trade.direction,
        entry            = trade.entry,
        stop             = trade.stop,
        target           = trade.target,
        exit_price       = exit_price,
        exit_reason      = exit_reason,
        pnl_ticks        = pnl_ticks,
        pnl_usd          = pnl_usd,
        entry_time       = trade.entry_bar.timestamp,
        exit_time        = exit_bar.timestamp,
        fabio_reasoning  = trade.consensus.fabio.reasoning,
        andrea_reasoning = trade.consensus.andrea.reasoning,
        setup_type       = trade.consensus.fabio.setup_type,
        final_confidence = trade.consensus.final_confidence,
        r_ratio          = trade.consensus.r_ratio,
    )

def step_trade(trade: OpenTrade, bars: list) -> 'ClosedTrade | None':
    """Walk forward through bars. Return ClosedTrade if exited, else None.

    Tie-breaking: if a single bar touches both target and stop, target is
    awarded (optimistic convention). Conservative alternative would award stop.
    """
    for bar in bars:
        if trade.direction == 'long':
            if bar.high >= trade.target:
                return _close(trade, trade.target, 'target', bar)
            if bar.low <= trade.stop:
                return _close(trade, trade.stop, 'stop', bar)
        else:  # short
            if bar.low <= trade.target:
                return _close(trade, trade.target, 'target', bar)
            if bar.high >= trade.stop:
                return _close(trade, trade.stop, 'stop', bar)
    return None

def close_eod(trade: OpenTrade, last_bar: Bar) -> ClosedTrade:
    return _close(trade, last_bar.close, 'eod', last_bar)
