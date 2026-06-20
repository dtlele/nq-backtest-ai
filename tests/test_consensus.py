import pytest
from src import FabioSignal, AndreaSignal, ConsensusSignal
from src.consensus import build_consensus

def _fab(conf, direction='long', entry=20002.0, stop=19990.0, target=20040.0):
    return FabioSignal(direction, conf, entry, stop, target,
                       'squeeze', 'reasoning', 'nlm')
def _and(confirm, conf):
    return AndreaSignal(confirm, conf, 'ibob' if confirm else 'none', 'r', 'nlm')

def test_fabio_below_threshold_no_trade():
    c = build_consensus(_fab(74), _and(True, 70))
    assert c.decision == 'no_trade'
    assert 'fabio' in c.no_trade_reason

def test_andrea_veto_disabled():
    # Andrea veto is disabled, so even if confirm=False and conf=35, trade proceeds
    c = build_consensus(_fab(85), _and(False, 35))
    assert c.decision == 'trade'

def test_andrea_confirms_trade():
    c = build_consensus(_fab(85), _and(True, 65))
    assert c.decision == 'trade'
    assert c.final_confidence > 85  # boosted

def test_r_ratio_calculated():
    c = build_consensus(_fab(85), _and(True, 65))
    # entry=20002, stop=19990, target=20040 → R = (20040-20002)/(20002-19990) = 38/12 ≈ 3.17
    assert c.r_ratio == pytest.approx(38/12, rel=0.01)

def test_fabio_direction_none_no_trade():
    """direction='none' with high confidence still blocks trade."""
    c = build_consensus(_fab(85, direction='none'), _and(True, 70))
    assert c.decision == 'no_trade'
    assert 'fabio' in c.no_trade_reason
    assert 'threshold' not in c.no_trade_reason

def test_approved_trade_none_prices_adjusted():
    """Verify behavior for None prices in both strict and adjusted modes."""
    import src.consensus as consensus
    fab_none = FabioSignal('long', 85, None, None, None, 'squeeze', 'r', 'nlm')
    
    # 1. STRICT_PROD_MODE = True -> Skip/Reject
    consensus.STRICT_PROD_MODE = True
    try:
        c = consensus.build_consensus(fab_none, _and(True, 65))
        assert c.decision == 'skip'
        assert 'missing_price_fields' in c.no_trade_reason
    finally:
        consensus.STRICT_PROD_MODE = False
        
    # 2. STRICT_PROD_MODE = False -> Adjust
    consensus.STRICT_PROD_MODE = False
    c = consensus.build_consensus(fab_none, _and(True, 65))
    assert c.decision == 'trade'
    assert c.entry == 0.0
    assert c.stop == -10.0
    assert c.target == 20.0

def test_backward_levels_adjusted():
    """Verify behavior for backward levels in both strict and adjusted modes."""
    import src.consensus as consensus
    # Long trade with stop >= entry and target <= entry
    fab_backward = FabioSignal('long', 85, 20000.0, 20010.0, 19990.0, 'squeeze', 'r', 'nlm')
    
    # 1. STRICT_PROD_MODE = True -> Reject/No Trade
    consensus.STRICT_PROD_MODE = True
    try:
        c = consensus.build_consensus(fab_backward, _and(True, 65))
        assert c.decision == 'no_trade'
        assert 'backward_levels' in c.no_trade_reason
    finally:
        consensus.STRICT_PROD_MODE = False
        
    # 2. STRICT_PROD_MODE = False -> Adjust
    consensus.STRICT_PROD_MODE = False
    c = consensus.build_consensus(fab_backward, _and(True, 65))
    assert c.decision == 'trade'
    assert c.stop == 19990.0  # entry (20000) - 10
    assert c.target == 20020.0  # entry (20000) + 20
