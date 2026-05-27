import pytest, json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import pytz
from src import Bar, SessionContext, VolumeProfile, CandidateBar, Trade, FabioSignal
from src.agents.fabio_agent import analyze

ET = pytz.timezone('America/New_York')

def _candidate():
    dt = ET.localize(datetime(2025,4,30,9,45)).astimezone(timezone.utc)
    big = [Trade(dt, 'A', 20000.0, 50)]
    bar = Bar(dt, 19998, 20002, 19995, 20000, 4500, 2500, 2000,
              500, 11.1, 500, 19999.5, big)
    vp = VolumeProfile(poc=20000.0, va_high=20050.0, va_low=19950.0,
                       hvn_levels=[20030.0], lvn_levels=[20000.0])
    ctx = SessionContext('2025-04-30', 20020.0, 19980.0, 40.0, True, vp, day_type='balance')
    return CandidateBar(bar, ctx, 20000.0, 'ask', 1, 50, 'lvn', 20000.0, 15, True)

MOCK_CLAUDE_RESPONSE = json.dumps({
    "direction": "long",
    "confidence": 78,
    "entry": 20002.0,
    "stop": 19990.0,
    "target": 20040.0,
    "setup_type": "squeeze",
    "reasoning": "Big buy cluster at LVN + second test = squeeze setup long."
})

def test_analyze_returns_fabio_signal(tmp_path):
    with patch('src.agents.fabio_agent.llm_ask', return_value=MOCK_CLAUDE_RESPONSE):
        signal = analyze(_candidate())
    assert isinstance(signal, FabioSignal)
    assert signal.direction == 'long'
    assert signal.confidence == 78
    assert signal.entry == pytest.approx(20002.0)

def test_analyze_returns_none_signal_on_no_trade():
    no_trade_response = json.dumps({
        "direction": "none", "confidence": 30,
        "entry": None, "stop": None, "target": None,
        "setup_type": "none",
        "reasoning": "No clear setup."
    })
    with patch('src.agents.fabio_agent.llm_ask', return_value=no_trade_response):
        signal = analyze(_candidate())
    assert signal.direction == 'none'
    assert signal.confidence == 30
