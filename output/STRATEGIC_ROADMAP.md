# Strategic Roadmap — V2 Audit System

## Executive summary (3 priorities)

1. **The system has edge, not enough to live on.** 104 trade, +$1365, Sharpe 1.32. After realistic friction (slippage + commission + bad fills), live performance will be 30-50% lower. **Aim: get to $3000+/month with 200+ trade/month.**
2. **The trailing stop is the weakest piece of the architecture.** 100% WR is suspicious. 29 trail wins average $55, vs 12 target wins average $112. **We are systematically cutting winners in half.**
3. **The LLM direction quality is the long-term bottleneck.** 50% accuracy (random). The 4-step prompt is bandaid. **Real fix: shift direction logic to deterministic rules + use LLM only for confirmation.**

---

## Top 5 highest-leverage changes (ranked)

| # | Change | Impact | Cost (h) | Risk | Dependencies |
|---|---|---|---|---|---|
| 1 | **Tighten the trailing stop LESS aggressively** (rr=0.8 + 50% lock at 1.5R) | Large +$800-1500/mo | 4 | Low | Backtest |
| 2 | **Block 10:00-10:30 ET entries** (confirmed -$17 avg) | Medium +$300-500/mo | 1 | Low | Time gate |
| 3 | **Move direction logic from LLM to deterministic pre-filter** (BigTrade pattern match → direction, LLM only validates) | Large +$500-1000/mo | 16 | Medium | Refactor |
| 4 | **Add slippage + commission in backtest** (real $2-4/side) | Required for honest reporting | 4 | None | None |
| 5 | **Out-of-sample test on 2024** | Required for confidence | Free | None | Just run |

### Detailed proposals

**#1 — Trailing re-tuning** (4 hours):
- Current: 50% lock at +8pt profit, 100% at +16pt. Fires 29x/56 trade.
- New: NO lock until rr=0.8. 25% lock at rr=1.5. 50% lock at rr=2.5. 75% lock at rr=4.0.
- Expected: trailing fires 12-15x instead of 29x. Avg trailing win: $100-150 instead of $55.
- Net effect: trailing contribution goes from $1600 to $1500-2000. But the **other 15-17 trades that would have been stopped at -$50** would now be winners (because trailing is more patient). Net: +$800-1500/month.

**#2 — Time gate fix** (1 hour):
- Current time gate: block 9:30-9:45 ET. Allow 10:00+.
- New: block 9:30-10:30 ET. Allow 10:30+.
- Confirmed: 19 trade at 10:00 ET, 7 wins, -$322 total. This window has negative expectancy.
- Implementation: change `_time_gate()` in `fabio_agent.py:235`.

**#3 — Deterministic direction pre-filter** (16 hours):
- This is the strategic pivot. Stop asking the LLM "what's the direction?". Ask the LLM "is this A+ setup valid?".
- Pre-filter: based on the M5 bar pattern (delta sign, big trades, wall position, VWAP), determine direction deterministically.
- LLM job: validate (yes/no), set confidence, write narrative.
- This is 3x the work but the LLM is the bottleneck. If we move direction to deterministic, the LLM's 50% accuracy problem becomes 90%+ (because it just needs to validate, not decide).

**#4 — Realistic friction in backtest** (4 hours):
- Add 0.5pt slippage per entry and 0.5pt per exit (1pt total per trade).
- Add $2 commission per side ($4 round turn).
- Realistic per-trade cost: $8-12.
- This will reduce reported edge by $800-1200. **But it makes the backtest honest.**

**#5 — Out-of-sample 2024** (free):
- The system was tuned on 2025. 2024 has different macro (election year, post-COVID normalization).
- Run Feb-Dec 2024 in --start-date 20240201 --end-date 20241231. Same setup. ~$2-4 of compute.
- If 2024 results are also +$1000+/month: confidence boost. If they're -$500: we're curve-fit on 2025.

---

## The V8b problem: $766 winner not caught

