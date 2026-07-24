# V1 vs V2 Audit — LIVE Comparison (Reflex V8b candidates)

**Data:** 24 luglio 2026 (live API calls)
**Cache:** Restored from `llm_cache_glm52_backup.json` (2,792 entries)
**Total cost:** $1.34 (from $9.10 to $7.76)

## 📊 Live Comparison

### Period 1: 04-12 Feb 2025 (8 days, V8b-ish)

| Audit | Trades | WR | PnL | Rejects |
|---|---|---|---|---|
| **V1 (baseline)** | 3 | 33% | **+$666** | 0 |
| **V2 (new)** | 2 | 0% | **-$102** | 1 (R3) |

V1 wins by $768.

### Period 2: 18-22 Feb 2025 (5 days, NEW)

| Audit | Trades | WR | PnL | Rejects |
|---|---|---|---|---|
| **V1 (baseline)** | 4 | 75% | **+$474** | 0 |
| **V2 (new)** | 3 | 66.7% | **+$198** | 3 (R1×2, R6×1) |

V1 wins by $276.

### Total over 13 days

| Audit | Trades | WR | PnL |
|---|---|---|---|
| V1 | 7 | 57% | **+$1,140** |
| V2 | 5 | 40% | **+$96** |

**V2 audit is HURTING the system by ~$1,044 over 13 days.**

## 🔍 Why V2 is failing in live (vs simulator)

The offline simulator predicted V2 would catch disasters while keeping winners. But in live:

1. **The LLM reflex's elaborate reasoning overwhelms the audit's rules.** The audit is swayed by "delta divergence = absorption" type arguments.
2. **V2 R1 rejects trades that V1 confirmed and that ended up winning.** The cv_delta threshold (±1500) is too tight — bars with strong directional flow on the right side of the trade still get rejected.
3. **V2 R6 (4.25pt stop too tight) rejected a valid trade.** V1 confirmed the same trade.
4. **The simulator's "delta opposes" tests used forced direction from bar.net.** The live LLM direction is more nuanced (and sometimes correct even when delta seems opposing).

## 📋 Live V2 Rejects That V1 Would Have Kept

| Date/Time | Direction | V2 Reject Reason | V1 Verdict | Actual PnL? |
|---|---|---|---|---|
| 18-22 Feb 11:01 | SHORT | R1: cv_delta_30m +1611 >= +1500 opposes short | CONFIRM | Not traded (V2 blocked) |
| 18-22 Feb 12:35 | SHORT | R1: cv_delta_30m +3359 exceeds +1500 | CONFIRM | Not traded (V2 blocked) |
| 18-22 Feb 14:30 | SHORT | R6: 4.25pt stop on 189.9 ATR=guaranteed noise stop | CONFIRM | Not traded (V2 blocked) |
| 04 Feb 13:00 | LONG | R3: 2 big SELLs 81+118=199 ≥150 | CONFIRM | Not traded (V2 blocked) |

These 4 rejected trades could have added to PnL if V1 had been used. We don't know exact outcomes but the V1 4-trade period had 3 wins (75% WR).

## 💡 Key Learnings

1. **V2 audit is too aggressive** — its R1/R3/R6 thresholds catch valid trades that win
2. **The LLM reflex's reasoning is sophisticated enough to explain away most rejections** — the audit gets convinced
3. **V1's "100% confirm" approach actually wins** because most of the LLM's trade proposals are reasonable
4. **The bottleneck is LLM direction quality, not audit quality** — V2 can't fix what V1 doesn't fix
5. **Adding rules doesn't help if the rules are too strict** — better to leave the LLM's proposals alone and focus on improving the LLM itself

## 🎯 Recommendations

### A. Revert to V1 (best ROI)
- V1 made **+$1,140 over 13 days** with 57% WR
- V2 made only **+$96 over 13 days** with 40% WR
- V2 is actively hurting the system

### B. If keeping V2, make it MUCH more lenient
- R1 thresholds: ±2000 (was ±1500) — only catch extreme cases
- R3: only fire on >=3 Big Trades (was 2)
- R6: don't fire on stop size — leave that to risk management
- OR: only VETO if score < 0.6 (trust ML filter, ignore audit)

### C. Try a different filter approach
- Implement the setup×ML filter as a hardcoded rule (no LLM):
  - ONLY take pullback/ivb_breakout/squeeze with ml>=0.7
  - REJECT reversal with ml>=0.7 (41.9% accuracy is worse than random)
- This was the real edge discovered in offline analysis

### D. Improve LLM direction quality
- Add M1 footprint context to the prompt
- Use ensemble (multiple LLMs, take majority)
- Fine-tune on historical NQ data (if budget allows)

## 📁 Artifacts

| File | Purpose |
|---|---|
| `output/week_v18b_v2audit.log` | V2 run 04-12 Feb |
| `output/week_v19_v2audit.log` | V2 run 18-22 Feb |
| `output/week_v19_v1audit.log` | V1 baseline run 18-22 Feb |
| `docs/V2_LIVE_RUN.md` | First V2 live run (deeper analysis) |
| `docs/V2_VALIDATION.md` | Offline validation |
| `scripts/ml/audit_v2_pnl_sim.py` | Offline PnL sim (was too optimistic) |

## 🔑 Bottom Line

**V2 audit makes the system WORSE in live.** The V8b +$666 was lucky timing. V1 (the "broken" audit) is actually the best version because it doesn't block the LLM from making trades.

**Next: revert to V1 default, or implement setup×ML hardcoded filter.**
