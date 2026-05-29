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

        is_reversal = False
        is_momentum = False
        is_pullback = False
        is_imbalance_hunter = False
        
        # In Imbalance State, we actively hunt on every M5 bar (using M1 footprint later in Fabio).
        # We bypass the strict volume floor.
        if m_state == 'imbalance':
            is_imbalance_hunter = True
        else:
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
            if not all_big and not is_imbalance_hunter:
                continue
                
            if all_big:
                wall_max_trade = max(all_big, key=lambda t: t.size)
                wall_level = wall_max_trade.price
                buy_big  = sum(t.size for t in all_big if t.side == 'A')
                sell_big = sum(t.size for t in all_big if t.side == 'B')
                wall_side  = 'ask' if buy_big >= sell_big else 'bid'
            else:
                # Dummy values for imbalance hunter if literally no big trades happened
                wall_level = price
                wall_side = 'none'
                all_big = []
                wall_max_trade = Trade(ts_event=bar.timestamp, side='A', price=price, size=0)

        levels = _get_vp_levels(active_ctx)
        
        # Must be near a structural level (VA or IB edges), EXCEPT if we are hunting in Imbalance
        nearby = [(lvl, name) for lvl, name in levels
                  if _near(price, lvl, VA_PROXIMITY_TICKS)]
        
        if not nearby and not is_imbalance_hunter:
            continue

        if nearby:
            nearby.sort(key=lambda x: abs(price - x[0]))
            prox_level, prox_name = nearby[0]
        else:
            prox_level, prox_name = price, "imbalance_zone"
            
        if is_imbalance_hunter:
            setup_cat = 'imbalance_hunting'
        else:
            setup_cat = 'pullback' if is_pullback else ('momentum' if is_momentum else 'reversal')
        
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
        ))
        
    return candidates

def detect_m1_candidates(m1_bar: Bar, m5_recent: list, ctx: SessionContext, m1_history: list = None) -> list:
    """
    Evaluates a single M1 bar as a candidate when the market is in IMBALANCE state.
    """
    candidates = []
    
    is_imbalance = False
    price = m1_bar.close
    
    # 1. Outside IB (if complete)
    if ctx.ib_complete:
        if price > ctx.ib_high or price < ctx.ib_low:
            is_imbalance = True
            
    # 2. Outside Previous Day Value Area (crucial for first hour moves)
    if ctx.prev_day_vp and not is_imbalance:
        if price > ctx.prev_day_vp.va_high or price < ctx.prev_day_vp.va_low:
            is_imbalance = True
            
    # 3. Outside Overnight Value Area (Fallback if prev day is missing, e.g. Monday)
    if ctx.vp and not is_imbalance:
        if price > ctx.vp.va_high or price < ctx.vp.va_low:
            is_imbalance = True
            
    if not is_imbalance:
        return candidates
        
    # If we are here, we are outside the IB, so generate an IMBALANCE_HUNTING candidate!
    all_big = m1_bar.big_trades
    
    if all_big:
        wall_max_trade = max(all_big, key=lambda t: t.size)
        wall_level = wall_max_trade.price
        buy_big = sum(t.size for t in all_big if t.side == 'A')
        sell_big = sum(t.size for t in all_big if t.side == 'B')
        wall_side = 'ask' if buy_big >= sell_big else 'bid'
    else:
        wall_level = price
        wall_side = 'none'
        wall_max_trade = Trade(ts_event=m1_bar.timestamp, side='A', price=price, size=0)

    # ── LOGICA SENZA REGOLE (Nessun Filtro Volume) ──
    # Passiamo a Fabio qualsiasi candela M1 che si trovi in fase di Imbalance 
    # e che contenga almeno un Big Trade istituzionale. Sarà Fabio (LLM) 
    # a decidere se è un falso segnale o l'inizio di un breakout reale.
    
    if not all_big:
        return candidates

    # Context states
    poc_mig = "flat"
    if ctx.vp and ctx.prev_day_vp:
        if ctx.vp.poc > ctx.prev_day_vp.poc + 4 * NQ_TICK_SIZE:
            poc_mig = "up"
        elif ctx.vp.poc < ctx.prev_day_vp.poc - 4 * NQ_TICK_SIZE:
            poc_mig = "down"

    candidates.append(CandidateBar(
        bar=m1_bar,  # M1 BAR!
        session_ctx=ctx,
        wall_level=wall_level,
        wall_side=wall_side,
        wall_trade_count=len(all_big),
        wall_max_size=wall_max_trade.size,
        proximity_to="imbalance_zone_m1",
        proximity_level=price,
        bars_in_session=len(m5_recent),
        is_second_test=False, 
        setup_category="imbalance_hunting",
        recent_bars=m5_recent,  # Fabio needs M5 structural context here
        market_state="imbalance",
        poc_migration=poc_mig,
        auction_type="initiative",
    ))
    
    return candidates
