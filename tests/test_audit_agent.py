import pytest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.agents.audit_agent import audit_session, load_dynamic_rules, save_dynamic_rules, DYNAMIC_RULES_FILE

@pytest.fixture(autouse=True)
def clean_rules_file(tmp_path):
    # Redirect DYNAMIC_RULES_FILE to temp directory for testing
    test_file = tmp_path / "dynamic_rules.json"
    with patch("src.agents.audit_agent.DYNAMIC_RULES_FILE", test_file):
        yield test_file

def test_load_dynamic_rules_creates_default_if_not_exists(clean_rules_file):
    assert not clean_rules_file.exists()
    rules = load_dynamic_rules()
    assert clean_rules_file.exists()
    assert "dynamic_rules" in rules
    assert "session_learnings" in rules

def test_save_and_load_dynamic_rules(clean_rules_file):
    data = {
        "dynamic_rules": [
            {
                "rule_id": "TEST_001",
                "topic": "Testing",
                "description": "Always write unit tests.",
                "action": "pass_test"
            }
        ],
        "session_learnings": ["Test ran successfully."]
    }
    save_dynamic_rules(data)
    loaded = load_dynamic_rules()
    assert loaded["dynamic_rules"][0]["rule_id"] == "TEST_001"
    assert loaded["session_learnings"][0] == "Test ran successfully."

@patch("src.agents.audit_agent.llm_ask")
def test_audit_session_updates_rules(mock_llm_ask, clean_rules_file, tmp_path):
    from src.agent_memory import LOG_FILE
    
    # Redirect LOG_FILE for testing
    test_log = tmp_path / "reasoning_log.jsonl"
    mock_response = json.dumps({
        "dynamic_rules": [
            {
                "rule_id": "AMT_001",
                "topic": "Trend",
                "description": "Never short trend up days.",
                "action": "skip"
            }
        ],
        "session_learnings": ["Avoided bad short."]
    })
    mock_llm_ask.return_value = mock_response

    with patch("src.agents.audit_agent.LOG_FILE", test_log):
        # Create a mock entry so audit doesn't skip
        test_log.parent.mkdir(parents=True, exist_ok=True)
        with open(test_log, 'w', encoding='utf-8') as f:
            f.write(json.dumps({"date": "2025-04-30", "fabio_reasoning": "some context"}) + "\n")

        # Call audit
        updated = audit_session("2025-04-30")
    
    assert mock_llm_ask.called
    assert len(updated["dynamic_rules"]) == 1
    assert updated["dynamic_rules"][0]["rule_id"] == "AMT_001"
    assert updated["session_learnings"][0] == "Avoided bad short."
    
    # Verify saved
    saved = load_dynamic_rules()
    assert len(saved["dynamic_rules"]) == 1
