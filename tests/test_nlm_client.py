import pytest
from unittest.mock import patch, MagicMock
import src.agents.nlm_client as nlm_mod
from src.agents.nlm_client import nlm_ask, nlm_use_notebook


@pytest.fixture(autouse=True)
def reset_auth_state():
    """Reset the lazy auth probe before each test."""
    nlm_mod._auth_expired = None
    yield
    nlm_mod._auth_expired = None


def test_nlm_ask_returns_stdout(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "The wall forms when big trades cluster at LVN.\n"
    mock_result.stderr = ""
    with patch('subprocess.run', return_value=mock_result) as mock_run:
        answer = nlm_ask("What is a wall?", "4c868e52")
    assert "wall" in answer.lower()
    # call_args_list: [0] auth probe 'use', [1] auth probe 'ask ping',
    #                 [2] actual 'use', [3] actual 'ask'
    assert mock_run.call_count == 4
    ask_call_args = mock_run.call_args_list[3][0][0]
    assert "ask" in ask_call_args
    assert "What is a wall?" in ask_call_args


def test_nlm_ask_returns_fallback_on_auth_error():
    """Auth expired returns a fallback string instead of raising."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Authentication expired. Run notebooklm login"
    with patch('subprocess.run', return_value=mock_result):
        answer = nlm_ask("question", "4c868e52")
    assert "NLM AUTH EXPIRED" in answer
    assert "notebooklm login" in answer


def test_nlm_skip_after_auth_detected():
    """Once auth is detected as expired, subsequent calls skip subprocess."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Authentication expired"
    with patch('subprocess.run', return_value=mock_result) as mock_run:
        # First call does the probe
        answer1 = nlm_ask("q1", "abc")
        call_count_after_first = mock_run.call_count
        # Second call should NOT spawn any subprocess
        answer2 = nlm_ask("q2", "abc")
        assert mock_run.call_count == call_count_after_first
    assert "NLM AUTH EXPIRED" in answer1
    assert "NLM AUTH EXPIRED" in answer2
