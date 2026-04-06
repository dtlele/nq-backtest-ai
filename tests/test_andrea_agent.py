import pytest, json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import pytz
from src import Bar, SessionContext, VolumeProfile, CandidateBar, Trade, FabioSignal, AndreaSignal
from src.agents.andrea_agent import confirm

ET = pytz.timezone('America/New_York')

def _candidate_and_fabio():
    dt = ET.localize(datetime(2025,4,30,9,45)).astimezone(timezone.utc)
    big = [Trade(dt, 'A', 20000.0, 50)]
    bar = Bar(dt, 19998, 20002, 19995, 20000, 4500, 2500, 2000,
              500, 11.1, 500, 19999.5, big)
    vp = VolumeProfile(poc=20000.0, va_high=20050.0, va_low=19950.0,
                       hvn_levels=[], lvn_levels=[20000.0])
    ctx = SessionContext('2025-04-30', 20020.0, 19980.0, 40.0, True, vp, 'balance')
    cand = CandidateBar(bar, ctx, 20000.0, 'ask', 1, 50, 'lvn', 20000.0, 15, True)
    fab = FabioSignal('long', 75, 20002.0, 19990.0, 20040.0, 'squeeze', 'reasoning', 'nlm')
    return cand, fab

MOCK_ANDREA = json.dumps({
    "confirmation": True,
    "confidence": 70,
    "setup_type": "ibob",
    "reasoning": "Close outside IB high, big trade in body, confirms long."
})

def test_confirm_returns_andrea_signal():
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=MOCK_ANDREA)]
    cand, fab = _candidate_and_fabio()
    with patch('src.agents.andrea_agent.nlm_ask', return_value="Andrea NLM context"):
        with patch('anthropic.Anthropic') as MockClaude:
            MockClaude.return_value.messages.create.return_value = mock_msg
            signal = confirm(cand, fab)
    assert isinstance(signal, AndreaSignal)
    assert signal.confirmation is True
    assert signal.confidence == 70
