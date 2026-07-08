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
            
    ot = OpenTrade(
        direction  = consensus.direction,
        entry      = actual_entry,
        stop       = actual_stop,
        target     = actual_target,
        entry_bar  = entry_bar,
        consensus  = consensus,
        contracts  = contracts,
        entry_time = entry_time or entry_bar.timestamp,
        last_eval_time = entry_time or entry_bar.timestamp,
        news_flag  = getattr(consensus, 'news_flag', 'none'),
        initial_stop = actual_stop  # Preserve original structural stop
    )
    return ot

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
            news_flag=getattr(pending.consensus, 'news_flag', 'none'),
            initial_stop=pending.stop
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
            news_flag=getattr(pending.consensus, 'news_flag', 'none'),
            initial_stop=pending.stop
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
    
    # Use the ORIGINAL structural stop for logging (not the current trailing/BE stop)
    logged_stop = getattr(trade, 'initial_stop', None) or trade.stop
    
    closed_t = ClosedTrade(
        direction        = trade.direction,
        entry            = trade.entry,
        stop             = logged_stop,
        target           = trade.target,
        exit_price       = exit_price,
        exit_reason      = exit_reason,
        pnl_ticks        = pnl_ticks,
        pnl_usd          = net_pnl_usd,  # Log Net PnL
        entry_time       = getattr(trade, 'entry_time', trade.entry_bar.timestamp),
        exit_time        = exit_bar.timestamp,
        fabio_reasoning  = trade.consensus.fabio.reasoning,
        andrea_reasoning = trade.consensus.andrea.reasoning,
        setup_type       = trade.consensus.fabio.setup_type,
        final_confidence = trade.consensus.final_confidence,
        r_ratio          = trade.consensus.r_ratio,
        contracts        = trade.contracts, # Log contracts used
        news_flag        = getattr(trade, 'news_flag', 'none'),
        context_fingerprint = getattr(trade.consensus, 'context_fingerprint', '')
    )
    closed_t.amt_day_profile = getattr(trade, 'amt_day_profile', None)
    closed_t.macro_regime = getattr(trade, 'macro_regime', None)
    closed_t.trapped_info = getattr(trade, 'trapped_info', None)
    closed_t.trapped_follow_through = getattr(trade, 'trapped_follow_through', None)
    return closed_t

