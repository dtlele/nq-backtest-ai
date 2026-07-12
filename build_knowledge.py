"""
Phase 1 — Knowledge Extraction Agent
Interrogates each NotebookLM notebook systematically and produces a structured
knowledge JSON file for each trading agent.

Usage:
    python build_knowledge.py --agent andrea
    python build_knowledge.py --agent fabio
    python build_knowledge.py --agent all
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ─── Notebook IDs ────────────────────────────────────────────────────────────
NOTEBOOKS = {
    "andrea":    "5204f969",
    "fabio":     "4c868e52",
    "composite": "c6ce7147",
}

OUTPUT_DIR = Path(__file__).parent / "knowledge"

# ─── Question Banks ───────────────────────────────────────────────────────────

ANDREA_QUESTIONS = [
    # ── Market Structure ──────────────────────────────────────────────────────
    ("pbd_shapes",
     "Describe Andrea Cimi's PBD method in full detail: what does a P-shape, B-shape, and D-shape look like in terms of price action + volume profile? How do you identify each one in real time?"),

    ("value_area_definition",
     "What exact percentage defines the Value Area? How does Andrea define VA High, VA Low, and POC? Are these computed from a single session or multiple sessions?"),

    ("hvn_lvn",
     "What are HVN (High Volume Nodes) and LVN (Low Volume Nodes)? How does Andrea use them as support/resistance? Give specific examples of entries at HVN and fast transit through LVN."),

    ("balance_vs_imbalance",
     "How does Andrea define balance vs imbalance in Auction Market Theory? What price behavior distinguishes a balanced market from an imbalanced one? How does this affect trade direction?"),

    ("range_acceptance",
     "What is 'range acceptance' in Andrea's methodology? How much time or how many bars must price spend outside a level before it's 'accepted'? Without acceptance, what does he do?"),

    ("composite_profile",
     "Does Andrea use a multi-day composite volume profile? How many days? What decisions does composite VP influence that single-session VP does not?"),

    # ── Failed Auction ────────────────────────────────────────────────────────
    ("failed_auction_definition",
     "Describe the Failed Auction concept in complete detail: definition, how it forms, what makes it 'fail', and what the precise entry trigger is (candle close? retest? break-in?)."),

    ("failed_auction_variants",
     "Are there different types of failed auctions in Andrea's system? For example: failed auction at VA edge vs at POC vs at a prior session high/low. Do the rules differ?"),

    ("absorption_vs_exhaustion",
     "What is the difference between 'absorption' and 'exhaustion' in Andrea's framework? How does each appear in the delta footprint? Which one leads to a faster reversal?"),

    # ── Orderflow & Delta ─────────────────────────────────────────────────────
    ("delta_thresholds",
     "What are Andrea Cimi's EXACT delta percentage thresholds? At what % is a candle considered 'initiative'? At what % is it 'absorbed'? At what % is it 'not meaningful'? Give numbers."),

    ("cvd_divergence",
     "Explain CVD divergence in Andrea's system with exact examples: price makes new high + CVD lower high = what signal? Price makes new low + CVD higher low = what signal? How many bars back does the divergence need to be?"),

    ("initiative_vs_response",
     "What is the R&I (Response and Initiative) cycle? How does Andrea identify when a Response phase ends and an Initiative phase begins? What orderflow signature marks the transition?"),

    ("bolle_filter",
     "What are 'bolle' (bubbles)? What exact contract size filter does Andrea use on NQ to isolate institutional trades? What is the difference between seeing 300-contract bubbles vs 2000-contract icebergs?"),

    ("footprint_reading",
     "How does Andrea read a footprint chart (MBO orderflow)? What patterns in the bid/ask footprint signal that a big player is absorbing? What does 'book sweeping' look like in the footprint?"),

    ("toxic_flow",
     "What is 'toxic flow' in Andrea's vocabulary? What CVD behavior and volume level per bar characterizes it? Is toxic flow tradeable or a no-trade condition?"),

    # ── Entry Rules ───────────────────────────────────────────────────────────
    ("entry_pbd_p",
     "For a P-shape setup, what is the EXACT entry rule? Break-in, close inside, or something else? What must the delta show at entry? Where is the stop and target?"),

    ("entry_pbd_b",
     "For a B-shape setup, what is the EXACT entry rule? Describe step by step: what must happen before entry, the trigger candle, stop placement, target."),

    ("entry_failed_auction",
     "For a Failed Auction entry, describe the step-by-step sequence: (1) price exits range, (2) what happens next, (3) entry trigger, (4) stop, (5) target. Be very specific."),

    ("entry_iceberg",
     "For an iceberg/absorption trade, what is the entry? Do you enter at the iceberg level, above/below it, or on confirmation? What delta pattern confirms the iceberg is holding?"),

    ("second_drive_andrea",
     "Does Andrea Cimi also use a 'second drive' concept (don't trade first breakout, wait for second test)? If so, describe exactly when and how."),

    # ── Stop & Target ─────────────────────────────────────────────────────────
    ("stop_placement_all",
     "For EACH setup type (PBD-P, PBD-B, PBD-D, Failed Auction, Iceberg), where exactly does Andrea place his stop? How many ticks? What reference level?"),

    ("target_rules",
     "What are Andrea's profit targets for each setup? Does he always target the opposite VA edge? When does he use POC as target? Does he scale out at multiple levels?"),

    ("rr_ratio",
     "What minimum R:R ratio does Andrea require before entering a trade? Does the required R:R differ by setup quality (A+ vs B)?"),

    ("trade_management",
     "Does Andrea trail his stop? Move to break-even? Scale out? Describe his full trade management approach after entry."),

    # ── Sessions & Filters ────────────────────────────────────────────────────
    ("session_times",
     "Which sessions does Andrea trade on NQ? NY open (09:30 EST)? London? Asian? What are the EXACT hours he is active vs inactive?"),

    ("volume_floor",
     "What is the minimum volume per bar to consider a trade on NQ? Andrea mentions 3000 contracts as 'negligible' - what is his actual trading threshold?"),

    ("no_trade_rules",
     "List EVERY no-trade condition Andrea mentions: news events, time of day, volume, market structure, delta conditions. Be exhaustive."),

    ("lunch_effect",
     "What happens during NY lunch (12:00-13:30 EST) in Andrea's experience? Does he sometimes trade it or is it a hard rule to stay out?"),

    # ── Trend vs Mean Reversion ───────────────────────────────────────────────
    ("day_type_classification",
     "How does Andrea classify the type of day (trending, balanced, volatile) before and during the session? What early signals determine which mode he operates in?"),

    ("trend_day_rules",
     "On a trend day (strong initiative, price discovery), does Andrea trade in the direction of the trend or fade it? What changes in his approach vs a balanced day?"),

    ("overnight_gaps",
     "What does Andrea say about overnight gaps and their interaction with the previous day's Value Area? Does he trade gap fills specifically?"),

    # ── Advanced Concepts ────────────────────────────────────────────────────
    ("institutional_activity",
     "How does Andrea identify institutional (smart money) activity vs retail noise? What contract sizes, what orderflow patterns, what time of day are institutional?"),

    ("squeeze_setup_andrea",
     "Does Andrea also trade 'squeeze' setups (trapped participants forced to cover)? How does his version differ from Fabio's?"),

    ("rotation_within_va",
     "When price is rotating INSIDE the Value Area (D-shape), what are the specific rules for fading VA High and VA Low? What orderflow confirms the fade?"),

    ("multi_timeframe",
     "Does Andrea use multiple timeframes? If so, which ones and how do they interact? For example: 5-min for context + 1-min for entry?"),

    ("losing_trade_characteristics",
     "What does a losing trade look like in Andrea's system? What went wrong in retrospect? What signals, if seen in real time, would have indicated the trade was wrong?"),

    ("best_setups_statistics",
     "Does Andrea mention the win rate or statistical edge for any of his specific setups? Which setup has the highest win rate?"),
]

FABIO_QUESTIONS = [
    # ── Core Model: Squeeze ───────────────────────────────────────────────────
    ("squeeze_definition",
     "Describe Fabio Valentini's 'squeeze' concept in complete detail: what is a squeeze, how does it form from trapped participants, and what is the pre-explosion signature?"),

    ("squeeze_entry_trigger",
     "What is the EXACT entry trigger for a squeeze trade? Is it when price breaks a level, when a candle closes, or when a specific delta pattern appears? Give step-by-step rules."),

    ("squeeze_vs_failed_auction",
     "How does Fabio's squeeze setup relate to a failed auction? Are they the same thing or different? When does a failed auction become a squeeze setup?"),

    ("pre_explosion_pattern",
     "What does the 'pre-explosion' pattern look like in Fabio's system? What specific delta, CVD, and price behavior precedes the explosive move?"),

    # ── Initial Balance ───────────────────────────────────────────────────────
    ("ib_definition",
     "What exact timeframe defines Fabio's Initial Balance (IB)? First 15 min? 30 min? 60 min? Is this fixed or variable based on market conditions?"),

    ("ib_breakout_rules",
     "What are the EXACT rules for trading an IB breakout? When is it valid vs a false breakout? What orderflow must confirm? How long after the breakout can you still enter?"),

    ("ib_bias",
     "How does Fabio use the IB to determine daily directional bias? If price is above IB midpoint at 10:00 EST, what does he assume? What invalidates the bias?"),

    ("ib_extension_targets",
     "What are Fabio's price targets after an IB breakout? Does he use 1x IB extension? 2x? Or does he use VA edges? What's the statistical probability he mentions?"),

    # ── Trapped Participants ──────────────────────────────────────────────────
    ("trapped_buyers",
     "How does Fabio identify trapped buyers? What does the delta footprint show when buyers are trapped at a high? Walk through a specific example."),

    ("trapped_sellers",
     "How does Fabio identify trapped sellers? What does the delta footprint show when sellers are trapped at a low? Walk through a specific example."),

    ("punches_to_wall",
     "What is a 'punch to the wall' (colpo al muro) in Fabio's vocabulary? How many punches are needed before the level breaks? What volume and delta confirm each punch?"),

    # ── Orderflow Tools ───────────────────────────────────────────────────────
    ("big_trades_filter",
     "What is Fabio's exact 'big trades' or 'deep trades' filter on NQ? What contract size threshold? What does it look like on screen? How does he use the 'wall' formed by these trades?"),

    ("effort_vs_result",
     "Explain Fabio's 'effort vs result' (VSA) concept with specific numbers: what volume constitutes high effort? What price movement is low result? Give a bullish and bearish example."),

    ("cvd_as_leading_indicator",
     "How does Fabio use CVD as a LEADING indicator? What does 'building pressure' look like? Give specific examples: CVD trending down while price is flat = what does Fabio expect?"),

    ("footprint_delta",
     "How does Fabio read the delta footprint bar by bar? What specific patterns (absorption at bid/ask, stacked imbalances, diagonal) does he look for and what do they mean?"),

    ("coherence_of_information",
     "What is 'coherence of information' in Fabio's framework? What must align for a signal to be valid? Give examples of coherent vs incoherent signals."),

    # ── Second Drive & Entry ──────────────────────────────────────────────────
    ("second_drive",
     "What is Fabio's 'second drive' rule? Why never trade the first breakout attempt? How do you identify the second drive and what makes it tradeable vs just another fake?"),

    ("aplus_setup",
     "What EXACTLY is an A+ setup for Fabio? List every confluence required. What makes it A vs B vs C quality? What are the position size rules for each grade?"),

    ("entry_mechanics",
     "Describe Fabio's entry mechanics precisely: does he enter at market on a candle close, use a limit order at a big trade level, or wait for confirmation? Any specific candle patterns?"),

    ("counter_trend_rules",
     "Does Fabio ever trade counter-trend? What conditions make a counter-trend trade acceptable? How does he adjust his rules (smaller size, tighter stop)?"),

    # ── Stop & Risk Management ────────────────────────────────────────────────
    ("stop_placement",
     "Where exactly does Fabio place his stop? Behind which 'wall' of big trades? How many ticks past the wall? What if there are multiple potential stop levels?"),

    ("breakeven_rules",
     "When does Fabio move his stop to break-even? What market action triggers this move? Does he use a time-based or price-based rule, or orderflow-based?"),

    ("trailing_stop",
     "How does Fabio trail his stop in a winning trade? What does 'stopping in profit' mean specifically? Does he trail behind new big trade clusters?"),

    ("max_daily_loss",
     "Does Fabio mention a maximum daily loss or daily stop? What is it? Does he mention a maximum profit target (daily goal)?"),

    # ── Targets ──────────────────────────────────────────────────────────────
    ("targets_standard",
     "What are Fabio's standard profit targets for a typical trade? What R:R does he aim for on a normal day?"),

    ("targets_high_volatility",
     "In high-volatility sessions (like post-NFP, post-CPI, strong trend days), how does Fabio's target selection change? When does he aim for 1:10+ R:R?"),

    ("partial_exits",
     "Does Fabio take partial profits? Does he scale out at multiple targets? What is his scaling approach if yes?"),

    # ── Position Building ─────────────────────────────────────────────────────
    ("position_building",
     "Describe Fabio's 'position building' technique: how does he start with small size and increase? What triggers adding to a winning position vs taking profit?"),

    ("risk_per_trade",
     "What dollar risk does Fabio use per trade for A+, A, B, and C setups? Give specific numbers he has mentioned."),

    # ── Sessions & Timing ─────────────────────────────────────────────────────
    ("session_schedule",
     "What are the EXACT hours Fabio trades? When does he start? When does he stop? What is the '3:30 PM shakeout' and how does he handle the NY open?"),

    ("avoid_times",
     "List ALL times/conditions Fabio explicitly avoids: pre-open, lunch, news events, late session, specific days of week, etc."),

    ("choppy_day_identification",
     "How does Fabio identify a 'choppy day' or 'balance day' where he should not trade his model? What early signals (first 30-60 min) tell him it's a no-trade day?"),

    # ── Statistical Edge ──────────────────────────────────────────────────────
    ("statistical_levels",
     "What is Fabio's statistical algorithm and 'protection levels'? What probability does he assign to his targets reaching VA edges? How is this calculated?"),

    ("world_cup_performance",
     "What specific trades or statistics from Fabio's Robbins World Cup performance does he discuss? What was his approximate return and what setups did he use most?"),

    ("win_rate_by_setup",
     "Does Fabio mention the win rate or edge statistics for specific setups? Which setups have the best historical performance in his experience?"),

    # ── Advanced ──────────────────────────────────────────────────────────────
    ("losing_trade_anatomy",
     "What does a losing trade look like in Fabio's system? What went wrong in hindsight? What real-time signals should have been a warning to avoid or exit early?"),

    ("multi_timeframe",
     "Does Fabio use multiple timeframes? How do the higher timeframe (30-min, daily) VP levels interact with the 1-min or 5-min execution timeframe?"),
]

# ─── Simplified Live Strategy Questions ───────────────────────────────────────
# Focus: model as taught in Chart Fanatics live sessions and recent videos.
# NO CVD, NO multi-TF. Only: Big Trades bubbles + IVB + Volume Profile.

ANDREA_SIMPLIFIED = [
    ("ibob_overview",
     "Describe your IBOB (Initial Balance Orderflow Breakout) method exactly as you present it in live sessions and recent videos. Give the exact 3-4 non-negotiable conditions in order. This is the simplified model, not the full PBD system."),

    ("ibob_ib_timing",
     "In IBOB: what exact time window defines the Initial Balance on NQ? Does it start at 9:30 AM EST exactly? When is the IB 'closed' and you can start looking for a breakout? Is it always 15 minutes or variable?"),

    ("ibob_candle_close",
     "In IBOB: the breakout requires a candle to CLOSE outside the IB range. What makes this close 'valid'? Must the full body be outside, or just the close price? Is there a minimum distance required? Does the candle size matter?"),

    ("ibob_bubble_body_vs_wick",
     "In IBOB: the big bubble (institutional order) must appear in the BODY of the breakout candle, NOT on the wick. Explain this distinction visually and mechanically. What does a bubble on the wick signal? What does a bubble in the body signal? Why does it disqualify a trade?"),

    ("ibob_diagonal_imbalances",
     "In IBOB: you require a cluster of 'diagonal imbalances' in the footprint of the breakout candle. What exactly are diagonal imbalances? How many minimum? What do they look like on screen? Are they stacked bid/ask imbalances at consecutive price levels?"),

    ("ibob_stop_target",
     "In IBOB: where exactly is the stop placed (below IB low / above IB high, and how many ticks buffer)? What is the profit target - 1x IB extension, 2x, or a specific structural level? What is the minimum R:R you accept?"),

    ("ibob_invalidation",
     "When does an IBOB trade fail or get invalidated AFTER entry? What real-time signals tell you the trade is wrong and you should exit before the stop? Give specific examples."),

    ("ibob_no_trade_conditions",
     "What conditions disqualify an IBOB setup even if all 4 criteria are technically met? List every no-trade filter for IBOB: volume, time of day, news, market structure issues."),

    ("ibob_vs_full_system",
     "How does IBOB differ from your full PBD system? What did you deliberately REMOVE to make IBOB simple enough for live teaching? What complexity did you strip away?"),

    ("simplified_big_trades_only",
     "In your most recent simplified approach (as seen in live sessions): if you had to trade with ONLY volume profile + big trades bubbles and nothing else, what would be the exact entry rule? What minimum do you need?"),

    ("simplified_day_filter",
     "In the simplified model: how do you decide in the first 15-30 minutes whether it is a tradeable day? What do you look at specifically to say 'today I trade IBOB' vs 'today I stay out'?"),

    ("simplified_entry_mechanical",
     "Give the most mechanical possible entry rule for IBOB: a computer program must know exactly WHEN to enter (which event triggers the order), at what price, with what stop distance. No discretion allowed."),

    ("simplified_losing_trades",
     "In the simplified IBOB model: what is the most common reason a trade loses? What was wrong about the setup in hindsight? What real-time warning signs exist?"),

    ("simplified_position_risk",
     "In the simplified model: what is the standard risk per trade? Fixed points, fixed dollar amount, or percentage of account? What changes the size (setup quality, market condition)?"),

    ("simplified_reentry",
     "In IBOB: if the first trade gets stopped out, do you look for re-entry on the same setup? What are the rules for a second attempt vs stopping the session?"),
]

FABIO_SIMPLIFIED = [
    ("simplified_model_overview",
     "Describe your simplest orderflow model as shown in recent live sessions and the video 'The Simplest Orderflow Trading Model'. What are the 3-4 exact conditions - no CVD required, just the core signals: IVB + big trades + second drive?"),

    ("simplified_ivb_formation",
     "In the simplified model: what exactly defines a valid IVB? First 15 minutes from 9:30 AM? What makes the IVB 'clean' and trustworthy for the day's bias? What makes you distrust it and skip the day?"),

    ("simplified_wall_definition",
     "In the simplified model: what makes a 'wall' valid? Minimum number of big trade bubbles (>= 30 contracts NQ) at a level? How clustered must they be? Over how many bars? What price range do they span?"),

    ("simplified_second_drive_exact",
     "In the simplified model: describe the second drive rule with exact mechanics. What does the FIRST drive look like (price, volume, time)? What must happen on the second drive to trigger entry? Is there a time limit between first and second drive?"),

    ("simplified_entry_trigger",
     "In the simplified model: what is the EXACT entry trigger? Market order at the close of a specific candle? Limit order at the wall level? What candle pattern or event pulls the trigger?"),

    ("simplified_stop_exact",
     "In the simplified model: where exactly is the stop? One tick behind the lowest/highest big trade bubble? Behind the lowest point of the wall cluster? Give the exact rule with no ambiguity."),

    ("simplified_target_exact",
     "In the simplified model: what is the target? Is it always 1:3 R:R? Or the first LVN? Or the POC? Or the opposite IVB edge? What does Fabio say in recent live sessions about where he takes profit?"),

    ("simplified_no_trade_top3",
     "In the simplified model: what are the TOP 3 absolute no-trade conditions? The situations where no matter how good the setup looks, you simply do not trade. Give the 3 most important rules."),

    ("simplified_absorption_no_cvd",
     "In the simplified model (no CVD): how do you identify absorption without looking at CVD? What do the big trade bubbles show when absorption is happening? What does 'high volume, no price progress' look like just using bubbles?"),

    ("simplified_breakeven_rule",
     "In the simplified model: when exactly do you move the stop to break-even? After reaching a specific R:R? After a specific candle close? After a specific time? Give the exact rule."),

    ("simplified_day_type_quick",
     "In the simplified model: how do you determine in the first 15-30 minutes whether it is a squeeze day, IVB breakout day, or a no-trade day? What are the exact signals for each classification?"),

    ("simplified_position_sizing",
     "In the simplified model: how does position sizing work? Fixed contracts? Based on setup quality (A+ vs regular)? What is the typical size for an A+ setup? For a normal setup?"),

    ("simplified_reentry",
     "In the simplified model: if you get stopped out on a squeeze or IVB trade, do you look for re-entry? What are the exact rules for re-entering vs stopping the session for the day?"),

    ("myisto_pattern",
     "What is the 'Myisto' pattern you mention in your model? Is it part of the simplified approach? If yes, describe it step by step: what does it look like, what triggers it, how do you enter?"),

    ("simplified_real_trade_example",
     "Describe 1-2 specific trade examples from your recent live sessions using the simplified model: exact setup, what you saw on screen (bubbles, IVB, price), what you did, and what happened. Be very specific."),
]


# ─── Core Functions ───────────────────────────────────────────────────────────

def nlm_ask(question: str, retry: int = 0) -> str:
    """Call notebooklm ask via CLI and return the answer text.
    Auto-detects auth expiry (short response) and prompts user to re-login."""
    result = subprocess.run(
        [sys.executable, "-m", "notebooklm", "ask", question],
        capture_output=True, text=True, timeout=120
    )
    output = result.stdout.strip()
    combined = output + result.stderr.strip()

    # Detect auth expiry from either stdout or stderr
    is_auth_error = (
        "Authentication expired" in combined
        or "notebooklm login" in combined
        or "accounts.google.com" in combined
    )
    if is_auth_error:
        raise RuntimeError(f"[AUTH EXPIRED] Run 'python -m notebooklm login' then re-run this script.")

    # Strip the "Answer:" prefix if present
    if output.startswith("Answer:"):
        output = output[7:].strip()
    # Strip the "Conversation: ..." footer
    for marker in ["\nConversation:", "\nResumed conversation:", "\nContinuing conversation"]:
        if marker in output:
            output = output[:output.rfind(marker)].strip()
    return output


def nlm_use(notebook_id: str) -> bool:
    """Select a notebook."""
    result = subprocess.run(
        [sys.executable, "-m", "notebooklm", "use", notebook_id],
        capture_output=True, text=True, timeout=30
    )
    return result.returncode == 0


def load_existing_knowledge(agent_name: str) -> dict | None:
    """Load existing knowledge file if it exists."""
    path = OUTPUT_DIR / f"{agent_name}_knowledge.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def extract_knowledge(agent_name: str, notebook_id: str, questions: list,
                      section: str = "knowledge_by_topic") -> dict:
    """Run all questions against the notebook and build knowledge document.
    section: 'knowledge_by_topic' for full system, 'simplified_strategy' for live model.
    """
    print(f"\n{'='*60}")
    print(f"Extracting [{section}]: {agent_name} (notebook: {notebook_id})", flush=True)
    print(f"{'='*60}\n")

    if not nlm_use(notebook_id):
        print(f"ERROR: Could not select notebook {notebook_id}")
        return {}

    # Resume from existing — skip already-good topics in this section
    existing = load_existing_knowledge(agent_name)
    if existing:
        section_data = existing.get(section, {})
        knowledge_by_topic = existing.get("knowledge_by_topic", {})
        qa_log = existing.get("qa_log", [])
        skipped = [t for t, v in section_data.items() if len(v) >= 200]
        if skipped:
            print(f"  Resuming: skipping {len(skipped)} already-complete topics in [{section}]")
    else:
        section_data = {}
        knowledge_by_topic = {}
        qa_log = []

    for topic, question in questions:
        if section_data.get(topic, "") and len(section_data[topic]) >= 200:
            print(f"  [{topic}] SKIP (already complete)")
            continue
        print(f"  [{topic}] Asking...", end=" ", flush=True)
        answer = nlm_ask(question)
        print(f"OK ({len(answer)} chars)")
        qa_log.append({"section": section, "topic": topic, "question": question, "answer": answer})
        section_data[topic] = answer

    # Synthesis only for full extraction
    gaps_answer = existing.get("gaps_and_unknowns", "") if existing else ""
    needs_answer = existing.get("required_data_inputs", "") if existing else ""

    if section == "knowledge_by_topic":
        print(f"  [synthesis] Summarizing gaps...", end=" ", flush=True)
        gaps_q = (
            "Based on everything you know about this trader's methodology, "
            "what are the 3-5 most important things that are NOT clearly defined "
            "or that require additional sources to clarify? "
            "Also: what data inputs does this agent absolutely need to make a decision on each bar?"
        )
        gaps_answer = nlm_ask(gaps_q)
        print(f"OK")

        needs_q = (
            "For an automated trading agent using this methodology, list EXACTLY "
            "what market data it needs per bar to make a trade decision. "
            "Format as a list: one item per line, be specific (e.g. 'delta_pct of current 1-min bar', "
            "'list of big trades (size, price, side) in current bar', "
            "'distance from IB_high in ticks', etc.) — focus on the SIMPLIFIED live model only."
        )
        print(f"  [data_needs] Asking...", end=" ", flush=True)
        needs_answer = nlm_ask(needs_q)
        print(f"OK")

    # Merge back into existing knowledge structure
    if existing:
        knowledge = existing.copy()
    else:
        knowledge = {
            "agent": agent_name,
            "notebook_id": notebook_id,
            "knowledge_by_topic": {},
            "simplified_strategy": {},
            "gaps_and_unknowns": "",
            "required_data_inputs": "",
            "qa_log": [],
        }

    knowledge["extracted_at"] = datetime.now().isoformat()
    knowledge[section] = section_data
    knowledge["gaps_and_unknowns"] = gaps_answer
    knowledge["required_data_inputs"] = needs_answer
    knowledge["qa_log"] = qa_log

    return knowledge


def save_knowledge(knowledge: dict, agent_name: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{agent_name}_knowledge.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(knowledge, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {path}")
    return path


def print_summary(knowledge: dict) -> None:
    agent = knowledge.get("agent", "?")
    topics = list(knowledge.get("knowledge_by_topic", {}).keys())
    print(f"\n{'='*60}")
    print(f"KNOWLEDGE SUMMARY --- {agent.upper()}")
    print(f"{'='*60}")
    print(f"Topics covered: {len(topics)}")
    for t in topics:
        ans = knowledge["knowledge_by_topic"][t]
        preview = ans[:120].replace('\n', ' ')
        print(f"  {t:25s}: {preview}...")
    print(f"\nGaps/Unknowns:\n{knowledge.get('gaps_and_unknowns','')[:400]}")
    print(f"\nRequired Data Inputs:\n{knowledge.get('required_data_inputs','')[:400]}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract trading knowledge from NotebookLM")
    parser.add_argument("--agent", choices=["andrea", "fabio", "all"], default="all")
    parser.add_argument("--mode", choices=["full", "simplified", "both"], default="simplified",
                        help="full=original 37 questions, simplified=live strategy questions, both=all")
    args = parser.parse_args()

    agents_to_run = ["andrea", "fabio"] if args.agent == "all" else [args.agent]

    for agent in agents_to_run:
        notebook_id = NOTEBOOKS[agent]
        full_qs = ANDREA_QUESTIONS if agent == "andrea" else FABIO_QUESTIONS
        simplified_qs = ANDREA_SIMPLIFIED if agent == "andrea" else FABIO_SIMPLIFIED

        knowledge = None

        if args.mode in ("full", "both"):
            knowledge = extract_knowledge(agent, notebook_id, full_qs, section="knowledge_by_topic")
            if knowledge:
                save_knowledge(knowledge, agent)

        if args.mode in ("simplified", "both"):
            knowledge = extract_knowledge(agent, notebook_id, simplified_qs, section="simplified_strategy")
            if knowledge:
                save_knowledge(knowledge, agent)

        if knowledge:
            print_summary(knowledge)
        else:
            print(f"ERROR: No knowledge extracted for {agent}")


if __name__ == "__main__":
    main()
