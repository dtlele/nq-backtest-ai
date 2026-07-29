from src import (Bar, ConsensusSignal, OpenTrade, ClosedTrade, PendingTrade,
                 NQ_TICK_SIZE, NQ_TICK_VALUE)
from src.risk_manager import calculate_commissions
import os

def _last_confirmed_swing(bars: list, direction: str, lookback: int = 40, k: int = 3):
    """Ultimo swing CONFERMATO nella finestra (default 40 barre M1).
    Swing low (long): low di una barra che e' il minimo delle k barre prima/dopo.
    Swing high (short): simmetrico. Solo swing confermati (k barre a destra),
    quindi struttura reale — non rumore dell'ultima barra."""
    win = bars[-lookback:]
    swings = []
    for i in range(k, len(win) - k):
        if direction == 'long':
            if all(win[i].low <= win[j].low for j in range(i - k, i + k + 1) if j != i):
                swings.append(win[i].low)
        else:
            if all(win[i].high >= win[j].high for j in range(i - k, i + k + 1) if j != i):
                swings.append(win[i].high)
    return swings[-1] if swings else None


def _donchian_trail_stop(trade, lookback: int = 20, tick: float = 0.25):
    """Trailing stop da range Donchian (stile Turtle): finestra max 40 barre,
    uscita asimmetrica sul canale corto a 20 barre. O(1) per barra — zero LLM.
    Long: minimo delle ultime 20 barre - 1 tick. Short: massimo + 1 tick."""
    bars = (trade.bars_seen or [])[-40:]
    if len(bars) < 5:
        return None
    win = bars[-lookback:] if len(bars) > lookback else bars
    if trade.direction == 'long':
        return min(b.low for b in win) - tick
    return max(b.high for b in win) + tick


