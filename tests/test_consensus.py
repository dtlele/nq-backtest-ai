import pytest
from src import FabioSignal, AndreaSignal, ConsensusSignal
from src.consensus import build_consensus

def _fab(conf, direction='long'):
    return FabioSignal(direction, conf, 20002.0, 19990.0, 20040.0,
                       'squeeze', 'reasoning', 'nlm')
def _and(confirm, conf):
    return AndreaSignal(confirm, conf, 'ibob' if confirm else 'none', 'r', 'nlm')

def test_fabio_below_threshold_no_trade():
    c = build_consensus(_fab(60), _and(True, 70))
    assert c.decision == 'no_trade'
    assert 'fabio' in c.no_trade_reason

def test_andrea_veto_no_trade():
    c = build_consensus(_fab(75), _and(False, 35))
    assert c.decision == 'no_trade'
    assert 'andrea' in c.no_trade_reason

def test_andrea_confirms_trade():
    c = build_consensus(_fab(75), _and(True, 65))
    assert c.decision == 'trade'
    assert c.final_confidence > 75  # boosted

def test_andrea_no_confirm_but_not_veto_still_trades():
    c = build_consensus(_fab(75), _and(False, 50))  # 50 >= veto threshold
    assert c.decision == 'trade'
    assert c.final_confidence < 75  # penalized

def test_r_ratio_calculated():
    c = build_consensus(_fab(75), _and(True, 65))
    # entry=20002, stop=19990, target=20040 → R = (20040-20002)/(20002-19990) = 38/12 ≈ 3.17
    assert c.r_ratio == pytest.approx(38/12, rel=0.01)
