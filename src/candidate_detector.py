from src import (Bar, SessionContext, CandidateBar, Trade,
                 NQ_BIG_TRADE_THRESHOLD, MIN_VOLUME_PER_BAR, MIN_REVERSAL_VOLUME,
                 VA_PROXIMITY_TICKS, BIG_TRADE_LOOKBACK_BARS, NQ_TICK_SIZE,
                 RECENT_BARS_CONTEXT)
from src.session_context import is_fabio_active

def _near(price: float, level: float, ticks: int) -> bool:
    return abs(price - level) <= ticks * NQ_TICK_SIZE

def _get_vp_levels(ctx: SessionContext) -> list:
    levels = []
    if ctx.ib_complete:
        levels += [(ctx.ib_high, 'ib_high'), (ctx.ib_low, 'ib_low')]
    
    # 1. Overnight Session Volume Profile Levels
    if ctx.vp:
        levels += [
            (ctx.vp.poc,      'overnight_poc'),
            (ctx.vp.va_high,  'overnight_vah'),
            (ctx.vp.va_low,   'overnight_val'),
        ]
        for p in ctx.vp.lvn_levels:
            levels.append((p, 'overnight_lvn'))
        for p in ctx.vp.hvn_levels:
            levels.append((p, 'overnight_hvn'))
            
    # 2. Yesterday's RTH Session Volume Profile Levels
    if ctx.prev_day_vp:
        levels += [
            (ctx.prev_day_vp.poc,      'prev_poc'),
            (ctx.prev_day_vp.va_high,  'prev_vah'),
            (ctx.prev_day_vp.va_low,   'prev_val'),
        ]
        for p in ctx.prev_day_vp.lvn_levels:
            levels.append((p, 'prev_lvn'))
        for p in ctx.prev_day_vp.hvn_levels:
            levels.append((p, 'prev_hvn'))
            
    return levels

import numpy as np

def _check_nav_alert(volumes: list) -> bool:
    if len(volumes) < 6:
        return False
    # Use all volumes except the very last one for baseline to avoid the spike skewing the baseline
    baseline = volumes[:-1]
    mean_vol = np.mean(baseline)
    std_vol = np.std(baseline)
    if std_vol == 0:
        return False
    return volumes[-1] > (mean_vol + 2.33 * std_vol)

