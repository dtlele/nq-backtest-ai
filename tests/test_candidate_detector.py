import pytest
from datetime import datetime, timezone
import pytz
from src import Bar, VolumeProfile, SessionContext, NQ_BIG_TRADE_THRESHOLD, Trade
from src.candidate_detector import detect_candidates

ET = pytz.timezone('America/New_York')

def _bar_et(h, m, close, vol=5000, big_size=0) -> Bar:
    dt = ET.localize(datetime(2025,4,30,h,m)).astimezone(timezone.utc)
    big = [Trade(dt, 'A', close, big_size)] if big_size >= NQ_BIG_TRADE_THRESHOLD else []
    return Bar(dt, close-1, close+1, close-1, close,
               vol, vol//2, vol//2, 0, 0.0, 0, close, big)

def _ctx(poc=20000.0, va_high=20050.0, va_low=19950.0,
         ib_high=20020.0, ib_low=19980.0) -> SessionContext:
    vp = VolumeProfile(poc=poc, va_high=va_high, va_low=va_low,
                       hvn_levels=[20030.0], lvn_levels=[20000.0])
    return SessionContext('2025-04-30', ib_high, ib_low,
                          ib_high-ib_low, True, vp, day_type='balance')

def test_detects_candidate_at_lvn():
    ctx = _ctx()
    bars = [_bar_et(9, 41, 20000.0, vol=6000, big_size=45)]
    candidates = detect_candidates(bars, ctx)
    assert len(candidates) == 1
    assert candidates[0].proximity_to in ('overnight_lvn', 'overnight_poc')

def test_no_candidate_before_fabio_active():
    ctx = _ctx()
    bars = [_bar_et(9, 34, 20000.0, vol=4000, big_size=45)]
    assert detect_candidates(bars, ctx) == []

def test_no_candidate_low_volume():
    ctx = _ctx()
    bars = [_bar_et(9, 41, 20000.0, vol=100, big_size=45)]
    assert detect_candidates(bars, ctx) == []

def test_no_candidate_no_big_trade():
    ctx = _ctx()
    bars = [_bar_et(9, 41, 20000.0, vol=4000, big_size=0)]
    assert detect_candidates(bars, ctx) == []

def test_no_candidate_far_from_levels():
    ctx = _ctx(poc=20000.0)
    bars = [_bar_et(9, 41, 20200.0, vol=4000, big_size=45)]
    assert detect_candidates(bars, ctx) == []
