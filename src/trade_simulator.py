from src import (Bar, ConsensusSignal, OpenTrade, ClosedTrade, PendingTrade,
                 NQ_TICK_SIZE, NQ_TICK_VALUE)
from src.risk_manager import calculate_commissions

def _compute_micro_poc(bars: list) -> float:
    """Compute the POC (price of control) from a list of M1 bars.
    Used for intra-trade dynamic trailing based on live volume profile."""
    if not bars:
        return 0.0
    TICK = 0.25
    price_vol: dict = {}
    for bar in bars:
        p_low  = round(bar.low  / TICK) * TICK
        p_high = round(bar.high / TICK) * TICK
        ticks  = max(1, round((p_high - p_low) / TICK) + 1)
        vol_per_tick = bar.volume / ticks
        price = p_low
        while price <= p_high + 1e-9:
            key = round(price / TICK) * TICK
            price_vol[key] = price_vol.get(key, 0) + vol_per_tick
            price += TICK
    if not price_vol:
        return 0.0
    return max(price_vol, key=price_vol.get)

# We use MNQ as the default instrument for granular position sizing
INSTRUMENT = 'MNQ'
TICK_VALUE = 0.50 # MNQ ($0.50 per tick)

def open_trade(consensus: ConsensusSignal, entry_bar: Bar, contracts: float = 1.0, entry_time = None) -> OpenTrade:
    # ── Execute at Market Close ──
    actual_entry = entry_bar.close
    actual_stop = consensus.stop
    actual_target = consensus.target
    
    if actual_target is None:
        risk_points = abs(actual_entry - actual_stop)
        if consensus.direction == 'long':
            actual_target = actual_entry + (risk_points * 2.0)
        else:
            actual_target = actual_entry - (risk_points * 2.0)
            
    return OpenTrade(
        direction  = consensus.direction,
        entry      = actual_entry,
        stop       = actual_stop,
        target     = actual_target,
        entry_bar  = entry_bar,
        consensus  = consensus,
        contracts  = contracts,
        entry_time = entry_time or entry_bar.timestamp,
        signal_time = entry_bar.timestamp,
        last_eval_time = entry_time or entry_bar.timestamp,
        news_flag  = getattr(consensus, 'news_flag', 'none')
    )

def check_pending_fill(pending: PendingTrade, bar: Bar) -> OpenTrade | None:
    """Checks if a pending limit order is filled by the current bar."""
    if pending.direction == 'long' and bar.low <= pending.limit_price:
        return OpenTrade(
            direction=pending.direction,
            entry=pending.limit_price,
            stop=pending.stop,
            target=pending.target,
            entry_bar=bar,
            consensus=pending.consensus,
            contracts=pending.contracts,
            entry_time=bar.timestamp,
            signal_time=getattr(pending, 'signal_time', bar.timestamp),
            news_flag=getattr(pending.consensus, 'news_flag', 'none')
        )
    elif pending.direction == 'short' and bar.high >= pending.limit_price:
        return OpenTrade(
            direction=pending.direction,
            entry=pending.limit_price,
            stop=pending.stop,
            target=pending.target,
            entry_bar=bar,
            consensus=pending.consensus,
            contracts=pending.contracts,
            entry_time=bar.timestamp,
            signal_time=getattr(pending, 'signal_time', bar.timestamp),
            news_flag=getattr(pending.consensus, 'news_flag', 'none')
        )
    return None

