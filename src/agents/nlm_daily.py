"""
NLM daily research module.

The backtest Python process does NOT call NotebookLM directly —
NLM is only accessible via Claude Code MCP.

This module generates contextual questions from each day's candidates
and saves them to agent_memory/nlm_pending.jsonl.

After the backtest, Claude reads nlm_pending.jsonl and answers each question
via the mcp__notebooklm__ask_question MCP tool, writing results to
agent_memory/nlm_daily_log.jsonl.

Notebooks:
  fabio-valentini-order-flow-squ  -- squeeze / IVB setup logic
  andrea-cimi-amt-order-flow      -- footprint / IBOB confirmation
  the-liquidity-auction-amt-orde  -- AMT auction theory
"""
import json
from datetime import datetime, timezone
from pathlib import Path

PENDING_FILE = Path(__file__).parent.parent.parent / "agent_memory" / "nlm_pending.jsonl"
NLM_LOG      = Path(__file__).parent.parent.parent / "agent_memory" / "nlm_daily_log.jsonl"

NB_FABIO  = "fabio-valentini-order-flow-squ"
NB_ANDREA = "andrea-cimi-amt-order-flow"
NB_AMT    = "the-liquidity-auction-amt-orde"


def build_daily_question(date_str: str, candidates: list, day_type: str,
                         ib_range: float, poc: float,
                         va_high: float, va_low: float) -> tuple:
    """Build a focused NLM question from the day's data. Returns (question, notebook_id).

    The question is dynamically generated based on the actual setups,
    proximity levels, and confidence patterns seen during the day.
    """
    n      = len(candidates)
    lvls   = list(dict.fromkeys(c.get("proximity_to", "") for c in candidates if c.get("proximity_to")))
    setups = list(dict.fromkeys(c.get("fabio_setup", "none") for c in candidates))
    confs  = [c["fabio_confidence"] for c in candidates if c.get("fabio_confidence")]
    max_c  = max(confs) if confs else 0
    avg_c  = round(sum(confs) / len(confs), 1) if confs else 0
    traded = any(c.get("decision") == "trade" for c in candidates)

    # Build context header
    day_label = day_type.upper().replace('_', ' ')
    header = (
        f"[{date_str}] {day_label} DAY — "
        f"IB={ib_range:.0f}pts, POC={poc:.2f}, VA={va_low:.2f}-{va_high:.2f}. "
        f"{n} candidates near: {', '.join(lvls)}. "
        f"Max conf={max_c}, avg={avg_c}. Setups: {', '.join(setups)}. "
        f"{'Trade taken.' if traded else 'No trade taken.'}"
    )

    # Build dynamic question based on what actually happened
    questions = []

    # Q1: Setup-specific question
    real_setups = [s for s in setups if s != 'none']
    if 'squeeze' in real_setups and 'ivb_breakout' in real_setups:
        questions.append(
            "When both squeeze and IVB breakout setups appear on the same day, "
            "how does Valentini prioritize between them? What makes one higher conviction?"
        )
    elif 'squeeze' in real_setups:
        questions.append(
            "What are the exact differences between a valid squeeze and a false squeeze trap? "
            "What must the big trades show at the wall to confirm it's real absorption, not just passive orders?"
        )
    elif 'ivb_breakout' in real_setups:
        questions.append(
            "After an IVB breakout, what distinguishes a clean second drive from a failed extension? "
            "What order flow sequence must appear before entry?"
        )
    elif all(s == 'none' for s in setups):
        questions.append(
            "When candidates appear but no valid setup forms all day, what is Valentini's "
            "checklist to distinguish 'correctly avoided' from 'missed opportunity'?"
        )

    # Q2: Confidence gap question (if close to threshold but didn't trigger)
    near_misses = [c for c in confs if 50 <= c < 65]
    if near_misses:
        questions.append(
            f"Confidence reached {max(near_misses)} but stayed below 65. "
            f"What specific order flow confirmations would have pushed it over the threshold?"
        )

    # Q3: Day-type specific question
    if day_type == 'balance':
        if any(p in lvls for p in ('va_high', 'va_low')):
            questions.append(
                "On a balance day with candidates near VA boundaries, "
                "how does Valentini handle the rotation vs breakout dilemma?"
            )
        else:
            questions.append(
                "On this balance day, what would a valid setup have looked like? "
                "What IB range or structure would have changed the day type classification?"
            )
    elif day_type in ('trend_up', 'trend_down'):
        direction = 'bullish' if day_type == 'trend_up' else 'bearish'
        if not traded:
            questions.append(
                f"On a {direction} trend day with no trade taken, was there a pullback "
                f"to IVB/POC that could have been a second drive entry? What was missing?"
            )

    # Q4: Proximity-specific question
    if 'lvn' in lvls:
        questions.append(
            "How does Valentini read big trades clustering at an LVN vs at POC? "
            "Does the LVN act as a magnet or a barrier in this context?"
        )

    # Combine: header + top 2 most relevant questions
    selected = questions[:2]
    q = f"{header} {' '.join(selected)}"

    # Route to appropriate notebook
    if any(s in ('squeeze', 'ivb_breakout') for s in setups):
        return q, NB_FABIO
    elif any(p in lvls for p in ('poc', 'va_high', 'va_low')):
        return q, NB_AMT  # AMT auction theory for VA/POC questions
    else:
        return q, NB_FABIO


def queue_daily_question(date_str: str, candidate_log: list, session_ctx) -> dict:
    """
    Build the day's NLM question and save it to nlm_pending.jsonl.
    Claude will answer it after the backtest via MCP.
    Returns the pending entry dict.
    """
    if not candidate_log:
        return {}

    vp    = session_ctx.vp
    poc   = vp.poc     if vp else 0.0
    va_h  = vp.va_high if vp else 0.0
    va_l  = vp.va_low  if vp else 0.0
    ib_r  = session_ctx.ib_range or 0.0

    question, nb_id = build_daily_question(
        date_str, candidate_log, session_ctx.day_type,
        ib_r, poc, va_h, va_l
    )

    entry = {
        "date":         date_str,
        "notebook_id":  nb_id,
        "day_type":     session_ctx.day_type,
        "n_candidates": len(candidate_log),
        "question":     question,
        "answered":     False,
        "queued_at":    datetime.now(timezone.utc).isoformat(),
    }

    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PENDING_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"  [NLM] question queued for {date_str} -> nlm_pending.jsonl")
    return entry


def load_pending() -> list:
    """Load all unanswered questions from nlm_pending.jsonl."""
    if not PENDING_FILE.exists():
        return []
    entries = []
    with open(PENDING_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                e = json.loads(line)
                if not e.get("answered"):
                    entries.append(e)
    return entries


def save_answer(date_str: str, answer: str, notebook_id: str, question: str) -> None:
    """Save a NLM answer to nlm_daily_log.jsonl and mark pending as answered."""
    entry = {
        "date":      date_str,
        "notebook":  notebook_id,
        "question":  question,
        "answer":    answer,
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(NLM_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Mark as answered in pending file (rewrite)
    if PENDING_FILE.exists():
        lines = PENDING_FILE.read_text(encoding="utf-8").splitlines()
        updated = []
        for line in lines:
            if not line.strip():
                continue
            e = json.loads(line)
            if e.get("date") == date_str and not e.get("answered"):
                e["answered"] = True
            updated.append(json.dumps(e, ensure_ascii=False))
        PENDING_FILE.write_text("\n".join(updated) + "\n", encoding="utf-8")
