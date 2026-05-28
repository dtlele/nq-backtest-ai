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
    # Gate 2: Andrea veto (Activated!)
    if andrea.confidence < ANDREA_VETO_THRESHOLD or not andrea.confirmation:
        return ConsensusSignal(
            direction='none', entry=0, stop=0, target=0,
            r_ratio=0, final_confidence=andrea.confidence,
            fabio=fabio, andrea=andrea,
            decision='no_trade',
            no_trade_reason=f'andrea_veto (confirmation={andrea.confirmation}, conf={andrea.confidence})',
        )

    # Trade approved
    boost = 1.1 if andrea.confirmation else 0.85
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
        
    if fabio.entry is None or fabio.stop is None or fabio.target is None:
        raise ValueError(f"Approved trade has None price fields: entry={fabio.entry}, stop={fabio.stop}, target={fabio.target}")
    entry  = fabio.entry
    stop   = fabio.stop
    target = fabio.target
    risk   = abs(entry - stop)
    reward = abs(target - entry)
    r_ratio = round(reward / risk, 2) if risk > 0 else 0.0
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
