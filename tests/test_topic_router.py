"""Tests for the dynamic topic router."""
import pytest
from datetime import datetime, timezone
from src import Bar, CandidateBar, SessionContext, VolumeProfile, Trade
from src.agents.topic_router import (
    select_fabio_topics, select_andrea_topics, build_knowledge_text,
    build_tiered_knowledge, SIMPLIFIED_TOPICS,
    _infer_preliminary_setup, FABIO_CORE, ANDREA_CORE,
    MAX_KNOWLEDGE_CHARS,
)


def _make_bar(close=19300.0, high=19310.0, low=19280.0, open_=19295.0,
              big_trades=None):
    return Bar(
        timestamp=datetime(2025, 5, 1, 14, 35, tzinfo=timezone.utc),
        open=open_, high=high, low=low, close=close,
        volume=8000, buy_volume=4000, sell_volume=4000,
        delta=0, delta_pct=0.0, cvd=0, vwap=close,
        big_trades=big_trades or [],
    )


def _make_vp():
    return VolumeProfile(
        poc=19298.0, va_high=19414.0, va_low=19200.0,
        hvn_levels=[19300.0], lvn_levels=[19350.0, 19250.0],
    )


def _make_ctx(day_type='balance', ib_high=19304.5, ib_low=19135.0):
    return SessionContext(
        date='2025-05-01', ib_high=ib_high, ib_low=ib_low,
        ib_range=ib_high - ib_low, ib_complete=True,
        vp=_make_vp(), day_type=day_type,
    )


def _make_candidate(close=19300.0, proximity='lvn', wall_side='bid',
                    day_type='balance', is_second_test=False,
                    wall_max_size=50, wall_trade_count=3,
                    ib_high=19304.5, ib_low=19135.0):
    bar = _make_bar(close=close, high=close + 10, low=close - 20)
    ctx = _make_ctx(day_type=day_type, ib_high=ib_high, ib_low=ib_low)
    return CandidateBar(
        bar=bar, session_ctx=ctx,
        wall_level=close - 5, wall_side=wall_side,
        wall_trade_count=wall_trade_count, wall_max_size=wall_max_size,
        proximity_to=proximity, proximity_level=close - 2,
        bars_in_session=10, is_second_test=is_second_test,
        recent_bars=[bar],
    )


# Fake knowledge store for testing
FAKE_STORE = {t: f"Knowledge about {t}. " * 20 for t in [
    # Fabio core + extras
    'simplified_model_overview', 'simplified_wall_definition',
    'simplified_entry_trigger', 'simplified_stop_exact', 'simplified_target_exact',
    'squeeze_definition', 'squeeze_entry_trigger', 'trapped_buyers', 'trapped_sellers',
    'simplified_second_drive_exact', 'simplified_ivb_formation', 'ib_breakout_rules',
    'ib_extension_targets', 'second_drive', 'squeeze_vs_failed_auction',
    'pre_explosion_pattern', 'effort_vs_result', 'simplified_no_trade_top3',
    'simplified_day_type_quick', 'choppy_day_identification', 'aplus_setup', 'ib_bias',
    'punches_to_wall', 'big_trades_filter', 'counter_trend_rules', 'entry_mechanics',
    'coherence_of_information', 'simplified_reentry', 'myisto_pattern', 'stop_placement',
    # Andrea core + extras
    'ibob_overview', 'ibob_candle_close', 'ibob_bubble_body_vs_wick',
    'simplified_entry_mechanical', 'squeeze_setup_andrea', 'ibob_diagonal_imbalances',
    'ibob_stop_target', 'ibob_invalidation', 'failed_auction_definition',
    'failed_auction_variants', 'absorption_vs_exhaustion',
    'ibob_no_trade_conditions', 'balance_vs_imbalance', 'no_trade_rules',
    'trend_day_rules', 'initiative_vs_response', 'hvn_lvn', 'bolle_filter',
    'rotation_within_va', 'entry_failed_auction', 'footprint_reading',
    'institutional_activity',
]}


class TestInferSetup:
    def test_failed_auction_above_ib(self):
        # Price poked above IB high but closed inside
        c = _make_candidate(close=19300.0, ib_high=19304.5)
        c.bar = _make_bar(close=19300.0, high=19310.0)
        assert _infer_preliminary_setup(c) == 'failed_auction'

    def test_ivb_breakout_above(self):
        c = _make_candidate(close=19310.0, ib_high=19304.5)
        assert _infer_preliminary_setup(c) == 'ivb_breakout'

    def test_squeeze_inside_ib(self):
        c = _make_candidate(close=19250.0, proximity='lvn',
                            wall_trade_count=3, ib_high=19304.5, ib_low=19135.0)
        c.bar = _make_bar(close=19250.0, high=19260.0, low=19240.0)
        assert _infer_preliminary_setup(c) == 'squeeze'


