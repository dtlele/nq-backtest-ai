import pytest
from unittest.mock import patch, MagicMock
from src.agents.nlm_client import nlm_ask, nlm_use_notebook

def test_nlm_ask_returns_stdout(tmp_path):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "The wall forms when big trades cluster at LVN.\n"
    mock_result.stderr = ""
    with patch('subprocess.run', return_value=mock_result) as mock_run:
        answer = nlm_ask("What is a wall?", "4c868e52")
    assert "wall" in answer.lower()
    # Verify CLI was called with correct notebook
    # call_args_list[0] = nlm_use_notebook (the 'use' call)
    # call_args_list[1] = the actual 'ask' call
    assert mock_run.call_count == 2
    ask_call_args = mock_run.call_args_list[1][0][0]
    assert "ask" in ask_call_args
    assert "What is a wall?" in ask_call_args

def test_nlm_ask_raises_on_auth_error():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Authentication expired. Run notebooklm login"
    with patch('subprocess.run', return_value=mock_result):
        with pytest.raises(RuntimeError, match="AUTH EXPIRED"):
            nlm_ask("question", "4c868e52")
