from src import (FabioSignal, AndreaSignal, ConsensusSignal,
                 FABIO_MIN_CONFIDENCE, ANDREA_VETO_THRESHOLD)

def build_consensus(fabio: FabioSignal, andrea: AndreaSignal) -> ConsensusSignal:
    # Gate 1: Fabio confidence
    if fabio.confidence < FABIO_MIN_CONFIDENCE or fabio.direction == 'none':
        if fabio.confidence < FABIO_MIN_CONFIDENCE:
            reason = f'fabio_below_threshold ({fabio.confidence} < {FABIO_MIN_CONFIDENCE})'
        else:
            reason = 'fabio_direction_none'
        return ConsensusSignal(
            direction='none', entry=0, stop=0, target=0,
            r_ratio=0, final_confidence=fabio.confidence,
            fabio=fabio, andrea=andrea,
            decision='no_trade',
            no_trade_reason=reason,
        )
    # Gate 2: Andrea veto (Disabled!)
    # if andrea.confidence < ANDREA_VETO_THRESHOLD or not andrea.confirmation:
    #     return ConsensusSignal(
    #         direction='none', entry=0, stop=0, target=0,
    #         r_ratio=0, final_confidence=andrea.confidence,
    #         fabio=fabio, andrea=andrea,
    #         decision='no_trade',
    #         no_trade_reason=f'andrea_veto (confirmation={andrea.confirmation}, conf={andrea.confidence})',
    #     )

    # Trade approved
    boost = 1.1 if andrea.confirmation else 1.0
    final_conf = min(100, int(fabio.confidence * boost))
    
    # Gate 3: Final confidence check
    if final_conf < FABIO_MIN_CONFIDENCE:
        return ConsensusSignal(
            direction='none', entry=0, stop=0, target=0,
            r_ratio=0, final_confidence=final_conf,
            fabio=fabio, andrea=andrea,
            decision='no_trade',
            no_trade_reason=f'final_conf_below_threshold ({final_conf} < {FABIO_MIN_CONFIDENCE})',
        )
        
    # Ensure entry, stop, and target are not None
    entry  = fabio.entry if fabio.entry is not None else 0.0
    stop   = fabio.stop if fabio.stop is not None else (entry - 10.0 if fabio.direction == 'long' else entry + 10.0)
    target = fabio.target if fabio.target is not None else (entry + 20.0 if fabio.direction == 'long' else entry - 20.0)

    
    # ── Andrea Structural Stop Override ──
    if andrea.structural_stop is not None:
        try:
            andrea_stop = float(andrea.structural_stop)
            # Calculate risk with Fabio's stop vs. Andrea's stop
            fabio_risk = abs(entry - fabio.stop) if fabio.stop is not None else 0.0
            andrea_risk = abs(entry - andrea_stop)
            
            # Target reward points
            reward = abs(target - entry)
            
            # Calculate Reward-to-Risk ratios
            fabio_rr = reward / fabio_risk if fabio_risk > 0 else 0.0
            andrea_rr = reward / andrea_risk if andrea_risk > 0 else 0.0
            
            should_override = False
            if fabio.direction == 'long' and andrea_stop < entry:
                # Andrea wants a wider stop (lower)
                # Only override if Fabio's stop is too tight (< 10 pts) and Andrea's stop still offers R:R >= 1.0,
                # OR if Andrea's stop is actually tighter (less risk) than Fabio's stop
                if fabio_risk < 10.0 and andrea_rr >= 1.0:
                    should_override = True
                elif andrea_stop > fabio.stop:
                    should_override = True
            elif fabio.direction == 'short' and andrea_stop > entry:
                # Andrea wants a wider stop (higher)
                if fabio_risk < 10.0 and andrea_rr >= 1.0:
                    should_override = True
                elif andrea_stop < fabio.stop:
                    should_override = True
                    
            if should_override:
                stop = andrea_stop
                print(f"  [CONSENSUS] Overriding stop with Andrea's Structural SL: {stop} (was {fabio.stop})")
            else:
                print(f"  [CONSENSUS] Keeping Fabio's protected stop {fabio.stop} (R:R {fabio_rr:.2f}) over Andrea's wider stop {andrea_stop} (R:R {andrea_rr:.2f})")
        except (ValueError, TypeError):
            pass

    risk   = abs(entry - stop)
    if fabio.direction == 'long':
        reward = target - entry
    else:
        reward = entry - target

    # Gate 4: Backward target / stop validation (Adjust instead of reject)
    if fabio.direction == 'long':
        if stop >= entry:
            print(f"  [CONSENSUS ADJUST] Long stop {stop} was backward relative to entry {entry}. Adjusting to entry - 10.0.")
            stop = entry - 10.0
        if target <= entry:
            print(f"  [CONSENSUS ADJUST] Long target {target} was backward relative to entry {entry}. Adjusting to entry + 20.0.")
            target = entry + 20.0
    elif fabio.direction == 'short':
        if stop <= entry:
            print(f"  [CONSENSUS ADJUST] Short stop {stop} was backward relative to entry {entry}. Adjusting to entry + 10.0.")
            stop = entry + 10.0
        if target >= entry:
            print(f"  [CONSENSUS ADJUST] Short target {target} was backward relative to entry {entry}. Adjusting to entry - 20.0.")
            target = entry - 20.0


    r_ratio = round(reward / risk, 2) if (risk > 0 and reward > 0) else 0.0

    
    # Gate 4: Minimum R:R check (disabled for observation)
    min_rr = 0.0
    if r_ratio < min_rr:
        return ConsensusSignal(
            direction='none', entry=0, stop=0, target=0,
            r_ratio=0, final_confidence=final_conf,
            fabio=fabio, andrea=andrea,
            decision='no_trade',
            no_trade_reason=f'insufficient_rr (R:R {r_ratio} < {min_rr})',
        )
        
    return ConsensusSignal(
        direction        = fabio.direction,
        entry            = entry,
        stop             = stop,
        target           = target,
        r_ratio          = r_ratio,
        final_confidence = final_conf,
        fabio            = fabio,
        andrea           = andrea,
        decision         = 'trade',
        no_trade_reason  = '',
    )
