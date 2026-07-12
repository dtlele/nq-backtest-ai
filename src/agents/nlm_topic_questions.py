"""
Topic-specific NLM question generator.

Generates precise, actionable questions for each knowledge topic.
These questions target the GAPS in current knowledge — what the agent
needs to make better trade/no-trade decisions.

Usage:
  questions = generate_topic_questions('fabio')
  # Then ask each via NLM MCP: mcp__notebooklm__ask_question

Each question maps to a specific topic key in the knowledge JSON.
Answers should be merged back into knowledge_by_topic or simplified_strategy.
"""

# ── FABIO: Questions per topic ────────────────────────────────────────────────
# Focus: fill gaps that affect trade decisions, not theoretical background

FABIO_TOPIC_QUESTIONS = {
    # === SQUEEZE mechanics (the core setup) ===
    'squeeze_definition': (
        "When Fabio identifies a squeeze, what is the MINIMUM number of big trade "
        "contracts that must cluster at a single level to qualify as a valid wall? "
        "Does he require 2+ separate big trades or is one large print sufficient?"
    ),
    'squeeze_entry_trigger': (
        "After Fabio identifies a squeeze wall, does he enter IMMEDIATELY when "
        "price reverses off the wall, or does he wait for a specific M1 candle "
        "close confirmation? What is the exact trigger — stop order or market order?"
    ),
    'squeeze_vs_failed_auction': (
        "Can a failed auction and a squeeze happen on the SAME bar? Specifically, "
        "if price wicks above IB high and closes back inside with massive sell big "
        "trades, is that ALREADY a valid short entry or must Fabio wait for a "
        "second drive down? Give a concrete example."
    ),
    'pre_explosion_pattern': (
        "In the pre-explosion pattern, Fabio mentions CVD divergence. But in the "
        "simplified model we removed CVD. Without CVD, what is the equivalent "
        "signal that pressure is building? Is delta alone sufficient, or does he "
        "need to see specific big trade sequences?"
    ),

    # === IVB / IB mechanics ===
    'ib_breakout_rules': (
        "After an IVB breakout, how many M5 bars must close OUTSIDE the IB range "
        "before Fabio considers it a confirmed breakout vs a false breakout? "
        "Is a single wick above IB high with close inside ever valid for a short?"
    ),
    'ib_extension_targets': (
        "What are the exact statistical extension targets from the IVB model? "
        "Give the specific multipliers or point levels: TP1 protection level, "
        "TP2 standard, TP3 extended. How does IB range size affect these?"
    ),
    'ib_bias': (
        "On a balance day when price oscillates around IB edges, does Fabio have "
        "a directional bias from the FIRST test of IB high/low, or only after "
        "a confirmed breakout? How does he handle the first 15-20 minutes?"
    ),

    # === Second drive ===
    'second_drive': (
        "In the second drive pattern, what is the MINIMUM retracement Fabio needs "
        "to see before the second leg? Is it measured in points, percentage of "
        "first drive, or does he just need price to return to a specific VP level? "
        "How many bars can pass between first and second drive?"
    ),

    # === Entry/Stop/Target precision ===
    'entry_mechanics': (
        "When Fabio uses buy-stop or sell-stop orders for entry, WHERE exactly "
        "does he place them relative to the big trade wall? 1 tick beyond the wall? "
        "At the wall level? At the M1 candle close beyond the wall?"
    ),
    'stop_placement': (
        "Fabio places stops behind the big trade wall. If the wall has 3 big "
        "trades at slightly different prices (e.g., 19981, 19983, 19984), does "
        "the stop go behind the HIGHEST one, the one with most contracts, or the "
        "cluster average? How many ticks of buffer?"
    ),
    'targets_standard': (
        "On a balance day, does Fabio always target the opposite IB edge, or does "
        "he sometimes use POC or VA boundary as TP1? What determines which level "
        "becomes the target? Does he ever use a fixed R:R like 1:2 instead?"
    ),
    'targets_high_volatility': (
        "On a strong trend day with IB range > 100 points, does Fabio shift to "
        "trailing stops instead of fixed targets? At what IB range or ATR level "
        "does he switch from standard to high-volatility target rules?"
    ),

    # === Trapped traders ===
    'trapped_buyers': (
        "How does Fabio identify trapped buyers on M1? Is it specifically when "
        "buy big trades appear in the wick above a resistance level and price "
        "closes back below? What delta threshold signals they are trapped?"
    ),
    'trapped_sellers': (
        "Same for trapped sellers — what is the M1 signature? Does he need to "
        "see sell big trades in the wick below support followed by a close above? "
        "How quickly must the trap spring — 1 bar, 2 bars, 5 bars?"
    ),

    # === Effort vs result ===
    'effort_vs_result': (
        "When 382 sell contracts hit at a level but price only drops 50 points "
        "before recovering — is that effort WITH result (valid sell) or effort "
        "WITHOUT result (absorption by buyers)? What price displacement per "
        "100 contracts does Fabio consider adequate result?"
    ),

    # === Day type / No trade ===
    'choppy_day_identification': (
        "What specific criteria does Fabio use in the FIRST 30 minutes to "
        "identify a choppy/no-trade day? Is it IB range size, number of "
        "reversals, or something about the big trade pattern?"
    ),
    'simplified_no_trade_top3': (
        "Of the top 3 no-trade conditions, which one catches the most false "
        "signals? On a balance day with a valid failed auction at IB high, "
        "does the balance day filter ALWAYS override, or can the failed auction "
        "signal be strong enough to trade despite balance classification?"
    ),

    # === A+ setup ===
    'aplus_setup': (
        "What makes a setup A+ vs B grade in Fabio's framework? Is it purely "
        "about the number of confirming big trades, or does the day type / IB "
        "range / time of day also factor in? Can a balance day ever produce "
        "an A+ setup?"
    ),

    # === Counter trend ===
    'counter_trend_rules': (
        "When price breaks IVB to the upside but Fabio sees massive sell big "
        "trades forming a wall above — does he EVER take a counter-trend short? "
        "If yes, what extra confirmations does he need beyond the standard model?"
    ),
}