def detect_candidates(bars: list, ctx: SessionContext, bars_1min_ny: list = None, bars_1min_overnight: list = None) -> list:
    """
    Identifies institutional triggers based on volume and technical levels.
    Implements a two-tier filter:
    1. Momentum: Volume > 3k (Standard E-mini institutional baseline)
    2. Reversal: Volume > 1.5k (Fading logic, requires absorption)
    3. Pullback: Volume < 1.5k but tests a wall established 1-3 bars ago by a valid institutional bar.
    """
    candidates = []
    
    for i, bar in enumerate(bars):
        # Fabio's Rule: Avoid first 30 mins of NY Open
        if not is_fabio_active(bar):
            continue

        # Dynamic Session Context to prevent lookahead bias + dynamic RTH Volume Profile!
        active_ctx = ctx
        if bars_1min_ny:
            from src.session_context import build_session_context
            from src.volume_profile import compute_volume_profile
            sub_1min = [b for b in bars_1min_ny if b.timestamp <= bar.timestamp]
            if sub_1min:
                from src.volume_profile import compute_vwap
                current_vwap, current_vwap_std = compute_vwap(sub_1min)
                dynamic_vp = ctx.vp # fallback
                try:
                    # Calculate progressive volume profile merging overnight and progressive intraday bars
                    merged_bars = (bars_1min_overnight or []) + sub_1min
                    dynamic_vp = compute_volume_profile(merged_bars)
                except Exception as e:
                    pass
                
                active_ctx = build_session_context(ctx.date, sub_1min, dynamic_vp, prev_day_vp=ctx.prev_day_vp)

        # --- Determine Market State First ---
        price = bar.close
        is_outside_ib = False
        if active_ctx.ib_complete:
            is_outside_ib = (price > active_ctx.ib_high or price < active_ctx.ib_low)
            
        m_state = "imbalance" if is_outside_ib else "balance"
        
        # Calculate NAV Alert for M5
        session_vols = [b.volume for b in bars[:i+1]]
        is_nav_alert = _check_nav_alert(session_vols)

        is_reversal = False
        is_momentum = False
        is_pullback = False
        
        # Check standard volume floor (Balance state sniper)
        if bar.volume >= MIN_VOLUME_PER_BAR:
            is_momentum = True
        elif bar.volume >= MIN_REVERSAL_VOLUME:
            is_reversal = True
        else:
                # PULLBACK RETEST LOGIC:
                for lookback in range(1, 4):
                    prev_idx = i - lookback
                    if prev_idx < 0:
                        break
                    prev_bar = bars[prev_idx]
                    if prev_bar.volume >= MIN_REVERSAL_VOLUME:
                        prev_window = bars[max(0, prev_idx - BIG_TRADE_LOOKBACK_BARS + 1): prev_idx + 1]
                        prev_big = [t for b in prev_window for t in b.big_trades]
                        if prev_big:
                            prev_max_trade = max(prev_big, key=lambda t: t.size)
                            if _near(bar.close, prev_max_trade.price, VA_PROXIMITY_TICKS):
                                is_pullback = True
                                all_big = prev_big
                                wall_max_trade = prev_max_trade
                                wall_level = prev_max_trade.price
                                buy_big = sum(t.size for t in all_big if t.side == 'A')
                                sell_big = sum(t.size for t in all_big if t.side == 'B')
                                wall_side = 'ask' if buy_big >= sell_big else 'bid'
                                break
                if not is_pullback:
                    continue

        # If not pullback, do the standard absorption/big trade checks
        if not is_pullback:
            window   = bars[max(0, i - BIG_TRADE_LOOKBACK_BARS + 1): i + 1]
            all_big  = [t for b in window for t in b.big_trades]
            if not all_big:
                continue
                
            if all_big:
                wall_max_trade = max(all_big, key=lambda t: t.size)
                wall_level = wall_max_trade.price
                buy_big  = sum(t.size for t in all_big if t.side == 'A')
                sell_big = sum(t.size for t in all_big if t.side == 'B')
                wall_side  = 'ask' if buy_big >= sell_big else 'bid'

        levels = _get_vp_levels(active_ctx)
        
        # Must be near a structural level (VA or IB edges)
        nearby = [(lvl, name) for lvl, name in levels
                  if _near(price, lvl, VA_PROXIMITY_TICKS)]
        
        if not nearby:
            continue

        if nearby:
            nearby.sort(key=lambda x: abs(price - x[0]))
            prox_level, prox_name = nearby[0]
            
        setup_cat = 'pullback' if is_pullback else ('momentum' if is_momentum else 'reversal')
            
        # --- SQUEEZE DETECTION ---
        upper_lvls = [lvl for lvl, name in levels if lvl > price]
        lower_lvls = [lvl for lvl, name in levels if lvl < price]
        if upper_lvls and lower_lvls:
            nearest_upper = min(upper_lvls)
            nearest_lower = max(lower_lvls)
            gap = nearest_upper - nearest_lower
            
            # Dynamic Squeeze: Gap is < 30% of IB Range or < 25 pts (if early)
            if (active_ctx.ib_range > 0 and gap < active_ctx.ib_range * 0.3) or (gap < 25.0):
                setup_cat = 'squeeze'
        
        # --- SECOND DRIVE DETECTION ---
        orig_is_second_test = False
        for prev_bar in bars[:i]:
            if (_near(prev_bar.high, prox_level, VA_PROXIMITY_TICKS) or 
                _near(prev_bar.low, prox_level, VA_PROXIMITY_TICKS) or
                _near(prev_bar.close, prox_level, VA_PROXIMITY_TICKS)):
                orig_is_second_test = True
                break

        # --- AUCTION MARKET THEORY (AMT) CALCULATIONS ---
        poc_mig = "flat"
        if active_ctx.vp and active_ctx.prev_day_vp:
            if active_ctx.vp.poc > active_ctx.prev_day_vp.poc + 4 * NQ_TICK_SIZE:
                poc_mig = "up"
            elif active_ctx.vp.poc < active_ctx.prev_day_vp.poc - 4 * NQ_TICK_SIZE:
                poc_mig = "down"

        m_state = "balance"
        if active_ctx.prev_day_vp:
            if not (active_ctx.prev_day_vp.va_low <= price <= active_ctx.prev_day_vp.va_high):
                m_state = "imbalance"

        sess_high = max(b.high for b in bars[:i+1])
        sess_low = min(b.low for b in bars[:i+1])
        auc_type = "responsive"
        if setup_cat == "momentum" or setup_cat == "pullback":
            is_outside_ib = False
            if active_ctx.ib_complete:
                is_outside_ib = (price > active_ctx.ib_high or price < active_ctx.ib_low)
            is_outside_prev_va = False
            if active_ctx.prev_day_vp:
                is_outside_prev_va = (price > active_ctx.prev_day_vp.va_high or price < active_ctx.prev_day_vp.va_low)
            if is_outside_ib or is_outside_prev_va:
                auc_type = "initiative"

        recent = bars[max(0, i - RECENT_BARS_CONTEXT + 1): i + 1]
        
        # Calculate new masterclass metrics
        prev_bar = bars[i-1] if i > 0 else None
        is_delta_div = False
        if prev_bar:
            is_delta_div = (bar.close > prev_bar.close and bar.delta < 0) or (bar.close < prev_bar.close and bar.delta > 0)
            
        is_effort_no_result = False
        session_ranges = [b.high - b.low for b in bars[:i+1]]
        if len(session_vols) >= 3:
            avg_vol = np.mean(session_vols[:-1])
            avg_rng = np.mean(session_ranges[:-1])
            bar_rng = bar.high - bar.low
            if avg_vol > 0 and avg_rng > 0:
                if bar.volume > avg_vol * 1.3 and bar_rng < avg_rng * 0.7:
                    is_effort_no_result = True
                    
        bar_rng = bar.high - bar.low
        if bar_rng > 0:
            t_wick = bar.high - max(bar.open, bar.close)
            b_wick = min(bar.open, bar.close) - bar.low
            t_ratio = t_wick / bar_rng
            b_ratio = b_wick / bar_rng
            c_percentile = (bar.close - bar.low) / bar_rng
        else:
            t_ratio = 0.0
            b_ratio = 0.0
            c_percentile = 0.5

        candidates.append(CandidateBar(
            bar=bar,
            session_ctx=active_ctx,
            wall_level=wall_level,
            wall_side=wall_side,
            wall_trade_count=len(all_big),
            wall_max_size=wall_max_trade.size,
            proximity_to=prox_name,
            proximity_level=prox_level,
            bars_in_session=i,
            is_second_test=orig_is_second_test, 
            setup_category=setup_cat,
            recent_bars=recent,
            market_state=m_state,
            poc_migration=poc_mig,
            auction_type=auc_type,
            vwap=current_vwap if 'current_vwap' in locals() else 0.0,
            vwap_std_dev=current_vwap_std if 'current_vwap_std' in locals() else 0.0,
            nav_alert=is_nav_alert,
            delta_divergence=is_delta_div,
            effort_no_result=is_effort_no_result,
            top_wick_ratio=t_ratio,
            bottom_wick_ratio=b_ratio,
            close_percentile=c_percentile,
        ))
        
    return candidates

