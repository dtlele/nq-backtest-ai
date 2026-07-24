# OOS 3-Week Validation Report
**Date:** 2026-07-24
**Branch:** feature/mechanical-trigger-m5
**Period tested:** 2025-03-10 → 2025-03-28 (8 trading days, 11 trades total)
**System:** V1 default (M2.5 reflex, GLM-5.2 audit, ML pre-filter ON @ 0.6, mechanical pre-filter ON)

## Executive Summary

**The V1 system has NO real out-of-sample edge.**

| Metric | Value | Verdict |
|---|---|---|
| Total trades | 11 | small sample |
| Win rate | 27.3% | **BELOW 40% breakeven** |
| Total P&L | -$116.95 | **NEGATIVE** |
| Avg P&L/trade | -$10.63 | **NEGATIVE** |
| Trading days active | 8/15 (53%) | sparse signals |

## Per-week results

| Week | Trades | W/L | WR | P&L | P&L/trade |
|---|---|---|---|---|---|
| OOS W1 (10-14 Mar) | 6 | 2/4 | 33.3% | +$31.23 | +$5.20 |
| OOS W2 (17-21 Mar) | 2 | 0/2 | 0.0% | -$101.51 | -$50.75 |
| OOS W3 (24-28 Mar) | 3 | 1/2 | 33.3% | -$46.66 | -$15.55 |
| **TOTAL** | **11** | **3/8** | **27.3%** | **-$116.95** | **-$10.63** |

## Comparison with in-sample (V1 Feb-Mar 2025)

| Period | Type | Trades | WR | P&L | P&L/trade |
|---|---|---|---|---|---|
| V8b (4-11 Feb) | in-sample | 1 | 0% | -$51 | -$51 |
| V19 (18-22 Feb) | in-sample | 4 | 75% | +$474 | +$118 |
| V21 (24-28 Feb) | in-sample | 17 | 35% | +$80 | +$5 |
| V22 (3-7 Mar) | in-sample | 13 | 38% | +$197 | +$15 |
| **OOS W1-W3 (10-28 Mar)** | **out-of-sample** | **11** | **27%** | **-$117** | **-$11** |

The in-sample V19 +$474 result was lucky (small sample, 4 trades). The OOS results show the system has no statistically significant edge.

## Why V8b +$666 is unattainable

V8b (4-11 Feb 2025) was a 3-trade run producing +$666 cited in earlier project memory. **It cannot be reproduced with the current V1 system.** Root cause:

- The ML model `rf_v1.pkl` (trained on 230 days, AUC 0.73) assigns scores < 0.5 to **100% of V8b candidates**.
- Without ML pre-filter (threshold 0), the LLM Fabio itself rejects 99% of candidates as "none(0)".
- Lowering threshold to 0.5 yields 2 V8b trades, both losses.
- Conclusion: the V8b +$666 came from a previous system state (pre-ML-pre-filter, commit 3340e62).

## Diagnosis

The V1 system is **rejection-overshoot**:
1. Mechanical pre-filter is too aggressive (skips complex V8b-style patterns)
2. ML pre-filter is too aggressive on early-Feb data (rf_v1.pkl distribution mismatch)
3. Audit 100% confirm — every signal that survives passes audit, no safety net
4. LLM Fabio itself rejects most patterns that the pre-filters miss

## Verdict

**The V1 system is not profitable in OOS.** Total +$629 across 6 in-sample weeks dissolves to -$117 across 3 OOS weeks. The system has negative expectancy of approximately -$10/trade after costs.

## Recommendations

1. **DO NOT trade this system live.** The OOS data is conclusive: WR 27% < 40% breakeven.
2. **Pivot to backtester/dashboard** as suggested in CONTINUE_PROMPT.md option D. The infrastructure (bias engine, mechanical trigger, ML pre-filter) has research value but not alpha.
3. **If continuing research**, the next focus should be: either (a) retrain ML on more recent data, (b) reduce the LLM rejection rate, or (c) find a different signal source entirely.
4. **Save the $11.34 remaining OpenRouter credits** for a future pivot rather than burning them on more OOS weeks that will likely show the same pattern.

## Cost tracking

- OpenRouter credits spent today: $0.71 (3 OOS weeks + V8b diagnosis tests)
- Remaining balance: $11.34
- Total project spend: $27.26 / $15 budget (over budget, paid out of pocket — see CONSTRAINTS #13 for context)