def _structural_stop_after_partial(trade, buffer: float = 0.5) -> float:
    """Stop post-partial: MAI semplice breakeven. Dietro l'ultimo swing
    confermato (40-bar window); se lo swing e' sopra l'entry, e' profit locked.
    Fallback BE solo se non esiste ancora struttura."""
    swing = _last_confirmed_swing(trade.bars_seen or [], trade.direction)
    if swing is None:
        return trade.entry
    if trade.direction == 'long':
        return max(trade.entry, swing - buffer)
    return min(trade.entry, swing + buffer)


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
    import os
    sign = 1 if trade.direction == 'long' else -1

    # Realistic slippage (NEW: prod2-yellow, after 4-month audit)
    # Apply 0.5pt slippage against the trade on both entry and exit.
    # Entry: actual_entry = entry +/- 0.5 (we got filled 0.5 worse than ref)
    # Exit: actual_exit = exit_price +/- 0.5 (exit was 0.5 worse than ref)
    # Net slippage per trade: 1pt = 4 ticks = $2 per contract.
    slippage_pts = float(os.environ.get('BACKTEST_SLIPPAGE_PTS', '0.5'))
    if trade.direction == 'long':
        effective_entry = trade.entry + slippage_pts
        effective_exit = exit_price - slippage_pts
    else:
        effective_entry = trade.entry - slippage_pts
        effective_exit = exit_price + slippage_pts

    # Calculate Gross PnL (with slippage)
    pnl_ticks = sign * (effective_exit - effective_entry) / NQ_TICK_SIZE
    gross_pnl_usd = pnl_ticks * TICK_VALUE * trade.contracts

    # Commissions
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
    MAX_STALL_BARS = 9999      # DEPRECATED: non eseguiamo piu' lo stall-exit meccanico.
                                # Era 5 barre consecutive stalling sotto POC. Sostituito da Donchian 40-bar trail.
    MIN_RR_FOR_POC_TRAIL = 1.0 # DEPRECATED: usato dal vecchio POC trail (rimosso). Lasciato per compat.
    poc_trail_active = False
    # === DEPRECATED VECCHI TIER LOCK (rimossi) ===
    # Tutti i lock trailing rigidi (1.6R lock 1R, 2.5R lock 1.5R, 3.5R lock 2.5R)
    # sono stati sostituiti da Donchian 40-bar + swing trail (vedi sezione 4 sotto).
    # Quei lock uccidevano il runner a +1R/+1.5R prima che potesse respirare.
    # I partial TP a 1R restano attivi: gestione rischio sana (50% chiuso, 50% runner).
    ENABLE_VECCHI_TIER_TRAILING = False
    ENABLE_POC_TRAIL = False   # Vecchio POC micro-trail rimosso (vedi Donchian).

    for i, bar in enumerate(bars):
        is_first = first_bar_after_entry and (i == 0)
        trade.bars_seen.append(bar)
        
        if trade.direction == 'long':
            # --- 1. Check Partial TP (50% distance / 1.0 R:R) - DISABLED per default ---
            # V16: partial TP a 1R causa tutti i trade a chiudere a breakeven.
            # Lasciamo correre fino a Donchian trail. Si puo' riattivare con
            # env var ENABLE_PARTIAL_TP=1
            if os.environ.get('ENABLE_PARTIAL_TP', '0') == '1':
                if not trade.partial_taken and risk_points > 0 and bar.high >= trade.entry + risk_points:
                    partial_exit_price = trade.entry + risk_points
                    closed_contracts = trade.contracts * 0.5
                    orig_contracts = trade.contracts
                    trade.contracts = closed_contracts
                    partial_closed = _close(trade, partial_exit_price, 'partial_tp', bar)
                    trade.contracts = orig_contracts - closed_contracts
                    trade.partial_taken = True
                    # Stop STRUTTURALE post-partial (dietro ultimo swing 40-bar),
                    # non semplice BE: il runner deve avere spazio per respirare.
                    trade.stop = _structural_stop_after_partial(trade)
                    if on_partial_close:
                        on_partial_close(partial_closed, trade)
                    on_partial_close(partial_closed)
            
            # --- 2. VECCHI TIER TRAILING (1.6R/2.5R/3.5R) DISABILITATI ---
            # Sostituiti dal Donchian 40-bar + swing trail (sezione 4).
            # I lock rigidi a 1R/1.5R/2.5R uccidevano il runner su ogni pullback.
            if not ENABLE_VECCHI_TIER_TRAILING:
                pass  # Skip the lock — Donchian takes care of it
            else:
                if risk_points > 0 and bar.high >= trade.entry + 1.6 * risk_points:
                    lock_in_stop = trade.entry + 1.0 * risk_points
                    if lock_in_stop > trade.stop:
                        print(f"  [MANAGEMENT] Near-TP reached (1.6 R:R). Trailing stop to lock in 1.0 R:R: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                        trade.stop = lock_in_stop
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
            
            # --- 4. RANGE TRAIL 40-BAR (Donchian) + SWING (LONG) ---
            # Gestione post-partial: il runner segue il minimo a 20 barre del
            # range a 40 (Turtle) combinato con gli swing low confermati.
            # Prende il piu' stretto dei due — mai sopra il prezzo, mai allarga.
            if risk_points > 0 and trade.partial_taken and len(trade.bars_seen) >= 7:
                d_stop = _donchian_trail_stop(trade, lookback=20)
                s_swing = _last_confirmed_swing(trade.bars_seen, 'long')
                swing_stop = (s_swing - 0.5) if s_swing is not None else None
                cands = [s for s in (d_stop, swing_stop) if s is not None]
                if cands:
                    best = max(cands)
                    if best > trade.stop and best < bar.close:
                        print(f"  [RANGE TRAIL] donchian20={d_stop} swing={swing_stop}. Stop UP: {trade.stop:.2f} -> {best:.2f}")
                        trade.stop = best
                
            # --- 5. Check Stop Loss Hit (CLOSE-BASED, no wick-hunting) ---
            # FIX: chiudi SOLO se close M1 < stop, non se solo il wick tocca.
            # Evita 'stop hunt' dove istituzionali spingono sotto stop e poi
            # continuano nella direzione del trade. Vedi analyze_after_stop.py.
            if bar.low <= trade.stop and bar.close <= trade.stop:
                reason = 'trailing_stop' if trade.stop > trade.entry else 'stop'
                return _close(trade, trade.stop, reason, bar)
            elif bar.low <= trade.stop and bar.close > trade.stop:
                # Wick tocca stop ma close sopra = probabile stop hunt, NON chiudere
                print(f'  [STOP WICK] bar.low={bar.low:.2f} <= stop {trade.stop:.2f} ma close={bar.close:.2f} > stop (stop hunt sopravvissuto)')
        else:  # short
            # --- 1. Check Partial TP (50% distance / 1.0 R:R) - DISABLED per default ---
            # V16: partial TP a 1R causa tutti i trade a chiudere a breakeven.
            # Lasciamo correre fino a Donchian trail. Si puo' riattivare con
            # env var ENABLE_PARTIAL_TP=1
            if os.environ.get('ENABLE_PARTIAL_TP', '0') == '1':
                if not trade.partial_taken and risk_points > 0 and bar.low <= trade.entry - risk_points:
                    partial_exit_price = trade.entry - risk_points
                    closed_contracts = trade.contracts * 0.5
                    orig_contracts = trade.contracts
                    trade.contracts = closed_contracts
                    partial_closed = _close(trade, partial_exit_price, 'partial_tp', bar)
                    trade.contracts = orig_contracts - closed_contracts
                    trade.partial_taken = True
                    # Stop STRUTTURALE post-partial (dietro ultimo swing 40-bar)
                    trade.stop = _structural_stop_after_partial(trade)
                if on_partial_close:
                    on_partial_close(partial_closed)
            
            # --- 2. VECCHI TIER TRAILING (1.6R/2.5R/3.5R) DISABILITATI ---
            if not ENABLE_VECCHI_TIER_TRAILING:
                pass  # Skip — Donchian handles trailing
            else:
                if risk_points > 0 and bar.low <= trade.entry - 1.6 * risk_points:
                    lock_in_stop = trade.entry - 1.0 * risk_points
                    if lock_in_stop < trade.stop:
                        print(f"  [MANAGEMENT] Near-TP reached (1.6 R:R). Trailing stop to lock in 1.0 R:R: {trade.stop:.2f} -> {lock_in_stop:.2f}")
                        trade.stop = lock_in_stop
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
            
            # --- 4. RANGE TRAIL 40-BAR (Donchian) + SWING (SHORT) ---
            if risk_points > 0 and trade.partial_taken and len(trade.bars_seen) >= 7:
                d_stop = _donchian_trail_stop(trade, lookback=20)
                s_swing = _last_confirmed_swing(trade.bars_seen, 'short')
                swing_stop = (s_swing + 0.5) if s_swing is not None else None
                cands = [s for s in (d_stop, swing_stop) if s is not None]
                if cands:
                    best = min(cands)
                    if best < trade.stop and best > bar.close:
                        print(f"  [RANGE TRAIL] donchian20={d_stop} swing={swing_stop}. Stop DOWN: {trade.stop:.2f} -> {best:.2f}")
                        trade.stop = best
                
            # --- 5. Check Stop Loss Hit (CLOSE-BASED, no wick-hunting) ---
            # FIX: chiudi SOLO se close M1 > stop, non se solo il wick tocca.
            if bar.high >= trade.stop and bar.close >= trade.stop:
                reason = 'trailing_stop' if trade.stop < trade.entry else 'stop'
                return _close(trade, trade.stop, reason, bar)
            elif bar.high >= trade.stop and bar.close < trade.stop:
                print(f'  [STOP WICK] bar.high={bar.high:.2f} >= stop {trade.stop:.2f} ma close={bar.close:.2f} < stop (stop hunt sopravvissuto)')
    return None

def close_eod(trade: OpenTrade, last_bar: Bar) -> ClosedTrade:
    return _close(trade, last_bar.close, 'eod', last_bar)

def close_early(trade: OpenTrade, exit_bar: Bar, reason: str) -> ClosedTrade:
    """Closes an open trade at the current bar's close price (active management exit)."""
    return _close(trade, exit_bar.close, f"early_{reason[:20]}", exit_bar)
