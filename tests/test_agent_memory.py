import pytest, json, os, tempfile
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
from src import ClosedTrade

def _trade(pnl_usd, direction='long'):
    sign = 1 if pnl_usd >= 0 else -1
    entry, stop = 20000.0, 19990.0 if direction == 'long' else 20010.0
    exit_p = entry + sign * abs(pnl_usd) / 5
    return ClosedTrade(direction, entry, stop, entry+sign*20, exit_p,
                       'target', pnl_usd/5, pnl_usd,
                       datetime(2025,4,30,9,45,tzinfo=timezone.utc),
                       datetime(2025,4,30,10, 0,tzinfo=timezone.utc),
                       'fabio', 'andrea', 'squeeze', 75, 2.0)

def test_reset_session_writes_file(tmp_path):
    import src.agent_memory as am
    with patch('src.agent_memory.SESSION_FILE', tmp_path / 'session_state.json'):
        state = am.reset_session('2025-04-30')
        assert state['date'] == '2025-04-30'
        assert state['daily_pnl_usd'] == 0.0
        with open(tmp_path / 'session_state.json') as f:
            saved = json.load(f)
        assert saved['date'] == '2025-04-30'

def test_log_reasoning_appends_jsonl(tmp_path):
    import src.agent_memory as am
    log = tmp_path / 'reasoning_log.jsonl'
    am.LOG_FILE = log
    am.log_reasoning({'bar_time': '09:45', 'decision': 'trade'})
    am.log_reasoning({'bar_time': '10:00', 'decision': 'no_trade'})
    lines = log.read_text().strip().split('\n')
    assert len(lines) == 2
    assert json.loads(lines[0])['decision'] == 'trade'

def test_update_pattern_memory_win_rate(tmp_path):
    import src.agent_memory as am
    pm_file = tmp_path / 'pattern_memory.json'
    pm_file.write_text(json.dumps({'total_trades':0,'wins':0,'losses':0,
                                   'win_rate':0.0,'avg_r':0.0,
                                   'best_setups':[],'worst_setups':[],'notes':[]}))
    am.PATTERN_FILE = pm_file
    am.update_pattern_memory(_trade(500, 'long'))
    am.update_pattern_memory(_trade(-250, 'short'))
    pm = json.loads(pm_file.read_text())
    assert pm['total_trades'] == 2
    assert pm['wins'] == 1
    assert pm['win_rate'] == pytest.approx(0.5)

def test_update_pattern_memory_r_positive_for_short_winner(tmp_path):
    """Short trade winner must produce positive R."""
    import src.agent_memory as am
    pm_file = tmp_path / 'pattern_memory.json'
    pm_file.write_text(json.dumps({'total_trades':0,'wins':0,'losses':0,
                                   'win_rate':0.0,'avg_r':0.0,
                                   'best_setups':[],'worst_setups':[],'notes':[]}))
    am.PATTERN_FILE = pm_file
    # Short: entry=20000, stop=20010, target=19980, exit at target → pnl_ticks=+80
    t = ClosedTrade('short', 20000.0, 20010.0, 19980.0, 19980.0, 'target',
                    80.0, 400.0,
                    datetime(2025,4,30,9,45,tzinfo=timezone.utc),
                    datetime(2025,4,30,10, 0,tzinfo=timezone.utc),
                    'fabio', 'andrea', 'squeeze', 75, 2.0)
    am.update_pattern_memory(t)
    pm = json.loads(pm_file.read_text())
    assert pm['avg_r'] > 0  # winner must have positive R
