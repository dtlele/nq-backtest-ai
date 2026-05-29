"""
Dynamic topic router for agent knowledge selection.

Instead of hardcoding the same 9 topics for every candidate, this module
selects the most relevant topics from the full knowledge base based on:
  - setup_type detected (squeeze, ivb_breakout, failed_auction)
  - day_type (balance, trend_up, trend_down)
  - proximity_to (which VP level the wall is near)
  - wall_side (bid/ask → short/long bias)
  - bar position relative to IB (above, below, inside)

Each agent (Fabio/Andrea) has its own routing table.
A token budget ensures we never exceed ~8K tokens of knowledge per call.
"""
from src import CandidateBar

# Max chars of knowledge to inject (~8K tokens ≈ 32K chars, but we stay conservative)
MAX_KNOWLEDGE_CHARS = 28_000


# ─── FABIO ROUTING TABLE ─────────────────────────────────────────────────────
# Core topics always included (minimal essentials — keep small to leave room for context-specific)
FABIO_CORE = [
    'simplified_model_overview',
    'simplified_entry_trigger',
    'simplified_stop_exact',
]

# Setup-specific topics
FABIO_BY_SETUP = {
    'squeeze': [
        'squeeze_definition',
        'squeeze_entry_trigger',
        'trapped_buyers',
        'trapped_sellers',
        'simplified_second_drive_exact',
    ],
    'ivb_breakout': [
        'simplified_ivb_formation',
        'ivb_model_1',
        'ib_breakout_rules',
        'ib_extension_targets',
        'simplified_second_drive_exact',
        'second_drive',
    ],
    'failed_auction': [
        'squeeze_vs_failed_auction',
        'pre_explosion_pattern',
        'effort_vs_result',
        'simplified_second_drive_exact',
    ],
    'imbalance_hunting': [
        'ib_breakout_rules',
        'ib_extension_targets',
        'simplified_second_drive_exact',
        'initiative_vs_absorption',
        'trapped_buyers',
        'trapped_sellers',
    ],
    'none': [
        'simplified_no_trade_top3',
        'simplified_ivb_formation',
    ],
}

# Day-type topics
FABIO_BY_DAY_TYPE = {
    'balance': [
        'simplified_day_type_quick',
        'choppy_day_identification',
        'simplified_no_trade_top3',
    ],
    'trend_up': [
        'simplified_day_type_quick',
        'aplus_setup',
        'ib_bias',
    ],
    'trend_down': [
        'simplified_day_type_quick',
        'aplus_setup',
        'ib_bias',
    ],
    'unknown': [
        'simplified_day_type_quick',
    ],
}

# Proximity-specific topics
FABIO_BY_PROXIMITY = {
    'ib_high': ['ib_breakout_rules', 'simplified_ivb_formation'],
    'ib_low':  ['ib_breakout_rules', 'simplified_ivb_formation'],
    'poc':     ['punches_to_wall', 'big_trades_filter'],
    'va_high': ['counter_trend_rules', 'entry_mechanics'],
    'va_low':  ['counter_trend_rules', 'entry_mechanics'],
    'lvn':     ['punches_to_wall', 'big_trades_filter', 'effort_vs_result'],
    'hvn':     ['big_trades_filter', 'coherence_of_information'],
    'imbalance_zone': ['ib_extension_targets', 'trapped_buyers', 'trapped_sellers'],
}

# Extra context for specific scenarios
FABIO_EXTRAS = {
    'second_test':    ['simplified_reentry', 'myisto_pattern'],
    'high_wall':      ['big_trades_filter', 'coherence_of_information'],
    'counter_trend':  ['counter_trend_rules', 'stop_placement'],
}


# ─── ANDREA ROUTING TABLE ────────────────────────────────────────────────────
ANDREA_CORE = [
    'ibob_overview',
    'ibob_candle_close',
    'ibob_bubble_body_vs_wick',
    'simplified_entry_mechanical',
]

ANDREA_BY_SETUP = {
    'squeeze': [
        'squeeze_setup_andrea',
        'ibob_diagonal_imbalances',
        'ibob_stop_target',
    ],
    'ivb_breakout': [
        'ibob_diagonal_imbalances',
        'ibob_stop_target',
        'ibob_invalidation',
    ],
    'failed_auction': [
        'failed_auction_definition',
        'failed_auction_variants',
        'absorption_vs_exhaustion',
        'ibob_invalidation',
    ],
    'imbalance_hunting': [
        'ibob_diagonal_imbalances',
        'ibob_stop_target',
        'ibob_invalidation',
    ],
    'none': [
        'ibob_no_trade_conditions',
        'ibob_invalidation',
    ],
}

ANDREA_BY_DAY_TYPE = {
    'balance': [
        'balance_vs_imbalance',
        'no_trade_rules',
    ],
    'trend_up': [
        'trend_day_rules',
        'initiative_vs_response',
    ],
    'trend_down': [
        'trend_day_rules',
        'initiative_vs_response',
    ],
    'unknown': [],
}

ANDREA_BY_PROXIMITY = {
    'ib_high': ['ibob_invalidation'],
    'ib_low':  ['ibob_invalidation'],
    'poc':     ['bolle_filter', 'footprint_reading'],
    'va_high': ['rotation_within_va', 'entry_failed_auction'],
    'va_low':  ['rotation_within_va', 'entry_failed_auction'],
    'lvn':     ['hvn_lvn', 'bolle_filter'],
    'hvn':     ['hvn_lvn', 'institutional_activity'],
}


