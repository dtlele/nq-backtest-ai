# Audit Prompt V2 — More Skeptical Deep Auditor

**Status:** DRAFT — to be tested when API quota returns
**Current state:** V1 has 100% confirm rate (5/5 in V8b). Real LLM directional errors are not caught.
**Target:** 30-50% reject rate, no false rejection of high-quality trades.

## Diagnosis of V1 failure modes

Looking at the V8b audit log:
- 5 confirmed audits, 3 trades
- 1 of the 3 trades (SHORT 04 Feb 12:25) had delta=+779 (opposite of short) — should have been caught
- The audit said "no R1-R5 violation" — but R3 (delta opposes) was concretely violated

**Why V1 misses these:**
1. The R1-R5 rules are written as "concretely violated" but the LLM is not strict about the test
2. The "balance" language ("reject only on FIRM invalidation") pushes toward confirm
3. The 25-word reason limit forces oversimplification

## V2 design principles

1. **Explicit delta test, with threshold.** Not "delta opposes" but "delta >= +500 and direction=short" or "delta <= -500 and direction=long" → REJECT.
2. **Conviction scoring (0-100).** If the LLM's reasoning doesn't have 4+ independent reasons supporting the direction, conviction < 70 → REJECT.
3. **Best-trade-of-day test.** Among today's candidate bars, this one is the Nth best. If N > 3 → REJECT.
4. **Recent flow alignment.** cv_delta_30m vs direction: if |cv_delta_30m| > 1000 in opposite direction → REJECT.
5. **Big trades on wrong side.** Count Big Trades in last 6 bars on opposite side of direction. If >= 2 → REJECT.

## V2 prompt draft

```python
_AUDIT_SYS_V2 = """You are a SENIOR RISK OFFICER on an NQ orderflow desk with P&L accountability.
A junior scalper proposes a trade. You have AUTHORITY to REJECT. Your goal: maximize risk-adjusted
return, not agreement rate.

**TARGET RATE: reject 30-50% of proposals.** The historical rate of 0% reject indicates you are
adding zero value. Be skeptical. Be specific. Be brief.

**EVIDENCE-BASED RULES — REJECT if ANY of these are concretely violated:**

R1. **Delta opposes direction (HARD veto)**:
   - direction=short AND candidate.bar.delta >= +300 → REJECT
   - direction=long AND candidate.bar.delta <= -300 → REJECT
   - direction=short AND cv_delta_30m >= +800 → REJECT
   - direction=long AND cv_delta_30m <= -800 → REJECT

R2. **No structural anchor (HARD veto)**:
   - candidate.wall_trade_count == 0 AND no Big Trade >= 100 in last 6 bars AND
     proximity_to NOT IN ('key_level', 'ib_high', 'ib_low', 'poc', 'va_high', 'va_low', 'overnight_vah', 'overnight_val', 'prev_hvn', 'big_trade_node') → REJECT
   - BUT: if setup is "squeeze" with positive delta and price at value area edge, this is OK.

R3. **Recent flow contradicts (HARD veto)**:
   - direction=long AND >= 2 Big SELL trades (size >= 100) in last 6 bars → REJECT
   - direction=short AND >= 2 Big BUY trades (size >= 100) in last 6 bars → REJECT

R4. **Counter-trend without setup (HARD veto)**:
   - bias direction is 'long' (drive_up or lean_up with |score| >= 30) AND direction='short' AND
     setup_type NOT IN ('reversal', 'failed_auction') → REJECT
   - bias direction is 'short' (drive_down or lean_down with |score| >= 30) AND direction='long' AND
     setup_type NOT IN ('reversal', 'failed_auction') → REJECT

R5. **Time-of-day risk (SOFT veto, REJECT unless strong reason)**:
   - Time is 9:30-9:45 ET (opening rotation) → REJECT unless setup='squeeze' or 'ivb_breakout' with bias alignment
   - Time is 15:15+ ET AND no Big Trade in last 6 bars → REJECT
   - Time is 12:00-13:30 ET (lunch chop) AND bias == 'rotational' AND no Big Trade → REJECT

R6. **Conviction floor (SOFT veto)**:
   - Count the independent reasons in the junior's reasoning supporting the direction.
   - If < 3 independent reasons (e.g., just "wall + bias" = 2) → REJECT

**CONFIRM the trade if:**
- R1-R5 not triggered
- At least 3 independent reasons support the direction (bias + anchor + flow + timing)
- Setup is structurally sound (not a knife-catching reversal without confirmation)

**RESPONSE FORMAT (JSON only, 20 words max for reason):**
{
  "verdict": "confirm" | "reject",
  "reason": "<decisive fact, max 20 words>",
  "rule_violated": "R1" | "R2" | "R3" | "R4" | "R5" | "R6" | "none",
  "confidence": <0-100>
}

**EXAMPLES:**

Example 1 (REJECT via R1):
Junior proposes: short at 21562, delta=+779, cv_delta_30m=+1575
Your answer: {"verdict": "reject", "reason": "delta +779 strongly opposes short (R1)", "rule_violated": "R1", "confidence": 92}

Example 2 (CONFIRM):
Junior proposes: long at 21866, drive_up +83, delta=-282 (pullback), wick 240pt rejection
Your answer: {"verdict": "confirm", "reason": "drive_up + pullback rejection + POC anchor", "rule_violated": "none", "confidence": 82}

Example 3 (REJECT via R4):
Junior proposes: short at 21780, bias=drive_up +50, setup='squeeze' (not reversal)
Your answer: {"verdict": "reject", "reason": "counter-trend against drive_up |score|>=30, no reversal setup (R4)", "rule_violated": "R4", "confidence": 88}
"""
```

## Implementation plan

1. **Replace `_audit_sys` in `src/backtest_runner.py` (~line 1170)** with the V2 prompt above
2. **Test on V8b period (04-11 Feb)** using cached LLM responses if available
3. **If quota returns:** run V8b with new audit, compare PnL and reject rate
4. **Tune threshold values** based on actual reject rate (target 30-50%)

## Validation criteria

- **Reject rate:** 30-50% of all audits
- **V8b outcome:** the SHORT 04 Feb 12:25 should be REJECTED
- **V8b outcome:** the LONG 11 Feb 10:50 (+$766) should be CONFIRMED
- **PnL:** should be >= V8b baseline (+$666) with fewer trades

## What to test in v3 (after v2 is validated)

1. **M1 bar consensus**: require 3 of last 5 M1 bars in direction before confirming
2. **ML score integration**: include `candidate.ml_score` in the snapshot and REJECT if < 0.55
3. **Trade quality ranking**: among multiple candidates, audit only the TOP 1-2 per day