class TestFabioTopics:
    def test_core_always_included(self):
        c = _make_candidate()
        topics = select_fabio_topics(c, FAKE_STORE)
        for core in FABIO_CORE:
            assert core in topics

    def test_squeeze_topics_for_squeeze_setup(self):
        c = _make_candidate(close=19250.0, proximity='lvn', wall_trade_count=3)
        c.bar = _make_bar(close=19250.0, high=19260.0, low=19240.0)
        topics = select_fabio_topics(c, FAKE_STORE)
        assert 'squeeze_definition' in topics
        assert 'squeeze_entry_trigger' in topics

    def test_ivb_topics_for_breakout(self):
        c = _make_candidate(close=19310.0)
        topics = select_fabio_topics(c, FAKE_STORE)
        assert 'simplified_ivb_formation' in topics or 'ib_breakout_rules' in topics

    def test_balance_day_adds_balance_topics(self):
        c = _make_candidate(day_type='balance')
        topics = select_fabio_topics(c, FAKE_STORE)
        assert 'simplified_day_type_quick' in topics

    def test_trend_day_adds_trend_topics(self):
        c = _make_candidate(day_type='trend_up', close=19310.0)
        topics = select_fabio_topics(c, FAKE_STORE)
        assert 'aplus_setup' in topics

    def test_second_test_adds_reentry(self):
        c = _make_candidate(is_second_test=True)
        topics = select_fabio_topics(c, FAKE_STORE)
        assert 'simplified_reentry' in topics

    def test_high_wall_adds_big_trades_filter(self):
        c = _make_candidate(wall_max_size=150)
        topics = select_fabio_topics(c, FAKE_STORE)
        assert 'big_trades_filter' in topics or 'coherence_of_information' in topics

    def test_no_duplicates(self):
        c = _make_candidate()
        topics = select_fabio_topics(c, FAKE_STORE)
        assert len(topics) == len(set(topics))

    def test_different_candidates_get_different_topics(self):
        # Squeeze candidate
        c1 = _make_candidate(close=19250.0, proximity='lvn', day_type='balance',
                             wall_trade_count=3)
        c1.bar = _make_bar(close=19250.0, high=19260.0, low=19240.0)
        # Trend breakout candidate
        c2 = _make_candidate(close=19310.0, proximity='ib_high', day_type='trend_up')

        t1 = select_fabio_topics(c1, FAKE_STORE)
        t2 = select_fabio_topics(c2, FAKE_STORE)
        assert t1 != t2


class TestAndreaTopics:
    def test_core_always_included(self):
        c = _make_candidate()
        topics = select_andrea_topics(c, 'squeeze', FAKE_STORE)
        for core in ANDREA_CORE:
            assert core in topics

    def test_squeeze_setup(self):
        c = _make_candidate()
        topics = select_andrea_topics(c, 'squeeze', FAKE_STORE)
        assert 'squeeze_setup_andrea' in topics

    def test_failed_auction_setup(self):
        c = _make_candidate()
        topics = select_andrea_topics(c, 'failed_auction', FAKE_STORE)
        assert 'failed_auction_definition' in topics

    def test_no_duplicates(self):
        c = _make_candidate()
        topics = select_andrea_topics(c, 'squeeze', FAKE_STORE)
        assert len(topics) == len(set(topics))


class TestBuildKnowledgeText:
    def test_formats_topics(self):
        store = {'topic_a': 'Answer A', 'topic_b': 'Answer B'}
        text = build_knowledge_text(['topic_a', 'topic_b'], store)
        assert '### topic_a' in text
        assert 'Answer A' in text
        assert '### topic_b' in text

    def test_skips_missing_topics(self):
        store = {'topic_a': 'Answer A'}
        text = build_knowledge_text(['topic_a', 'missing'], store)
        assert '### topic_a' in text
        assert 'missing' not in text


class TestBuildTieredKnowledge:
    def test_separates_rules_and_context(self):
        store = {
            'simplified_model_overview': 'Rule content',
            'squeeze_definition': 'Context content',
        }
        rules, context = build_tiered_knowledge(
            ['simplified_model_overview', 'squeeze_definition'], store
        )
        assert 'Rule content' in rules
        assert 'Context content' in context
        assert 'squeeze_definition' not in rules
        assert 'simplified_model_overview' not in context

    def test_all_simplified_in_rules(self):
        store = {
            'simplified_entry_trigger': 'A',
            'simplified_stop_exact': 'B',
            'ibob_overview': 'C',
        }
        rules, context = build_tiered_knowledge(
            ['simplified_entry_trigger', 'simplified_stop_exact', 'ibob_overview'], store
        )
        assert 'simplified_entry_trigger' in rules
        assert 'simplified_stop_exact' in rules
        assert 'ibob_overview' in rules  # ibob_overview is in SIMPLIFIED_TOPICS

    def test_deep_topics_in_context(self):
        store = {
            'squeeze_vs_failed_auction': 'Deep knowledge',
            'effort_vs_result': 'More deep knowledge',
        }
        rules, context = build_tiered_knowledge(
            ['squeeze_vs_failed_auction', 'effort_vs_result'], store
        )
        assert rules == ''  # no simplified topics
        assert 'squeeze_vs_failed_auction' in context
        assert 'effort_vs_result' in context


class TestBudgetTrimming:
    def test_respects_budget(self):
        # Create a store with huge topics
        big_store = {f'topic_{i}': 'x' * 10_000 for i in range(10)}
        topics = [f'topic_{i}' for i in range(10)]
        from src.agents.topic_router import _trim_to_budget
        trimmed = _trim_to_budget(topics, big_store)
        total = sum(len(big_store[t]) for t in trimmed)
        assert total <= MAX_KNOWLEDGE_CHARS
        assert len(trimmed) < 10  # some were dropped