def _dedupe(topics: list) -> list:
    """Remove duplicates preserving order."""
    seen = set()
    result = []
    for t in topics:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _infer_preliminary_setup(candidate: CandidateBar) -> str:
    """Infer a likely setup type from candidate data before Fabio runs.

    This is a heuristic — the real setup_type comes from Fabio's response.
    Used to pre-select relevant knowledge topics.
    """
    bar = candidate.bar
    ctx = candidate.session_ctx

    if candidate.setup_category == 'imbalance_hunting':
        return 'imbalance_hunting'

    # Failed auction: price poked outside IB but closed back inside
    if bar.high > ctx.ib_high and bar.close < ctx.ib_high:
        return 'failed_auction'
    if bar.low < ctx.ib_low and bar.close > ctx.ib_low:
        return 'failed_auction'

    # IVB breakout: price closed outside IB
    if bar.close > ctx.ib_high or bar.close < ctx.ib_low:
        return 'ivb_breakout'

    # Squeeze: big trades cluster near VP level, price inside IB
    if candidate.wall_trade_count >= 2 and candidate.proximity_to in ('lvn', 'poc', 'hvn'):
        return 'squeeze'

    return 'none'


def select_fabio_topics(candidate: CandidateBar,
                        knowledge_store: dict) -> list[str]:
    """Select relevant topics for Fabio based on candidate context.

    Args:
        candidate: The CandidateBar being analyzed
        knowledge_store: Dict merging simplified_strategy + knowledge_by_topic

    Returns:
        Ordered list of topic keys, trimmed to fit token budget.
    """
    setup = _infer_preliminary_setup(candidate)
    day = candidate.session_ctx.day_type
    prox = candidate.proximity_to

    topics = list(FABIO_CORE)
    topics.extend(FABIO_BY_SETUP.get(setup, []))
    topics.extend(FABIO_BY_DAY_TYPE.get(day, []))
    topics.extend(FABIO_BY_PROXIMITY.get(prox, []))

    # Extra: second test
    if candidate.is_second_test:
        topics.extend(FABIO_EXTRAS['second_test'])

    # Extra: large wall (>=100 contracts)
    if candidate.wall_max_size >= 100:
        topics.extend(FABIO_EXTRAS['high_wall'])

    # Extra: counter-trend (wall suggests direction against day_type)
    if (day == 'trend_up' and candidate.wall_side == 'bid') or \
       (day == 'trend_down' and candidate.wall_side == 'ask'):
        topics.extend(FABIO_EXTRAS['counter_trend'])

    topics = _dedupe(topics)

    # Trim to budget
    return _trim_to_budget(topics, knowledge_store)


def select_andrea_topics(candidate: CandidateBar,
                         fabio_setup: str,
                         knowledge_store: dict) -> list[str]:
    """Select relevant topics for Andrea based on candidate + Fabio's signal.

    Args:
        candidate: The CandidateBar being analyzed
        fabio_setup: setup_type from Fabio's signal (known at this point)
        knowledge_store: Dict merging simplified_strategy + knowledge_by_topic
    """
    day = candidate.session_ctx.day_type
    prox = candidate.proximity_to

    topics = list(ANDREA_CORE)
    topics.extend(ANDREA_BY_SETUP.get(fabio_setup, ANDREA_BY_SETUP['none']))
    topics.extend(ANDREA_BY_DAY_TYPE.get(day, []))
    topics.extend(ANDREA_BY_PROXIMITY.get(prox, []))

    topics = _dedupe(topics)
    return _trim_to_budget(topics, knowledge_store)


def _trim_to_budget(topics: list[str], store: dict) -> list[str]:
    """Keep topics until we hit MAX_KNOWLEDGE_CHARS."""
    result = []
    total = 0
    for t in topics:
        text = store.get(t, '')
        if not text:
            continue
        if total + len(text) > MAX_KNOWLEDGE_CHARS:
            break
        result.append(t)
        total += len(text)
    return result


def build_knowledge_text(topics: list[str], store: dict) -> str:
    """Build formatted knowledge string from selected topics."""
    parts = []
    for t in topics:
        if t in store:
            parts.append(f"### {t}\n{store[t]}\n")
    return '\n'.join(parts)


# Topics that belong to the simplified strategy (decision rules)
SIMPLIFIED_TOPICS = {
    'simplified_model_overview', 'simplified_ivb_formation', 'ivb_model_1', 'simplified_wall_definition',
    'simplified_second_drive_exact', 'simplified_entry_trigger', 'simplified_stop_exact',
    'simplified_target_exact', 'simplified_no_trade_top3', 'simplified_absorption_no_cvd',
    'simplified_breakeven_rule', 'simplified_day_type_quick', 'simplified_position_sizing',
    'simplified_reentry', 'myisto_pattern', 'simplified_real_trade_example',
    'initiative_vs_absorption',
    # Andrea simplified
    'ibob_overview', 'ibob_ib_timing', 'ibob_candle_close', 'ibob_bubble_body_vs_wick',
    'ibob_diagonal_imbalances', 'ibob_stop_target', 'ibob_invalidation',
    'ibob_no_trade_conditions', 'ibob_vs_full_system', 'simplified_big_trades_only',
    'simplified_day_filter', 'simplified_entry_mechanical', 'simplified_losing_trades',
    'simplified_position_risk',
}


def build_tiered_knowledge(topics: list[str], store: dict) -> tuple[str, str]:
    """Build knowledge split into rules (simplified) and context (deep).

    Returns:
        (rules_text, context_text) — rules are the decision framework,
        context is supplementary information that should not add new filters.
    """
    rules = []
    context = []
    for t in topics:
        if t not in store:
            continue
        if t in SIMPLIFIED_TOPICS:
            rules.append(f"### {t}\n{store[t]}\n")
        else:
            context.append(f"### {t}\n{store[t]}\n")
    return '\n'.join(rules), '\n'.join(context)
