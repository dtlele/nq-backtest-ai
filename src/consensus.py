from src import (FabioSignal, AndreaSignal, ConsensusSignal,
                 FABIO_MIN_CONFIDENCE, ANDREA_VETO_THRESHOLD)

def build_consensus(fabio: FabioSignal, andrea: AndreaSignal) -> ConsensusSignal:
    # Gate 1: Fabio confidence
    if fabio.confidence < FABIO_MIN_CONFIDENCE or fabio.direction == 'none':
        return ConsensusSignal(
            direction='none', entry=0, stop=0, target=0,
            r_ratio=0, final_confidence=fabio.confidence,
            fabio=fabio, andrea=andrea,
            decision='no_trade',
            no_trade_reason=f'fabio_below_threshold ({fabio.confidence} < {FABIO_MIN_CONFIDENCE})',
        )
    # Gate 2: Andrea veto
    if not andrea.confirmation and andrea.confidence < ANDREA_VETO_THRESHOLD:
        return ConsensusSignal(
            direction='none', entry=0, stop=0, target=0,
            r_ratio=0, final_confidence=fabio.confidence,
            fabio=fabio, andrea=andrea,
            decision='no_trade',
            no_trade_reason=f'andrea_veto (confidence={andrea.confidence})',
        )
    # Trade approved
    boost = 1.1 if andrea.confirmation else 0.85
    final_conf = min(100, int(fabio.confidence * boost))
    entry  = fabio.entry  or 0.0
    stop   = fabio.stop   or 0.0
    target = fabio.target or 0.0
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
