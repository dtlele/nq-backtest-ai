import pytest
from datetime import datetime, timezone
from src import Bar, ConsensusSignal, FabioSignal, AndreaSignal, OpenTrade, ClosedTrade
from src.trade_simulator import open_trade, step_trade, close_eod

def _bar(h, m, hi, lo, vol=4000):
    dt = datetime(2025,4,30,h,m,tzinfo=timezone.utc)
    return Bar(dt, (hi+lo)/2, hi, lo, (hi+lo)/2, vol,
               vol//2, vol//2, 0, 0.0, 0, (hi+lo)/2)

def _consensus(direction='long', entry=20000.0, stop=19990.0, target=20020.0):
    fab = FabioSignal(direction, 75, entry, stop, target, 'squeeze', 'r', 'nlm')
    and_ = AndreaSignal(True, 70, 'ibob', 'r', 'nlm')
    from src.consensus import build_consensus
    return build_consensus(fab, and_)

def test_long_hits_target():
    trade = open_trade(_consensus('long', 20000, 19990, 20020), _bar(13,30,20001,19999))
    bars = [_bar(13,31,20025,20010)]  # high exceeds target
    closed = step_trade(trade, bars)
    assert closed is not None
    assert closed.exit_reason == 'target'
    assert closed.pnl_usd > 0

def test_long_hits_stop():
    trade = open_trade(_consensus('long', 20000, 19990, 20020), _bar(13,30,20001,19999))
    bars = [_bar(13,31,20005,19985)]  # low below stop
    closed = step_trade(trade, bars)
    assert closed is not None
    assert closed.exit_reason == 'stop'
    assert closed.pnl_usd < 0

def test_short_hits_target():
    trade = open_trade(_consensus('short', 20000, 20010, 19980), _bar(13,30,20001,19999))
    bars = [_bar(13,31,19990,19975)]  # low below target 19980
    closed = step_trade(trade, bars)
    assert closed is not None
    assert closed.exit_reason == 'target'
    assert closed.pnl_usd > 0

def test_short_hits_stop():
    trade = open_trade(_consensus('short', 20000, 20010, 19980), _bar(13,30,20001,19999))
    bars = [_bar(13,31,20015,20005)]  # high above stop 20010
    closed = step_trade(trade, bars)
    assert closed is not None
    assert closed.exit_reason == 'stop'
    assert closed.pnl_usd < 0

def test_eod_close():
    trade = open_trade(_consensus('long', 20000, 19990, 20020), _bar(13,30,20001,19999))
    closed = close_eod(trade, _bar(15,59,20010,19995))
    assert closed.exit_reason == 'eod'
