import pytest, json
from datetime import datetime, timezone
import pytz
from src import Bar, SessionContext, VolumeProfile, CandidateBar, Trade
from src.signal_context import build_fabio_question, build_andrea_question

ET = pytz.timezone('America/New_York')

def _candidate() -> CandidateBar:
    dt = ET.localize(datetime(2025,4,30,9,45)).astimezone(timezone.utc)
    big = [Trade(dt, 'A', 20000.0, 50)]
    bar = Bar(dt, 19998, 20002, 19995, 20000, 4500, 2500, 2000,
              500, 11.1, 500, 19999.5, big)
    vp = VolumeProfile(poc=20000.0, va_high=20050.0, va_low=19950.0,
                       hvn_levels=[20030.0], lvn_levels=[20000.0])
    ctx = SessionContext('2025-04-30', 20020.0, 19980.0, 40.0, True, vp, day_type='balance')
    return CandidateBar(bar, ctx, 20000.0, 'ask', 1, 50, 'lvn', 20000.0, 15, False)

def test_fabio_question_contains_key_data():
    q = build_fabio_question(_candidate())
    assert '20000' in q
    assert '20020' in q or 'IVB' in q  # ib_high
    assert 'squeeze' in q.lower() or 'drive' in q.lower()

def test_fabio_question_no_volume_profile():
    cand = _candidate()
    cand.session_ctx.vp = None
    q = build_fabio_question(cand)
    assert 'N/A' in q

def test_andrea_question_requires_fabio_signal():
    from src import FabioSignal
    fab = FabioSignal('long', 75, 20002.0, 19990.0, 20040.0, 'squeeze', 'reasoning', 'nlm')
    q = build_andrea_question(_candidate(), fab)
    assert 'long' in q
    assert 'IBOB' in q or 'ibob' in q.lower()
