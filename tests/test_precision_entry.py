"""Tests for the precision entry agent."""
import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from src import Bar, CandidateBar, SessionContext, VolumeProfile, Trade
from src import FabioSignal, AndreaSignal, ConsensusSignal
from src.agents.precision_entry import get_m1_context, refine_entry, _select_precision_topics


def _make_bar(ts_minute=0, close=19940.0, high=19950.0, low=19930.0,
              big_trades=None):
    ts = datetime(2025, 5, 1, 13, ts_minute, tzinfo=timezone.utc)
    return Bar(
        timestamp=ts, open=close - 5, high=high, low=low, close=close,
        volume=2000, buy_volume=1000, sell_volume=1000,
        delta=0, delta_pct=0.0, cvd=0, vwap=close,
        big_trades=big_trades or [],
    )


def _make_m5_bar():
    """M5 bar at 13:50 UTC (09:50 ET)."""
    return Bar(
        timestamp=datetime(2025, 5, 1, 13, 50, tzinfo=timezone.utc),
        open=19971.5, high=19996.25, low=19941.0, close=19944.5,
        volume=9540, buy_volume=4500, sell_volume=5040,
        delta=-538, delta_pct=5.6, cvd=-538, vwap=19960.0,
        big_trades=[
            Trade(ts_event=datetime(2025, 5, 1, 13, 52, tzinfo=timezone.utc),
                  side='B', price=19981.25, size=382),
        ],
    )


def _make_vp():
    return VolumeProfile(
        poc=19943.0, va_high=20034.0, va_low=19885.0,
        hvn_levels=[19941.0], lvn_levels=[19993.0, 20049.75],
    )


def _make_ctx():
    return SessionContext(
        date='2025-05-01', ib_high=19990.75, ib_low=19888.25,
        ib_range=102.5, ib_complete=True, vp=_make_vp(), day_type='balance',
    )


def _make_consensus():
    fabio = FabioSignal(
        direction='short', confidence=65, entry=19940.0,
        stop=19988.0, target=19888.25, setup_type='squeeze',
        reasoning='test', nlm_answer='test',
    )
    andrea = AndreaSignal(
        confirmation=True, confidence=62, setup_type='failed_auction',
        reasoning='test', nlm_answer='test',
    )
    return ConsensusSignal(
        direction='short', entry=19940.0, stop=19988.0, target=19888.25,
        r_ratio=1.08, final_confidence=71, fabio=fabio, andrea=andrea,
        decision='trade', no_trade_reason='',
    )


def _make_candidate():
    bar = _make_m5_bar()
    ctx = _make_ctx()
    return CandidateBar(
        bar=bar, session_ctx=ctx, wall_level=19981.25, wall_side='bid',
        wall_trade_count=1, wall_max_size=382, proximity_to='poc',
        proximity_level=19943.0, bars_in_session=5, is_second_test=False,
        recent_bars=[bar],
    )


class TestGetM1Context:
    def test_extracts_correct_window(self):
        # Create M1 bars from 13:45 to 13:58
        m1_bars = [_make_bar(ts_minute=m) for m in range(45, 59)]
        m5_bar = _make_m5_bar()  # timestamp = 13:50

        result = get_m1_context(m1_bars, m5_bar, context_before=3, context_after=2)

        # Should get 13:47 to 13:56 (3 before 13:50, 5 in M5 bar, 2 after)
        assert len(result) == 10
        assert result[0].timestamp.minute == 47
        assert result[-1].timestamp.minute == 56

    def test_empty_if_no_m1_bars(self):
        m5_bar = _make_m5_bar()
        result = get_m1_context([], m5_bar)
        assert result == []

    def test_partial_window(self):
        # Only have bars 13:50-13:54
        m1_bars = [_make_bar(ts_minute=m) for m in range(50, 55)]
        m5_bar = _make_m5_bar()

        result = get_m1_context(m1_bars, m5_bar, context_before=3, context_after=2)
        assert len(result) == 5  # only the 5 bars we have


class TestSelectPrecisionTopics:
    def test_balance_day_squeeze(self):
        topics = _select_precision_topics('balance', 'squeeze')
        assert 'entry_mechanics' in topics
        assert 'stop_placement' in topics
        assert 'targets_standard' in topics
        assert 'squeeze_entry_trigger' in topics

    def test_trend_day_ivb(self):
        topics = _select_precision_topics('trend_up', 'ivb_breakout')
        assert 'targets_high_volatility' in topics
        assert 'ib_extension_targets' in topics

    def test_always_has_real_trade_example(self):
        topics = _select_precision_topics('balance', 'none')
        assert 'simplified_real_trade_example' in topics


class TestRefineEntry:
    @patch('src.agents.precision_entry.llm_ask')
    def test_returns_refined_levels(self, mock_claude):
        mock_claude.return_value = '```json\n{"entry": 19945.0, "stop": 19985.0, "target": 19888.25, "abort": false, "entry_reasoning": "M1 cluster at 19945", "stop_reasoning": "Behind 382-sell wall", "target_reasoning": "IB low"}\n```'

        candidate = _make_candidate()
        consensus = _make_consensus()
        m1_bars = [_make_bar(ts_minute=m) for m in range(47, 57)]

        result = refine_entry(candidate, consensus, m1_bars)

        assert result['entry'] == 19945.0
        assert result['stop'] == 19985.0
        assert result['target'] == 19888.25
        assert result['abort'] is False
        assert 'M1 cluster' in result['entry_reasoning']

    @patch('src.agents.precision_entry.llm_ask')
    def test_abort_signal(self, mock_claude):
        mock_claude.return_value = '{"entry": 0, "stop": 0, "target": 0, "abort": true, "entry_reasoning": "M1 shows buy absorption, signal invalidated", "stop_reasoning": "", "target_reasoning": ""}'

        candidate = _make_candidate()
        consensus = _make_consensus()
        m1_bars = [_make_bar(ts_minute=m) for m in range(47, 57)]

        result = refine_entry(candidate, consensus, m1_bars)
        assert result['abort'] is True

    @patch('src.agents.precision_entry.llm_ask')
    def test_fallback_on_json_error(self, mock_claude):
        mock_claude.return_value = 'INVALID RESPONSE'

        candidate = _make_candidate()
        consensus = _make_consensus()
        m1_bars = [_make_bar(ts_minute=m) for m in range(47, 57)]

        result = refine_entry(candidate, consensus, m1_bars)
        # Should fallback to M5 levels
        assert result['entry'] == 19940.0
        assert result['stop'] == 19988.0
        assert result['abort'] is False