# ── ANDREA: Questions per topic ───────────────────────────────────────────────

ANDREA_TOPIC_QUESTIONS = {
    'failed_auction_definition': (
        "In Andrea's framework, can a failed auction at IB high be confirmed "
        "on the SAME bar that makes the probe, or must price close inside IB "
        "on a SUBSEQUENT bar? What about a wick-only probe with close at the edge?"
    ),
    'failed_auction_variants': (
        "Andrea describes multiple failed auction types. Which variant applies "
        "when price probes above IB high with a large sell big trade cluster "
        "and closes back inside? Is that a Type 1 (immediate reversal) or does "
        "it need the next bar's confirmation?"
    ),
    'absorption_vs_exhaustion': (
        "When 382 sell contracts appear at a level and price drops sharply — "
        "is that absorption (sellers absorbing buy flow) or exhaustion "
        "(sellers dumping, done selling)? How does Andrea distinguish these "
        "two using ONLY the current bar's data?"
    ),
    'balance_vs_imbalance': (
        "On a balance day, what specific order flow signature would shift "
        "Andrea from 'no trade' to 'this is actually an imbalanced auction "
        "worth trading'? Is there a delta threshold or big trade count?"
    ),
    'institutional_activity': (
        "When Andrea sees institutional big trades on both sides (e.g., "
        "100 buy + 200 sell), does the NET direction matter or the SEQUENCE? "
        "If sells come AFTER buys, is that more bearish than if they come before?"
    ),
    'ibob_candle_close': (
        "For IBOB confirmation, Andrea requires candle close outside IB. "
        "Does a close EXACTLY at IB high/low count as outside or inside? "
        "What about close 0.25 points above — is 1 tick enough?"
    ),
    'ibob_invalidation': (
        "Once an IBOB signal is confirmed, what invalidates it? Does a "
        "single M5 bar closing back inside IB kill the signal, or does "
        "Andrea allow a brief pullback inside before the second drive?"
    ),
}


def generate_all_questions(agent: str = 'fabio') -> list[dict]:
    """Generate all topic questions for an agent.

    Returns list of {topic, question, notebook_id} dicts.
    """
    if agent == 'fabio':
        questions = FABIO_TOPIC_QUESTIONS
        nb_id = 'fabio-valentini-order-flow-squ'
    elif agent == 'andrea':
        questions = ANDREA_TOPIC_QUESTIONS
        nb_id = 'andrea-cimi-amt-order-flow'
    else:
        raise ValueError(f"Unknown agent: {agent}")

    return [
        {'topic': topic, 'question': question, 'notebook_id': nb_id}
        for topic, question in questions.items()
    ]


def generate_priority_questions(agent: str = 'fabio', max_questions: int = 10) -> list[dict]:
    """Generate only the highest-priority questions.

    Priority is based on which topics most affect trade decisions:
    1. Entry/exit mechanics (directly affect P&L)
    2. Setup validation (affect trade/no-trade decision)
    3. Day type filters (affect candidate selection)
    """
    priority_order_fabio = [
        'squeeze_vs_failed_auction',   # #1: this caused the conf=65→15 regression
        'simplified_no_trade_top3',    # #2: balance day override vs strong signal
        'squeeze_entry_trigger',       # #3: exact entry timing
        'stop_placement',              # #4: M1 stop precision
        'entry_mechanics',             # #5: stop order vs market order
        'effort_vs_result',            # #6: what counts as valid displacement
        'ib_breakout_rules',           # #7: confirmed vs false breakout
        'second_drive',                # #8: retracement requirements
        'targets_standard',            # #9: target selection on balance day
        'trapped_buyers',              # #10: M1 trap identification
        'squeeze_definition',
        'aplus_setup',
        'counter_trend_rules',
        'ib_extension_targets',
        'pre_explosion_pattern',
        'targets_high_volatility',
        'trapped_sellers',
        'choppy_day_identification',
        'ib_bias',
    ]

    priority_order_andrea = [
        'failed_auction_definition',
        'failed_auction_variants',
        'absorption_vs_exhaustion',
        'ibob_candle_close',
        'ibob_invalidation',
        'balance_vs_imbalance',
        'institutional_activity',
    ]

    order = priority_order_fabio if agent == 'fabio' else priority_order_andrea
    questions = FABIO_TOPIC_QUESTIONS if agent == 'fabio' else ANDREA_TOPIC_QUESTIONS
    nb_id = 'fabio-valentini-order-flow-squ' if agent == 'fabio' else 'andrea-cimi-amt-order-flow'

    result = []
    for topic in order[:max_questions]:
        if topic in questions:
            result.append({
                'topic': topic,
                'question': questions[topic],
                'notebook_id': nb_id,
            })
    return result
