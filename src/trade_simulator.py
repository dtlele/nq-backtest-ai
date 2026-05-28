from src import (Bar, ConsensusSignal, OpenTrade, ClosedTrade,
                 NQ_TICK_SIZE, NQ_TICK_VALUE)
from src.risk_manager import calculate_commissions

# We use MNQ as the default instrument for granular position sizing
INSTRUMENT = 'MNQ'
TICK_VALUE = 0.50 # MNQ ($0.50 per tick)

def open_trade(consensus: ConsensusSignal, entry_bar: Bar, contracts: int = 1) -> OpenTrade:
    return OpenTrade(
        direction  = consensus.direction,
        entry      = consensus.entry,
        stop       = consensus.stop,
        target     = consensus.target,
        entry_bar  = entry_bar,
        consensus  = consensus,
        contracts  = contracts,  # NEW: Store number of contracts
    )

def _close(trade: OpenTrade, exit_price: float,
           exit_reason: str, exit_bar: Bar) -> ClosedTrade:
    sign = 1 if trade.direction == 'long' else -1
    
    # Calculate Gross PnL
    pnl_ticks = sign * (exit_price - trade.entry) / NQ_TICK_SIZE
    gross_pnl_usd = pnl_ticks * TICK_VALUE * trade.contracts
    
    # Calculate Commissions
    commissions = calculate_commissions(trade.contracts, instrument=INSTRUMENT)
    net_pnl_usd = gross_pnl_usd - commissions
    
    return ClosedTrade(
        direction        = trade.direction,
        entry            = trade.entry,
        stop             = trade.stop,
        target           = trade.target,
        exit_price       = exit_price,
        exit_reason      = exit_reason,
        pnl_ticks        = pnl_ticks,
        pnl_usd          = net_pnl_usd,  # Log Net PnL
        entry_time       = trade.entry_bar.timestamp,
        exit_time        = exit_bar.timestamp,
        fabio_reasoning  = trade.consensus.fabio.reasoning,
        andrea_reasoning = trade.consensus.andrea.reasoning,
        setup_type       = trade.consensus.fabio.setup_type,
        final_confidence = trade.consensus.final_confidence,
        r_ratio          = trade.consensus.r_ratio,
        contracts        = trade.contracts, # Log contracts used
    )

def step_trade(trade: OpenTrade, bars: list, first_bar_after_entry: bool = False) -> 'ClosedTrade | None':
    """Walk forward through bars. Return ClosedTrade if exited, else None.
    
    first_bar_after_entry: if True, the first bar in the list is the same M5 bar
    where the entry occurred. In this case, we use a causality-safe check: a stop
    is only triggered if the close confirms the breach (price did not recover),
    preventing false stops when the bar's extreme occurred before our entry time.
    Target hits are still valid (price reaching target after entry is always good).
    """
    for i, bar in enumerate(bars):
        is_first = first_bar_after_entry and (i == 0)
        
        if trade.direction == 'long':
            if bar.high >= trade.target:
                return _close(trade, trade.target, 'target', bar)
            if bar.low <= trade.stop:
                if is_first:
                    # Causality check: only stop out if close is also below stop
                    # (meaning the adverse move persisted after our entry)
                    if bar.close <= trade.stop:
                        return _close(trade, trade.stop, 'stop', bar)
                    # else: low touched stop but price recovered — not a real stop
                else:
                    return _close(trade, trade.stop, 'stop', bar)
        else:  # short
            if bar.low <= trade.target:
                return _close(trade, trade.target, 'target', bar)
            if bar.high >= trade.stop:
                if is_first:
                    # Causality check: only stop out if close is also above stop
                    if bar.close >= trade.stop:
                        return _close(trade, trade.stop, 'stop', bar)
                    # else: high touched stop but price recovered — not a real stop
                else:
                    return _close(trade, trade.stop, 'stop', bar)
    return None

def close_eod(trade: OpenTrade, last_bar: Bar) -> ClosedTrade:
    return _close(trade, last_bar.close, 'eod', last_bar)

def close_early(trade: OpenTrade, exit_bar: Bar, reason: str) -> ClosedTrade:
    """Closes an open trade at the current bar's close price (active management exit)."""
    return _close(trade, exit_bar.close, f"early_{reason[:20]}", exit_bar)