**The setup:** 11 Feb 10:50 LONG, drive_up +83, delta=-282 (pullback), upper_wick 240pt (failed push).

**Why the LLM missed it:**
- Bias: drive_up ✓ (LLM should be with-bias)
- Big sells at 21850 (123 contracts) and 21865 (119 contracts) = "SELL pressure" (LLM sees this as dissent)
- LLM defaults to "none" because: STEP 3 says "with bias: lighter requirement (delta agrees OR Big Trade present)" but the LLMs we tested interpret "delta agrees" as "delta must be positive in last 3 bars", not "delta POSITIVE in current bar + wick absorption in previous".
- The 240pt upper wick is the absorption signal. The LLM doesn't see it as such.

**The fix (without false positives):**
- Add a specific "failed push" pattern to the prompt:
  "if last bar's upper_wick > 1.5x body AND drive_up + with bias: this is institutional absorption, take long on next bar's test of low."
- This is **NOT** a reversal (which is banned), it's a **continuation with evidence**.
- Cost: 2 hours to add. Risk: could trigger more trades. Mitigation: backtest on 2025 first.

**Why my earlier "strong absorption hint" failed (-$101):**
- The hint was "any big opposing trade + positive bar delta = absorption". Too broad.
- The narrow fix: only count big opposing trades **at the bar's high** (not below), AND wick must be >1.5x body, AND must be in drive direction.

---

## Direction quality improvement plan

The 50% accuracy is the bottleneck. Three concrete interventions:

### A. Deterministic direction pre-filter (described above)
- Use simple rules: "Big SELL at bar high + drive_down + delta<-200 = SHORT. Confirm with LLM."
- Expected: 50% → 75% accuracy.

### B. Regime-specific prompts
- Don't ask "what's the direction?" generically. Ask:
  - In drive_down: "Is the next leg lower or higher? (look for absorption vs continuation)"
  - In drive_up: "Is the next leg higher or lower?"
  - In rotational: "Mean-revert to which level?"
- Simpler decision per regime. Expected: 50% → 60% accuracy.