def generate_m1_candidate(m1_bar: Bar, m5_recent: list, ctx: SessionContext, m1_history: list = None, override_wall_level: float = None, override_wall_side: str = None) -> CandidateBar:
    """
    Generates a CandidateBar for EVERY single M1 bar. No mechanical filtering (Zero-Waste logic).
    The LLM will decide if the bar contains a valid setup based on the footprint.
    """
    from src.volume_profile import compute_vwap
    all_m1_so_far = (m1_history or []) + [m1_bar]
    current_vwap, current_vwap_std = compute_vwap(all_m1_so_far)
    
    session_vols = [b.volume for b in all_m1_so_far]
    is_nav_alert = _check_nav_alert(session_vols)
    
    if override_wall_level is not None:
        wall_level = override_wall_level
        wall_side = override_wall_side or 'none'
        wall_max_trade = Trade(ts_event=m1_bar.timestamp, side='A', price=wall_level, size=0)
        all_big = []
    else:
        # Find the wall by looking back up to 3 M1 bars
        recent_m1 = all_m1_so_far[-3:]
        all_big = [t for b in recent_m1 for t in b.big_trades]
        if all_big:
            wall_max_trade = max(all_big, key=lambda t: t.size)
            wall_level = wall_max_trade.price
            buy_big = sum(t.size for t in all_big if t.side == 'A')
            sell_big = sum(t.size for t in all_big if t.side == 'B')
            wall_side = 'ask' if buy_big >= sell_big else 'bid'
        else:
            wall_level = m1_bar.close
            wall_side = 'none'
            wall_max_trade = Trade(ts_event=m1_bar.timestamp, side='A', price=m1_bar.close, size=0)
        
    poc_mig = "flat"
    if ctx.vp and ctx.prev_day_vp:
        if ctx.vp.poc > ctx.prev_day_vp.poc + 4 * NQ_TICK_SIZE:
            poc_mig = "up"
        elif ctx.vp.poc < ctx.prev_day_vp.poc - 4 * NQ_TICK_SIZE:
            poc_mig = "down"
            
    is_imbalance = False
    price = m1_bar.close
    if ctx.ib_complete and (price > ctx.ib_high or price < ctx.ib_low):
        is_imbalance = True
        
    # Calculate new masterclass metrics for M1 candidate
    prev_bar = m1_history[-1] if (m1_history and len(m1_history) > 0) else None
    is_delta_div = False
    if prev_bar:
        is_delta_div = (price > prev_bar.close and m1_bar.delta < 0) or (price < prev_bar.close and m1_bar.delta > 0)
        
    is_effort_no_result = False
    session_ranges = [b.high - b.low for b in all_m1_so_far]
    if len(session_vols) >= 3:
        avg_vol = np.mean(session_vols[:-1])
        avg_rng = np.mean(session_ranges[:-1])
        bar_rng = m1_bar.high - m1_bar.low
        if avg_vol > 0 and avg_rng > 0:
            if m1_bar.volume > avg_vol * 1.3 and bar_rng < avg_rng * 0.7:
                is_effort_no_result = True
                
    bar_rng = m1_bar.high - m1_bar.low
    if bar_rng > 0:
        t_wick = m1_bar.high - max(m1_bar.open, m1_bar.close)
        b_wick = min(m1_bar.open, m1_bar.close) - m1_bar.low
        t_ratio = t_wick / bar_rng
        b_ratio = b_wick / bar_rng
        c_percentile = (m1_bar.close - m1_bar.low) / bar_rng
    else:
        t_ratio = 0.0
        b_ratio = 0.0
        c_percentile = 0.5

    return CandidateBar(
        bar=m1_bar,
        session_ctx=ctx,
        wall_level=wall_level,
        wall_side=wall_side,
        wall_trade_count=len(all_big),
        wall_max_size=wall_max_trade.size,
        proximity_to="m1_feed",
        proximity_level=price,
        bars_in_session=len(m5_recent),
        is_second_test=False,
        setup_category="m1_total_feed",
        recent_bars=m5_recent, # Still pass M5 context so LLM sees the macro structure
        market_state="imbalance" if is_imbalance else "balance",
        poc_migration=poc_mig,
        auction_type="initiative" if is_imbalance else "responsive",
        vwap=current_vwap,
        vwap_std_dev=current_vwap_std,
        nav_alert=is_nav_alert,
        delta_divergence=is_delta_div,
        effort_no_result=is_effort_no_result,
        top_wick_ratio=t_ratio,
        bottom_wick_ratio=b_ratio,
        close_percentile=c_percentile,
    )