def _close(trade: OpenTrade, exit_price: float,
           exit_reason: str, exit_bar: Bar) -> ClosedTrade:
    sign = 1 if trade.direction == 'long' else -1
    
    # Calculate Gross PnL
    pnl_ticks = sign * (exit_price - trade.entry) / NQ_TICK_SIZE
    gross_pnl_usd = pnl_ticks * TICK_VALUE * trade.contracts
    
    # Calculate Commissions
    commissions = calculate_commissions(trade.contracts, instrument=INSTRUMENT)
    net_pnl_usd = gross_pnl_usd - commissions
    
    closed_t = ClosedTrade(
        direction        = trade.direction,
        entry            = trade.entry,
        stop             = trade.stop,
        target           = trade.target,
        exit_price       = exit_price,
        exit_reason      = exit_reason,
        pnl_ticks        = pnl_ticks,
        pnl_usd          = net_pnl_usd,  # Log Net PnL
        entry_time       = getattr(trade, 'entry_time', trade.entry_bar.timestamp),
        signal_time      = getattr(trade, 'signal_time', None),
        exit_time        = exit_bar.timestamp,
        fabio_reasoning  = trade.consensus.fabio.reasoning,
        andrea_reasoning = trade.consensus.andrea.reasoning,
        setup_type       = trade.consensus.fabio.setup_type,
        final_confidence = trade.consensus.final_confidence,
        r_ratio          = trade.consensus.r_ratio,
        contracts        = trade.contracts, # Log contracts used
        news_flag        = getattr(trade, 'news_flag', 'none'),
        context_fingerprint = getattr(trade.consensus, 'context_fingerprint', ''),
        entry_type       = getattr(trade, 'entry_type', 'market'),
        signal_bar_time  = getattr(trade, 'signal_bar_time', None),
    )
    closed_t.amt_day_profile = getattr(trade, 'amt_day_profile', None)
    closed_t.macro_regime = getattr(trade, 'macro_regime', None)
    closed_t.trapped_info = getattr(trade, 'trapped_info', None)
    closed_t.trapped_follow_through = getattr(trade, 'trapped_follow_through', None)
    return closed_t