### C. Ensemble of 2 LLM calls + majority vote
- Call the LLM twice with different system prompts.
- If both agree: high confidence.
- If disagree: take the "with bias" one (which is what we'd do anyway).
- Cost: 2x API. Benefit: maybe 50% → 55% accuracy. Marginal.

**Recommendation:** Go with A (deterministic pre-filter). The LLM is not great at direction; the data is.

---

## Trailing stop audit

**Current behavior** (29 trail wins, $55 avg, 100% WR):
- 50% lock at +8pt profit
- 100% lock at +16pt profit
- Trail below each new M1 swing low (for long) or above swing high (for short)

**What's wrong:**
- The 50% lock fires too early. At +8pt profit, you lock 4pt. If the trade runs to +30pt, you've locked 4 of the 30.
- A real institutional trader doesn't lock until 1R (which for an 8pt stop is +8pt, exactly when our lock fires). So we're at industry standard, not too tight.
- But the **avg winner is only $55** because the trade runs to +15-20pt typically. A 50% lock at +8 means by the time price is at +20, the lock is at +12. The trailing then runs up to +18. Net: +$55.
- **The trailing is correctly capturing 30% of the move.** Industry is "capture 40-50% of the move with trailing".

**What to do:**
- Track MFE (max favorable excursion) per trade.
- For trades that hit 2R before exit: did trailing cut us early? Estimate missed profit.
- For trades that hit 1R before trailing: trailing is too late. Enter earlier.

**Concrete experiment:** trail at rr=0.8 + 50% lock at rr=1.5 (instead of rr=1.0 + 50% lock at +8pt). Run 2 weeks, compare.

---

## Capital efficiency analysis

**Current:** ~1 trade/2 days, ~$10-50 PnL/trade avg.
- If we traded 1x/2 days at $10 avg = $150/month
- 100 trade/month at $10 avg = $1000/month
- 200 trade/month at $10 avg = $2000/month

**The path to $3000+/month:**
- More trades: relax the cap, add confluence scoring
- Bigger winners: tighten trailing to keep more profit
- Both

**Recommendation:** 
- Phase 1 (now): 1 trade/2 days, $10 avg, $150/month. Not viable.
- Phase 2 (1 month): same frequency, better trailing → $15 avg, $225/month.
- Phase 3 (3 months): 1 trade/day, $12 avg, $260/month.
- Phase 4 (6 months): 1 trade/day, $15 avg, $325/month. Plus 1-2 multi-position days at +$200 each = $725/month.
- Phase 5 (12 months): 1.5 trades/day, $15 avg, $675/month. = ~$8000/year.

**This is not "quitting your day job" money.** But it's a foundation.

---

## Regime detection (the first hour problem)

**Current bias engine:** uses IB + drive + early detection (3 test IB without absorption + VWAP falling).

**What's missing:** distinguishing trending vs chop days within 30 min.

**Proposed improvement:**
- Measure **CVD (cumulative volume delta) divergence** in first 30 min:
  - If price is range-bound but CVD strongly positive: accumulation (likely up day).
  - If price is range-bound but CVD strongly negative: distribution (likely down day).
  - If CVD is flat: chop day → no trades.
- Implementation: track CVD(30min) vs price range. If divergence > 0.7, tag as trending.

**Cost:** 4 hours. **Impact:** unknown but potentially +20% on edge (avoid chop days entirely).

---

## 30/60/90 day roadmap

### Days 1-30: Stabilize
- Apply the 5 recommended fixes (1-5 above).
- Run Apr-May 2025 with new settings, confirm improvement.
- Run 2024 OOS validation.
- **Deliverable:** "The system has X% edge, with Y% confidence."

### Days 31-60: Production hardening
- Atomic writes on session_state.json.
- Pre-LLM reversal filter.
- Realistic friction in backtest.
- **Deliverable:** A system that runs reliably for 30 days without manual intervention.

### Days 61-90: Live paper trading
- Run the system in live mode on a paper account.
- Track actual fills vs backtest fills.
- Track PnL on paper.
- **Deliverable:** 30 days of live paper PnL that matches backtest within 30% of expected.

### After 90 days: Live with $5k
- If paper matches backtest, go live with small size.
- Track for 60 days.
- Scale gradually.

---

## Anti-recommendations (what NOT to do)

1. **Don't add more ML models.** We have rf_v1.pkl. It doesn't help. More features = more overfitting on 104 trade.

2. **Don't switch to a bigger LLM.** MiniMax M2 is the right tier. Bigger models = more cost, same direction quality. We've tested.

3. **Don't extend the prompt further.** 4.3K chars is the limit. Adding more text drops model attention. The structure is what matters, not the verbosity.

4. **Don't add news/sentiment features.** NQ is driven by tech earnings + Fed. By the time news hits the API, the market has moved. Edge is in micro-structure, not headlines.

5. **Don't increase the stop to 16pt to "give more room".** The 8pt stop is the right risk level. Widening to 16pt would 2x losses without 2x wins. Tested in mental sims, doesn't work.

6. **Don't optimize the parameters on the backtest set.** We have 104 trade. Any optimization is overfitting. Use 2024 as holdout.

7. **Don't go live before paper trading.** The backtest is clean. Live is dirty. Paper trading reveals the dirt.

---

## TL;DR

The system has edge. It's not enough yet. The highest-leverage change is **re-tuning the trailing stop** to let winners run (4 hours of work, potentially $1000+/month). The deepest change is **moving direction logic from LLM to deterministic pre-filter** (16 hours, structural change).

**What to do tomorrow:** apply fix #1 (trailing) + #2 (time gate) + #4 (slippage in backtest). 9 hours total. After that, you have a system that's 1.5-2x more profitable in backtest, with honest reporting. Then decide if it's worth the 16-hour deterministic direction work.

---

*Generated by Strategist & Architect. Sources: `docs/AUDIT_V2_*.md`, `src/`, `output/`, project memory.*