def detect_m1_candidates(m1_bar, m5_recent: list, ctx: SessionContext, m1_history: list = None) -> list:
    """
    Evaluates a single M1 bar as a candidate.
    Yields a candidate if:
    1. A collision with a Liquidity Wall occurred, resolving an Event X (Defense or Trapped).
    2. OR, the market is in IMBALANCE state and there is a Big Trade.
    """
    candidates = []
    price = m1_bar.close
    
    # 1. LIQUIDITY MAP COLLISION ENGINE
    walls_to_remove = []
    collision_triggered = False
    collision_event = None
    
    for wall in ctx.active_walls:
        if wall.status != 'active':
            continue
            
        # Check if the current bar intersects the wall
        # We also allow proximity sweeps (within 2 ticks) to count as a test
        buffer = 2 * NQ_TICK_SIZE
        if (m1_bar.low - buffer) <= wall.price <= (m1_bar.high + buffer):
            # Collision detected! Evaluate the Close to determine Event X
            
            # Event X1: Absorption / Defense
            if wall.side == 'Buy' and price >= wall.price:
                collision_triggered = True
                collision_event = 'DEFENSE_LONG'
                wall.status = 'defended'
            elif wall.side == 'Sell' and price <= wall.price:
                collision_triggered = True
                collision_event = 'DEFENSE_SHORT'
                wall.status = 'defended'
                
            # Event X2: Trapped Participants (Resa)
            elif wall.side == 'Buy' and price < wall.price - buffer:
                collision_triggered = True
                collision_event = 'TRAPPED_SELL'
                wall.status = 'broken'
                walls_to_remove.append(wall)
            elif wall.side == 'Sell' and price > wall.price + buffer:
                collision_triggered = True
                collision_event = 'TRAPPED_BUY'
                wall.status = 'broken'
                walls_to_remove.append(wall)
                
            if collision_triggered:
                # Assign the active wall for context
                break
                
    # Clean up broken walls
    for w in walls_to_remove:
        if w in ctx.active_walls:
            ctx.active_walls.remove(w)
            
    if collision_triggered:
        cand = generate_m1_candidate(
            m1_bar, m5_recent, ctx, m1_history=m1_history,
            override_wall_level=wall.price,
            override_wall_side=('bid' if wall.side == 'Buy' else 'ask')
        )
        cand.setup_category = f'liquidity_map_{collision_event.lower()}'
        candidates.append(cand)
        return candidates
        
    # 2. NEW LOGIC: Trigger purely on Big Trades, regardless of being inside/outside IB
    # We only pass M1 candidates that contain at least one Big Trade to avoid spam
    if not m1_bar.big_trades:
        return candidates

    cand = generate_m1_candidate(m1_bar, m5_recent, ctx, m1_history=m1_history)
    
    # Override setup_category and proximity_to to match new event-driven format
    cand.setup_category = "big_trade_event"
    cand.proximity_to = "big_trade_node"
    
    candidates.append(cand)
    return candidates