def step_trade(trade: OpenTrade, bars: list, first_bar_after_entry: bool = False, on_partial_close = None) -> 'ClosedTrade | None':
    """Walk forward through bars. Return ClosedTrade if exited, else None.
    
    first_bar_after_entry: if True, the first bar in the list is the same M5 bar
    where the entry occurred. In this case, we use a causality-safe check: a stop
    is only triggered if the close confirms the breach (price did not recover),
    preventing false stops when the bar's extreme occurred before our entry time.
    Target hits are still valid (price reaching target after entry is always good).
    
    POC Trailing (Expansive Phase Management):
    Once the trade is in profit by >= 0.5 R:R, we start computing a live micro POC
    from the bars since entry. We trail the stop behind this POC (buffer of 3 ticks).
    If price stalls on the wrong side of the POC for 3+ consecutive M1 bars
    (accumulation/momentum failure), we exit early.
    """
    risk_points = abs(trade.entry - trade.stop)
    # Use OpenTrade's persistent attributes to accumulate state across sequential step_trade calls
    if not hasattr(trade, 'bars_seen') or trade.bars_seen is None:
        trade.bars_seen = []
    if not hasattr(trade, 'bars_stalling_vs_poc') or trade.bars_stalling_vs_poc is None:
        trade.bars_stalling_vs_poc = 0
        
    POC_TRAIL_BUFFER_TICKS = 16 # 16 ticks = 4.0pts below POC for structural protection on NQ
    MAX_STALL_BARS = 5         # exit after 5 consecutive M1 bars stalling under POC
    MIN_RR_FOR_POC_TRAIL = 1.0 # only activate POC trailing once we're 1.0 R:R in profit to prevent premature tight trail
    poc_trail_active = False
    
    for i, bar in enumerate(bars):
        is_first = first_bar_after_entry and (i == 0)
        trade.bars_seen.append(bar)
        
        if trade.direction == 'long':
            # --- 1. Check Partial TP (50% distance / 1.0 R:R) ---
            if not trade.partial_taken and risk_points > 0 and bar.high >= trade.entry + risk_points:
                partial_exit_price = trade.entry + risk_points
                closed_contracts = trade.contracts * 0.5
                orig_contracts = trade.contracts
                trade.contracts = closed_contracts
                partial_closed = _close(trade, partial_exit_price, 'partial_tp', bar)
                trade.contracts = orig_contracts - closed_contracts
                trade.partial_taken = True
                trade.stop = trade.entry  # Move remaining to Break Even!
                if on_partial_close:
                    on_partial_close(partial_closed)
            
            # --- 2. Check Near-TP Trailing (80% distance / 1.6 R:R) ---
            if risk_points > 0 and bar.high >= trade.entry + 1.6 * risk_points:
                lock_in_stop = trade.entry + 1.0 * risk_points
                if lock_in_stop > trade.stop:
                    print(f"  [MANAGEMENT] Near-TP reached (1.6 R:R). Trailing stop to lock in 1.0 R:R: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                    trade.stop = lock_in_stop
                    
            # --- Check High-RR Trailing Tiers ---
            if risk_points > 0:
                if bar.high >= trade.entry + 3.5 * risk_points:
                    lock_in_stop = trade.entry + 2.5 * risk_points
                    if lock_in_stop > trade.stop:
                        print(f"  [MANAGEMENT] 3.5 R:R reached. Trailing stop to lock in 2.5 R:R: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                        trade.stop = lock_in_stop
                elif bar.high >= trade.entry + 2.5 * risk_points:
                    lock_in_stop = trade.entry + 1.5 * risk_points
                    if lock_in_stop > trade.stop:
                        print(f"  [MANAGEMENT] 2.5 R:R reached. Trailing stop to lock in 1.5 R:R: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                        trade.stop = lock_in_stop
            
            # --- 3. Check Target Hit ---
            if bar.high >= trade.target:
                return _close(trade, trade.target, 'target', bar)
            
            # --- 4. POC Trailing / Accumulation Detection (LONG) ---
            if risk_points > 0:
                profit_so_far = bar.close - trade.entry
                if profit_so_far >= MIN_RR_FOR_POC_TRAIL * risk_points and len(trade.bars_seen) >= 3:
                    micro_poc = _compute_micro_poc(trade.bars_seen)
                    if micro_poc > 0:
                        poc_trail_active = True
                        poc_trail_stop = micro_poc - (POC_TRAIL_BUFFER_TICKS * 0.25)
                        # Only move stop UP (never down for a long)
                        if poc_trail_stop > trade.stop and poc_trail_stop < bar.close:
                            print(f"  [POC TRAIL] Micro POC={micro_poc:.2f}. Trailing stop UP: {trade.stop:.2f} -> {poc_trail_stop:.2f}")
                            trade.stop = poc_trail_stop
                        # Stall detection: price closed below the micro POC
                        if bar.close < micro_poc:
                            trade.bars_stalling_vs_poc += 1
                            if trade.bars_stalling_vs_poc >= MAX_STALL_BARS:
                                print(f"  [ACCUMULATION EXIT] Price stalled below POC={micro_poc:.2f} for {MAX_STALL_BARS} bars. Exiting early.")
                                return _close(trade, bar.close, 'poc_accumulation_exit', bar)
                        else:
                            trade.bars_stalling_vs_poc = 0  # reset if price re-crosses above POC
                
            # --- 5. Check Stop Loss Hit ---
            if bar.low <= trade.stop:
                if is_first:
                    if bar.close <= trade.stop:
                        reason = 'trailing_stop' if trade.stop > trade.entry else 'stop'
                        return _close(trade, trade.stop, reason, bar)
                else:
                    reason = 'trailing_stop' if trade.stop > trade.entry else 'stop'
                    return _close(trade, trade.stop, reason, bar)
        else:  # short
            # --- 1. Check Partial TP (50% distance / 1.0 R:R) ---
            if not trade.partial_taken and risk_points > 0 and bar.low <= trade.entry - risk_points:
                partial_exit_price = trade.entry - risk_points
                closed_contracts = trade.contracts * 0.5
                orig_contracts = trade.contracts
                trade.contracts = closed_contracts
                partial_closed = _close(trade, partial_exit_price, 'partial_tp', bar)
                trade.contracts = orig_contracts - closed_contracts
                trade.partial_taken = True
                trade.stop = trade.entry  # Move remaining to Break Even!
                if on_partial_close:
                    on_partial_close(partial_closed)
            
            # --- 2. Check Near-TP Trailing (80% distance / 1.6 R:R) ---
            if risk_points > 0 and bar.low <= trade.entry - 1.6 * risk_points:
                lock_in_stop = trade.entry - 1.0 * risk_points
                if lock_in_stop < trade.stop:
                    print(f"  [MANAGEMENT] Near-TP reached (1.6 R:R). Trailing stop to lock in 1.0 R:R: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                    trade.stop = lock_in_stop
                    
            # --- Check High-RR Trailing Tiers ---
            if risk_points > 0:
                if bar.low <= trade.entry - 3.5 * risk_points:
                    lock_in_stop = trade.entry - 2.5 * risk_points
                    if lock_in_stop < trade.stop:
                        print(f"  [MANAGEMENT] 3.5 R:R reached. Trailing stop to lock in 2.5 R:R: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                        trade.stop = lock_in_stop
                elif bar.low <= trade.entry - 2.5 * risk_points:
                    lock_in_stop = trade.entry - 1.5 * risk_points
                    if lock_in_stop < trade.stop:
                        print(f"  [MANAGEMENT] 2.5 R:R reached. Trailing stop to lock in 1.5 R:R: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                        trade.stop = lock_in_stop
            
            # --- 3. Check Target Hit ---
            if bar.low <= trade.target:
                return _close(trade, trade.target, 'target', bar)
            
            # --- 4. POC Trailing / Accumulation Detection (SHORT) ---
            if risk_points > 0:
                profit_so_far = trade.entry - bar.close
                if profit_so_far >= MIN_RR_FOR_POC_TRAIL * risk_points and len(trade.bars_seen) >= 3:
                    micro_poc = _compute_micro_poc(trade.bars_seen)
                    if micro_poc > 0:
                        poc_trail_active = True
                        poc_trail_stop = micro_poc + (POC_TRAIL_BUFFER_TICKS * 0.25)
                        # Only move stop DOWN (never up for a short)
                        if poc_trail_stop < trade.stop and poc_trail_stop > bar.close:
                            print(f"  [POC TRAIL] Micro POC={micro_poc:.2f}. Trailing stop DOWN: {trade.stop:.2f} -> {poc_trail_stop:.2f}")
                            trade.stop = poc_trail_stop
                        # Stall detection: price closed above micro POC
                        if bar.close > micro_poc:
                            trade.bars_stalling_vs_poc += 1
                            if trade.bars_stalling_vs_poc >= MAX_STALL_BARS:
                                print(f"  [ACCUMULATION EXIT] Price stalled above POC={micro_poc:.2f} for {MAX_STALL_BARS} bars. Exiting early.")
                                return _close(trade, bar.close, 'poc_accumulation_exit', bar)
                        else:
                            trade.bars_stalling_vs_poc = 0
                
            # --- 5. Check Stop Loss Hit ---
            if bar.high >= trade.stop:
                if is_first:
                    if bar.close >= trade.stop:
                        reason = 'trailing_stop' if trade.stop < trade.entry else 'stop'
                        return _close(trade, trade.stop, reason, bar)
                else:
                    reason = 'trailing_stop' if trade.stop < trade.entry else 'stop'
                    return _close(trade, trade.stop, reason, bar)
    return None

def close_eod(trade: OpenTrade, last_bar: Bar) -> ClosedTrade:
    return _close(trade, last_bar.close, 'eod', last_bar)

def close_early(trade: OpenTrade, exit_bar: Bar, reason: str) -> ClosedTrade:
    """Closes an open trade at the current bar's close price (active management exit)."""
    return _close(trade, exit_bar.close, f"early_{reason[:20]}", exit_bar)