def step_trade(trade: OpenTrade, bars: list, first_bar_after_entry: bool = False, on_partial_close = None, session_bars: list = None) -> 'ClosedTrade | None':
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
    
    Structural Trailing Stop:
    - Long: Trails 15pt behind dynamic VAL or 15pt behind Big Buy Trades >= 200 size
    - Short: Trails 15pt above dynamic VAH or 15pt above Big Sell Trades >= 200 size
    """
    risk_points = abs(trade.entry - trade.stop)
    # Internal accumulators for POC trailing
    trade_bars_so_far = []     # M1 bars seen since entry
    bars_stalling_vs_poc = 0   # consecutive bars price hasn't re-crossed the POC
    POC_TRAIL_BUFFER_TICKS = 3 # 3 ticks = 0.75pts below POC for long stop
    MAX_STALL_BARS = 15        # exit after 15 consecutive M1 bars stalling under POC
                               # (was 5 — too aggressive, NQ consolidations last 10-15min normally)
    MIN_RR_FOR_POC_TRAIL = 1.0 # only activate POC trailing once we're 1.0 R:R in profit
                               # (was 0.5 — too early, POC too close to entry at that point)
    PARTIAL_TP_RR = 1.5        # take partial at 1.5 R:R (was 1.0 — too early)
    STOP_AFTER_PARTIAL_RR = 0.5 # after partial, lock stop at 0.5R (was 0/BE — gets stopped on retests)
    poc_trail_active = False
    
    for i, bar in enumerate(bars):
        is_first = first_bar_after_entry and (i == 0)
        trade_bars_so_far.append(bar)
        
        # Calculate dynamic VAL/VAH if session_bars is provided
        val = None
        vah = None
        if session_bars:
            bars_up_to_now = [b for b in session_bars if b.timestamp <= bar.timestamp]
            if bars_up_to_now:
                from src.volume_profile import compute_volume_profile
                dyn_vp = compute_volume_profile(bars_up_to_now)
                if dyn_vp:
                    val = dyn_vp.va_low
                    vah = dyn_vp.va_high
        
        if trade.direction == 'long':
            # --- 0. Check Target Hit FIRST (before any partial/trail logic) ---
            # If the same bar hits both target and partial threshold, close 100% at target.
            # Do NOT give up 50% of a winning trade to a partial when the full target is achievable.
            if bar.high >= trade.target:
                return _close(trade, trade.target, 'target', bar)

            # --- 1. Check Partial TP (1.5 R:R) ---
            # Threshold raised from 1.0R to 1.5R: gives trade room to develop before reducing size.
            # Stop after partial: 0.5R (not BE=0R), so a normal retest doesn't stop the remaining half.
            if not trade.partial_taken and risk_points > 0 and bar.high >= trade.entry + PARTIAL_TP_RR * risk_points:
                partial_exit_price = trade.entry + PARTIAL_TP_RR * risk_points
                closed_contracts = trade.contracts * 0.5
                orig_contracts = trade.contracts
                trade.contracts = closed_contracts
                partial_closed = _close(trade, partial_exit_price, 'partial_tp', bar)
                trade.contracts = orig_contracts - closed_contracts
                trade.partial_taken = True
                # Lock stop at 0.5R (not BE) — gives breathing room for retest of entry
                lock_stop = trade.entry + STOP_AFTER_PARTIAL_RR * risk_points
                if lock_stop > trade.stop:
                    print(f"  [PARTIAL TP] 1.5 R:R reached. Closing 50% @ {partial_exit_price:.2f}. Stop locked at 0.5R: {trade.stop:.2f} -> {lock_stop:.2f}")
                    trade.stop = lock_stop
                if on_partial_close:
                    on_partial_close(partial_closed)
            
            # --- 2. Near-TP Trailing (2.0 R:R → lock stop at BE) ---
            # Threshold raised from 1.6R to 2.0R: ensures we've really moved before locking BE
            if risk_points > 0 and bar.high >= trade.entry + 2.0 * risk_points:
                lock_in_stop = trade.entry  # BE
                if lock_in_stop > trade.stop:
                    print(f"  [MANAGEMENT] 2.0 R:R reached. Trailing stop to BE: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                    trade.stop = lock_in_stop
                    
            # --- 3. High-RR Trailing Tiers (wider than before to let runners run) ---
            # Old: 2.5R→1.5R, 3.5R→2.5R
            # New: 3.0R→1.0R, 4.5R→2.5R — gives more room for NQ trend day runners
            if risk_points > 0:
                if bar.high >= trade.entry + 4.5 * risk_points:
                    lock_in_stop = trade.entry + 2.5 * risk_points
                    if lock_in_stop > trade.stop:
                        print(f"  [MANAGEMENT] 4.5 R:R reached. Trailing stop to lock in 2.5 R:R: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                        trade.stop = lock_in_stop
                elif bar.high >= trade.entry + 3.0 * risk_points:
                    lock_in_stop = trade.entry + 1.0 * risk_points
                    if lock_in_stop > trade.stop:
                        print(f"  [MANAGEMENT] 3.0 R:R reached. Trailing stop to lock in 1.0 R:R: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                        trade.stop = lock_in_stop
            
            # --- 4. POC Trailing / Accumulation Detection (LONG) ---
            # Activates only after 1.0 R:R (was 0.5R — too early, POC hugs entry at that point)
            if risk_points > 0:
                profit_so_far = bar.close - trade.entry
                if profit_so_far >= MIN_RR_FOR_POC_TRAIL * risk_points and len(trade_bars_so_far) >= 3:
                    micro_poc = _compute_micro_poc(trade_bars_so_far)
                    if micro_poc > 0:
                        poc_trail_active = True
                        poc_trail_stop = micro_poc - (POC_TRAIL_BUFFER_TICKS * 0.25)
                        # Only move stop UP (never down for a long)
                        if poc_trail_stop > trade.stop and poc_trail_stop < bar.close:
                            print(f"  [POC TRAIL] Micro POC={micro_poc:.2f}. Trailing stop UP: {trade.stop:.2f} -> {poc_trail_stop:.2f}")
                            trade.stop = poc_trail_stop
                        # Stall detection: price closed below the micro POC
                        # Requires 15 bars (was 5) — NQ consolidations are normal and last 10-15min
                        if bar.close < micro_poc:
                            bars_stalling_vs_poc += 1
                            if bars_stalling_vs_poc >= MAX_STALL_BARS:
                                print(f"  [ACCUMULATION EXIT] Price stalled below POC={micro_poc:.2f} for {MAX_STALL_BARS} bars. Exiting early.")
                                return _close(trade, bar.close, 'poc_accumulation_exit', bar)
                        else:
                            bars_stalling_vs_poc = 0  # reset if price re-crosses above POC

            # --- 4.5. Structural Trailing Stop Logic (LONG) ---
            if bar.big_trades:
                buy_trades = [t for t in bar.big_trades if t.side == 'A' and t.size >= 200]
                if buy_trades:
                    max_buy_price = max(t.price for t in buy_trades)
                    new_sl = max_buy_price - 15.0
                    if new_sl > trade.stop and new_sl < bar.close:
                        print(f"  [STRUCTURAL TRAIL] Big Buy Trade wall at {max_buy_price:.2f}. Trailing stop UP: {trade.stop:.2f} -> {new_sl:.2f}")
                        trade.stop = new_sl

            if val is not None:
                new_sl_val = val - 15.0
                if new_sl_val > trade.stop and new_sl_val < bar.close:
                    print(f"  [STRUCTURAL TRAIL] Dynamic VAL at {val:.2f}. Trailing stop UP: {trade.stop:.2f} -> {new_sl_val:.2f}")
                    trade.stop = new_sl_val
                
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
            # --- 0. Check Target Hit FIRST (before any partial/trail logic) ---
            if bar.low <= trade.target:
                return _close(trade, trade.target, 'target', bar)

            # --- 1. Check Partial TP (1.5 R:R) ---
            if not trade.partial_taken and risk_points > 0 and bar.low <= trade.entry - PARTIAL_TP_RR * risk_points:
                partial_exit_price = trade.entry - PARTIAL_TP_RR * risk_points
                closed_contracts = trade.contracts * 0.5
                orig_contracts = trade.contracts
                trade.contracts = closed_contracts
                partial_closed = _close(trade, partial_exit_price, 'partial_tp', bar)
                trade.contracts = orig_contracts - closed_contracts
                trade.partial_taken = True
                # Lock stop at 0.5R below entry (not BE) — gives breathing room for retest
                lock_stop = trade.entry - STOP_AFTER_PARTIAL_RR * risk_points
                if lock_stop < trade.stop:
                    print(f"  [PARTIAL TP] 1.5 R:R reached. Closing 50% @ {partial_exit_price:.2f}. Stop locked at 0.5R: {trade.stop:.2f} -> {lock_stop:.2f}")
                    trade.stop = lock_stop
                if on_partial_close:
                    on_partial_close(partial_closed)
            
            # --- 2. Near-TP Trailing (2.0 R:R → lock stop at BE) ---
            if risk_points > 0 and bar.low <= trade.entry - 2.0 * risk_points:
                lock_in_stop = trade.entry  # BE
                if lock_in_stop < trade.stop:
                    print(f"  [MANAGEMENT] 2.0 R:R reached. Trailing stop to BE: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                    trade.stop = lock_in_stop
                    
            # --- 3. High-RR Trailing Tiers ---
            if risk_points > 0:
                if bar.low <= trade.entry - 4.5 * risk_points:
                    lock_in_stop = trade.entry - 2.5 * risk_points
                    if lock_in_stop < trade.stop:
                        print(f"  [MANAGEMENT] 4.5 R:R reached. Trailing stop to lock in 2.5 R:R: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                        trade.stop = lock_in_stop
                elif bar.low <= trade.entry - 3.0 * risk_points:
                    lock_in_stop = trade.entry - 1.0 * risk_points
                    if lock_in_stop < trade.stop:
                        print(f"  [MANAGEMENT] 3.0 R:R reached. Trailing stop to lock in 1.0 R:R: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                        trade.stop = lock_in_stop
            
            # --- 4. POC Trailing / Accumulation Detection (SHORT) ---
            if risk_points > 0:
                profit_so_far = trade.entry - bar.close
                if profit_so_far >= MIN_RR_FOR_POC_TRAIL * risk_points and len(trade_bars_so_far) >= 3:
                    micro_poc = _compute_micro_poc(trade_bars_so_far)
                    if micro_poc > 0:
                        poc_trail_active = True
                        poc_trail_stop = micro_poc + (POC_TRAIL_BUFFER_TICKS * 0.25)
                        # Only move stop DOWN (never up for a short)
                        if poc_trail_stop < trade.stop and poc_trail_stop > bar.close:
                            print(f"  [POC TRAIL] Micro POC={micro_poc:.2f}. Trailing stop DOWN: {trade.stop:.2f} -> {poc_trail_stop:.2f}")
                            trade.stop = poc_trail_stop
                        # Stall detection: price closed above micro POC
                        if bar.close > micro_poc:
                            bars_stalling_vs_poc += 1
                            if bars_stalling_vs_poc >= MAX_STALL_BARS:
                                print(f"  [ACCUMULATION EXIT] Price stalled above POC={micro_poc:.2f} for {MAX_STALL_BARS} bars. Exiting early.")
                                return _close(trade, bar.close, 'poc_accumulation_exit', bar)
                        else:
                            bars_stalling_vs_poc = 0

            # --- 4.5. Structural Trailing Stop Logic (SHORT) ---
            if bar.big_trades:
                sell_trades = [t for t in bar.big_trades if t.side == 'B' and t.size >= 200]
                if sell_trades:
                    min_sell_price = min(t.price for t in sell_trades)
                    new_sl = min_sell_price + 15.0
                    if new_sl < trade.stop and new_sl > bar.close:
                        print(f"  [STRUCTURAL TRAIL] Big Sell Trade wall at {min_sell_price:.2f}. Trailing stop DOWN: {trade.stop:.2f} -> {new_sl:.2f}")
                        trade.stop = new_sl

            if vah is not None:
                new_sl_vah = vah + 15.0
                if new_sl_vah < trade.stop and new_sl_vah > bar.close:
                    print(f"  [STRUCTURAL TRAIL] Dynamic VAH at {vah:.2f}. Trailing stop DOWN: {trade.stop:.2f} -> {new_sl_vah:.2f}")
                    trade.stop = new_sl_vah
                
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
