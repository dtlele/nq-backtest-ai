"""
Phase 2 — Knowledge Gap Filler
Targeted questions derived from 5-day backtest analysis + VP definition audit.

Groups questions by agent and notebook, asks them in bulk (one NLM session),
and merges answers into the existing knowledge JSON.

Usage:
    python build_knowledge_v2.py                    # all agents
    python build_knowledge_v2.py --agent fabio      # fabio only
    python build_knowledge_v2.py --agent andrea     # andrea only
    python build_knowledge_v2.py --dry-run          # show questions without asking
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

NOTEBOOKS = {
    "fabio":  "4c868e52",
    "andrea": "5204f969",
}

OUTPUT_DIR = Path(__file__).parent / "knowledge"

# ── FABIO GAP QUESTIONS ──────────────────────────────────────────────────────
# Derived from: backtest gap analysis + VP audit

FABIO_GAP_QUESTIONS = [
    # ── Balance Day Exceptions (CRITICAL: 100% winning trades were balance day) ──
    ("balance_day_exceptions",
     "In your simplified model, you say balance days have no edge. "
     "But in backtesting, the ONLY winning trade was a squeeze on a balance day "
     "(382 sell contracts at IVB high, failed auction, conf 65). "
     "In which SPECIFIC situations does a balance day still produce a valid squeeze or trade? "
     "What makes a balance day 'tradeable despite being balance'? "
     "Give concrete conditions: wall size, failed auction signature, delta threshold."),

    ("balance_vs_failed_auction",
     "What is the difference between a balance day where you do NOT trade "
     "and a balance day where a failed auction at the IVB edge creates a valid squeeze? "
     "The failed auction seems to override the 'balance = no trade' rule. "
     "Is that correct? What are the exact conditions for this override?"),

    # ── Wall Size Thresholds ──
    ("wall_size_minimum_balance",
     "On a balance day, what is the MINIMUM wall size (total big trade contracts) "
     "that makes you consider a trade despite the balance classification? "
     "In backtesting we saw: 382 contracts → trade taken, 120 contracts → skipped, "
     "455 contracts at HVN → skipped (conf 18). "
     "Is there a number threshold, or is it purely contextual?"),

    # ── First Drive vs Failed Auction as Setup ──
    ("failed_auction_is_the_setup",
     "In the simplified model you wait for second drive after first breakout. "
     "But the winning backtest trade was a failed auction (probe above IVB high, "
     "crushed back inside by 382 sell contracts). There was no 'first drive + retracement + second drive' — "
     "the failed auction itself WAS the setup. "
     "Is a failed auction at IVB edge a valid standalone entry WITHOUT waiting for second drive? "
     "What are the exact conditions?"),

    # ── Counter-Trend on Trend Day ──
    ("counter_trend_on_trend_day",
     "On a trend_up day, we saw a wall of 114 sell contracts near an LVN, "
     "but confidence was only 22 because it was against the trend. "
     "In which situations do you take a counter-trend trade on a trend day? "
     "What wall size, what orderflow signature, what structural pattern "
     "overrides the 'don't fade the trend' rule?"),

    # ── HVN Behavior ──
    ("hvn_big_wall_rules",
     "On May 1st at 10:15, there was a wall of 455 contracts at an HVN, "
     "but you gave conf=18 because 'no breakout occurred, price inside IVB'. "
     "When a MASSIVE wall forms at an HVN while price is inside IVB, "
     "what does it mean? Is it always a no-trade? "
     "Or can it be a setup (accumulation/distribution) that becomes tradeable later?"),

    # ── Confidence Calibration ──
    ("confidence_40_60_zone",
     "In backtesting, almost all candidates get either conf < 30 or conf 65+. "
     "There is almost no 40-60 zone. "
     "What setups should realistically produce confidence 40-60? "
     "What is 'almost there but not quite' — what single missing element "
     "would push a 50 to a 65?"),

    # ── Time Decay and Repeated Tests ──
    ("repeated_level_test",
     "If a level is tested at 09:50 with a wall of 60 contracts (conf 40), "
     "and then tested again at 10:15 with a bigger wall of 120 contracts, "
     "is the second test MORE valid (bigger wall, level confirmed) "
     "or LESS valid (level has been 'used up', trapped traders already exited)? "
     "How does time affect a setup's validity?"),

    # ── VP Definition: IVB Duration ──
    ("ivb_15_vs_30_minutes",
     "In recent live sessions and videos, do you define the IVB as the first 15 minutes "
     "or the first 30 minutes of the NY session? "
     "Has this changed over time? "
     "Is it ever variable based on how quickly the opening auction resolves?"),

    # ── VP Definition: Which Session ──
    ("vp_session_scope",
     "When you say 'Value Area' and 'POC' during an intraday trade decision, "
     "are you referring to: "
     "(a) the developing VP of the CURRENT session (from 09:30 onward), "
     "(b) the VP of the PREVIOUS NY cash session (yesterday), "
     "(c) a multi-day composite (e.g., 90-day), or "
     "(d) a combination? "
     "Please specify which VP you use for EACH of these decisions: "
     "1) determining day type (balance/trend), "
     "2) finding entry levels (LVN, POC proximity), "
     "3) setting targets (VA edge, POC)."),

    # ── VP Definition: Composite ──
    ("composite_vs_session_vp",
     "You mention 90-day composite profiles for macro context. "
     "Do you also use them for intraday levels? "
     "For example: if today's developing POC is at 20100 but the 90-day composite POC is at 19950, "
     "which one matters for a squeeze target? "
     "When do composite levels override session levels?"),

    # ── VP Definition: Overnight Data ──
    ("vp_includes_overnight",
     "When you compute the session VP, do you include Globex/overnight data "
     "(Asian session, London session) or only the NY cash session (09:30-16:00 EST)? "
     "For the IVB specifically, do overnight highs/lows matter?"),
]

# ── FABIO ROUND 3 QUESTIONS ──────────────────────────────────────────────────
# Derived from: analysis of round 2 answers + model distinction + missing data

FABIO_ROUND3_QUESTIONS = [
    # Retry of failed question
    ("counter_trend_on_trend_day",
     "On a trend_up day, when do you take a counter-trend (short) trade? "
     "What wall size, delta signature, and structural pattern overrides the trend? "
     "Give specific conditions with numbers."),

    # Two-model switching logic
    ("trend_vs_mean_reversion_model",
     "You have two models: Trend Following (second drive after IVB breakout) "
     "and Mean Reversion (failed auction at range edge, squeeze back to POC). "
     "What are the EXACT conditions to switch from one model to the other? "
     "Is the switch based on day type alone (balance=MR, trend=TF) or can "
     "you use MR on a trend day and TF on a balance day?"),

    # TP1 / Protection Level formula
    ("ivb_protection_level",
     "After a valid IVB breakout, you mention a Protection Level (TP1) "
     "as an algorithmic target. How is this level calculated? "
     "Is it based on the IVB range projected from the breakout point? "
     "What multiple of the IVB range do you use? Give the exact formula."),

    # Participation baseline measurement
    ("participation_baseline",
     "You mention a participation baseline of 4000-5000 contracts per 1-minute candle "
     "on NQ. Below this, the setup lacks steroids. "
     "Is this the volume of the CANDIDATE bar specifically, or the average session volume? "
     "How do you measure it in practice on M5 bars?"),
]

# ── ANDREA GAP QUESTIONS ─────────────────────────────────────────────────────

ANDREA_GAP_QUESTIONS = [
    # ── IBOB Alternatives ──
    ("confirmation_without_ibob",
     "In backtesting, you confirmed a trade as 'failed_auction' even though "
     "it was NOT a clean IBOB (close was inside IB range). "
     "What other confirmation patterns do you use besides the classic IBOB? "
     "When is a failed auction sufficient confirmation WITHOUT an outside-bar close? "
     "List every alternative confirmation pattern."),

    ("ibob_relaxed_conditions",
     "When Fabio's signal is a high-confidence squeeze (conf >= 65) with a massive wall "
     "(e.g., 382 sell contracts), do you relax the IBOB close-outside-IB requirement? "
     "In other words: does the strength of Fabio's signal affect "
     "how strict your IBOB criteria need to be?"),

    # ── VP Definition ──
    ("andrea_vp_session_scope",
     "When you check if price is at Value Area High or Value Area Low, "
     "which Value Area are you using: "
     "(a) yesterday's NY cash session VA, "
     "(b) the current developing session VA, "
     "(c) a multi-day composite? "
     "Specify for each use case: "
     "1) opening gap analysis, "
     "2) identifying rotation inside VA (D-shape), "
     "3) confirming a breakout/failed auction."),

    ("andrea_overnight_gap_va",
     "For the overnight gap strategy (70% fill probability), "
     "the 'previous day VA' — is this computed from: "
     "(a) only the NY cash session 09:30-16:00, "
     "(b) the full Globex session including overnight, or "
     "(c) the RTH (Regular Trading Hours) only? "
     "What about the close price for the gap calculation — "
     "is it the 16:00 cash close or the last Globex trade?"),

    # ── Balance Day + Failed Auction ──
    ("andrea_balance_day_confirmation",
     "When the day is classified as 'balance' and Fabio identifies a failed auction "
     "squeeze at the IVB edge, what does Andrea look for to confirm? "
     "The standard IBOB requires an outside close, but on a balance day "
     "the price may not close outside. "
     "What is the confirmation rule for failed auctions on balance days?"),

    # ── 5-min vs 1-min Confirmation ──
    ("confirmation_timeframe",
     "For IBOB confirmation, do you look at the 5-minute breakout candle "
     "or do you drop to 1-minute for confirmation? "
     "In the video you say: 'For a 5-minute range, requires a 1-minute candle close.' "
     "Does this mean the IBOB trigger is actually on the 1-minute chart, not the 5-minute?"),
]

# ── ANDREA ROUND 3 QUESTIONS ────────────────────────────────────────────────

ANDREA_ROUND3_QUESTIONS = [
    # Which confirmation model to apply
    ("ibob_vs_failed_auction_selection",
     "When Fabio gives a signal, how do you decide whether to apply "
     "the IBOB breakout confirmation or the Failed Auction/Break-In confirmation? "
     "Is it purely based on day type (trend=IBOB, balance=failed auction)? "
     "Or does it depend on the setup type (squeeze vs ivb_breakout)?"),

    # Imbalance cluster definition
    ("imbalance_cluster_definition",
     "You require 2-3 diagonal imbalances for confirmation. "
     "What ratio defines an imbalance cell in the footprint? "
     "Is it 300% (3:1) or some other threshold? "
     "And diagonal means consecutive price levels, each showing imbalance?"),

    # Andrea stop placement per setup type
    ("andrea_stop_per_setup",
     "For each confirmation pattern, where exactly do you place the stop? "
     "Specifically: (a) on IBOB breakout, (b) on failed auction/squeeze, "
     "(c) on gap fill. Is it always behind the big trade cluster? "
     "How many ticks of buffer? Give exact numbers for NQ."),

    # R:R minimum
    ("andrea_minimum_rr",
     "What is the minimum risk-to-reward ratio you require to take a trade? "
     "Is it 1:1, 1:1.5, 1:2, or does it depend on the setup type? "
     "If the entry/stop/target math gives R:R of 0.8, do you skip the trade?"),
]

# ── FABIO/ANDREA ROUND 4 — OPERATIONAL DETAILS ─────────────────────────────
# These fill gaps that directly impact trade simulation and scoring

FABIO_ROUND4_QUESTIONS = [
    # CVD contradiction — system prompt says NO CVD but knowledge uses it
    ("cvd_in_simplified_model",
     "In your SIMPLIFIED model you say to ignore CVD. "
     "But in your mean reversion model you mention CVD divergence as confirmation. "
     "Clarify: does the simplified model EVER use CVD? "
     "Or is CVD only for the advanced version? "
     "If we are building a mechanical backtest with NO CVD, "
     "what replaces CVD divergence as absorption confirmation?"),

    # Acceptance definition — how many ticks/bars
    ("acceptance_definition_exact",
     "You say a valid breakout requires 'acceptance' — a full-body candle close outside the range. "
     "Exactly how do you define this? "
     "(a) Must the ENTIRE body be outside, or just the close price? "
     "(b) On which timeframe — the 5-minute candle? "
     "(c) How many ticks outside the IVB high/low counts as 'acceptance'? "
     "(d) Does a single candle suffice or do you need 2+ consecutive closes outside?"),

    # Pre-market levels
    ("pre_market_levels_usage",
     "You mention pre-market high and pre-market low as important for failed auction triggers. "
     "How do you define the pre-market range? "
     "Is it the Globex high/low from midnight to 09:30, or a shorter window? "
     "Do you use these as standalone entry levels or only as context for IVB setups?"),

    # Target selection hierarchy
    ("target_selection_hierarchy",
     "When you have a valid setup, how do you choose the target? "
     "You mention: POC, opposite VA edge, IVB protection level, previous day POC. "
     "What is the priority order? Which target do you use for: "
     "(a) a mean reversion squeeze on balance day, "
     "(b) an IVB breakout on trend day, "
     "(c) a failed auction at IVB edge? "
     "Do you always use the nearest target or the most probable?"),

    # Time cutoff for setups
    ("setup_time_cutoff",
     "After what time ET do setups become invalid or significantly less reliable? "
     "You mention avoiding lunch time. "
     "Is 11:00 ET a hard cutoff? 11:30? "
     "Or do you keep looking for setups into the afternoon? "
     "In your simplified model, what is the last valid entry time?"),
]

ANDREA_ROUND4_QUESTIONS = [
    # Gap open rules
    ("gap_open_ivb_interaction",
     "When the market opens with a gap (outside yesterday's VA), "
     "how does this affect the IB/IVB formation? "
     "Does a gap up mean the IVB high is more likely to hold, "
     "or does the gap fill probability override the IVB breakout signal? "
     "How do you reconcile a gap fill setup with an IVB breakout in the opposite direction?"),

    # Confirmation when both buy and sell walls exist
    ("conflicting_walls_resolution",
     "When you see both buy-side AND sell-side big trade clusters near the same level "
     "(within 2-3 ticks), what does this mean? "
     "Is it a no-trade, or does the LARGER side win? "
     "How do you resolve conflicting institutional signals?"),
]


# ── Core Functions ───────────────────────────────────────────────────────────

def nlm_ask(question: str) -> str:
    """Call notebooklm ask via CLI."""
    result = subprocess.run(
        [sys.executable, "-m", "notebooklm", "ask", question],
        capture_output=True, text=True, timeout=180
    )
    output = result.stdout.strip()
    combined = output + result.stderr.strip()

    if any(err in combined for err in
           ("Authentication expired", "notebooklm login", "accounts.google.com")):
        raise RuntimeError("[AUTH EXPIRED] Run 'python -m notebooklm login' then re-run.")

    if output.startswith("Answer:"):
        output = output[7:].strip()
    for marker in ["\nConversation:", "\nResumed conversation:", "\nContinuing conversation"]:
        if marker in output:
            output = output[:output.rfind(marker)].strip()
    return output


def nlm_use(notebook_id: str) -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "notebooklm", "use", notebook_id],
        capture_output=True, text=True, timeout=30
    )
    return result.returncode == 0


def load_knowledge(agent: str) -> dict:
    path = OUTPUT_DIR / f"{agent}_knowledge.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_knowledge(knowledge: dict, agent: str):
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / f"{agent}_knowledge.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(knowledge, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {path}")


def run_gap_questions(agent: str, questions: list, dry_run: bool = False):
    """Ask gap questions and merge into existing knowledge."""
    notebook_id = NOTEBOOKS[agent]
    knowledge = load_knowledge(agent)

    # Merge target: knowledge_by_topic (dict section)
    kbt = knowledge.get("knowledge_by_topic", {})
    if isinstance(kbt, list):
        # Convert list format to dict if needed
        kbt_dict = {}
        for item in kbt:
            if isinstance(item, dict) and "topic" in item and "answer" in item:
                kbt_dict[item["topic"]] = item["answer"]
        kbt = kbt_dict

    qa_log = knowledge.get("qa_log", [])

    print(f"\n{'='*60}")
    print(f"  {agent.upper()} — {len(questions)} gap questions")
    print(f"{'='*60}")

    if dry_run:
        for topic, question in questions:
            existing = kbt.get(topic, "")
            status = f"EXISTS ({len(existing)} chars)" if existing and len(existing) > 100 else "NEW"
            print(f"\n  [{topic}] {status}")
            print(f"    Q: {question[:120]}...")
        return

    if not nlm_use(notebook_id):
        print(f"  ERROR: could not select notebook {notebook_id}")
        return

    asked = 0
    skipped = 0
    for topic, question in questions:
        existing = kbt.get(topic, "")
        if existing and len(existing) > 200 and "Error:" not in existing[:80]:
            print(f"  [{topic}] SKIP (already good, {len(existing)} chars)")
            skipped += 1
            continue

        print(f"  [{topic}] Asking...", end=" ", flush=True)
        try:
            answer = nlm_ask(question)
            print(f"OK ({len(answer)} chars)")
            kbt[topic] = answer
            qa_log.append({
                "section": "gap_fill_v2",
                "topic": topic,
                "question": question,
                "answer": answer,
            })
            asked += 1
        except RuntimeError as e:
            print(f"\n  {e}")
            break
        except Exception as e:
            print(f"ERROR: {e}")
            kbt[topic] = f"Error: {e}"

    # Save after each agent (in case of interruption)
    knowledge["knowledge_by_topic"] = kbt
    knowledge["qa_log"] = qa_log
    knowledge["gap_fill_at"] = datetime.now().isoformat()
    save_knowledge(knowledge, agent)

    print(f"\n  Done: {asked} asked, {skipped} skipped")


QUESTION_SETS = {
    "fabio": {
        "round2": FABIO_GAP_QUESTIONS,
        "round3": FABIO_ROUND3_QUESTIONS,
        "round4": FABIO_ROUND4_QUESTIONS,
    },
    "andrea": {
        "round2": ANDREA_GAP_QUESTIONS,
        "round3": ANDREA_ROUND3_QUESTIONS,
        "round4": ANDREA_ROUND4_QUESTIONS,
    },
}

ALL_ROUNDS = ["round2", "round3", "round4"]


def main():
    parser = argparse.ArgumentParser(description="Fill knowledge gaps from backtest analysis")
    parser.add_argument("--agent", choices=["fabio", "andrea", "all"], default="all")
    parser.add_argument("--round", choices=ALL_ROUNDS + ["all"], default="all",
                        help="Which question set to run")
    parser.add_argument("--dry-run", action="store_true", help="Show questions without asking NLM")
    args = parser.parse_args()

    agents = ["fabio", "andrea"] if args.agent == "all" else [args.agent]
    rounds = ALL_ROUNDS if args.round == "all" else [args.round]

    for agent in agents:
        for rnd in rounds:
            questions = QUESTION_SETS[agent][rnd]
            if questions:
                run_gap_questions(agent, questions, dry_run=args.dry_run)

    if not args.dry_run:
        print("\n" + "="*60)
        print("  All gap questions complete!")
        print("  Re-run backtest to see impact: python run_backtest.py --days 5 -q")
        print("="*60)


if __name__ == "__main__":
    main()
