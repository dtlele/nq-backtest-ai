# LLM Direction Quality Analysis

**Data:** 24 luglio 2026
**Method:** Analyzed 816 Fabio direction calls (conf >= 55) across all reasoning logs vs next-bar direction in features_230d dataset.

## 🎯 The Smoking Gun

**LLM (Fabio) directional accuracy: 50.6%** — essentially random.

| Setup × ML score | n | Accuracy | Edge |
|---|---|---|---|
| ALL Fabio calls | 699 | 50.6% | +0.6% |
| Reversal | 414 | 47.3% | -2.7% (worse than random!) |
| Imbalance_hunting | 93 | 57.0% | +7.0% |
| Pullback | 92 | 53.3% | +3.3% |
| Squeeze | 73 | 52.1% | +2.1% |
| IVB_breakout | 22 | **68.2%** | +18.2% |

**By ML score bin:**
| ML bin | n | Accuracy |
|---|---|---|
| 0.00-0.50 | 79 | 30.4% (anti-pattern!) |
| 0.50-0.60 | 91 | 71.4% (highest!) |
| 0.60-0.70 | 85 | 49.4% |
| 0.70-0.80 | 179 | 47.5% |
| 0.80-1.01 | 265 | 51.3% |

## 🔬 Setup × ML Combined Filter

The most actionable finding — specific combinations have REAL edge:

| Filter | n | Accuracy | Edge |
|---|---|---|---|
| pullback × ml>=0.7 | 82 | **64.6%** | +14.6% |
| pullback × ml[0.7-0.8) | 24 | 62.5% | +12.5% |
| pullback × ml[0.8-1.0) | 58 | **65.5%** | +15.5% |
| ivb_breakout × ml>=0.7 | 16 | 62.5% | +12.5% |
| reversal × ml[0.5-0.6) | 88 | 72.7% | +22.7% (small sample) |
| **reversal × ml>=0.7** | 210 | **41.9%** | **-8.1% (WORSE than random)** |
| imbalance_hunting × ml>=0.7 | 71 | 47.9% | -2.1% |

## ⚠️ Critical: PnL is not accuracy

The 64.6% accuracy on pullback+ml>=0.7 sounds great, but the actual simulated PnL is:

| Filter | n | WR (8pt/16pt sim) | Total PnL |
|---|---|---|---|
| All (no filter) | 793 | 9.0% | -5036pt |
| pullback + ml>=0.7 | 82 | 13.4% | -433pt |
| pullback + ml>=0.8 | 58 | 6.9% | -397pt |
| ivb_breakout + ml>=0.7 | 16 | 18.8% | -64pt |

**Why?** Because the accuracy metric measures "did the next bar go in LLM's direction", but the trade uses 8pt stop / 16pt target over 6 bars (30 min). The trade can be stopped even when the LLM direction is right on the next bar.

## 📉 The Real PnL Problem

Even with the "best" filter (pullback+ivb_breakout+squeeze × ml>=0.7, cap 3/day):
- n = 36 trades over 14 days
- WR = 19.4% (need 33% to break even with R:R=2)
- Total PnL = -138pt
- Days > 0: 21.4%

**The system is unprofitable because:**
1. **LLM direction accuracy is 50%** — barely above random
2. **8pt stop / 16pt target R:R=2 requires 33% WR to break even** (with cost)
3. **Most setups achieve 7-15% WR** because the stop is too tight vs target

## 🎯 Recommendations

### A. Improve LLM direction quality (the real bottleneck)
- Add more context to the LLM prompt (M1 footprint, M1 delta sequence)
- Use the M2.5 model (currently GLM-5.2) for direction
- Consider fine-tuning on historical NQ data
- Add multi-expert consensus (but user excluded Andrea)

### B. Change R:R ratio
- Smaller target (e.g., 8pt target with 4pt stop = R:R=2) — too tight
- OR larger target with same stop (e.g., 24pt target with 8pt stop = R:R=3) — needs 25% WR to break even
- OR trailing stop with no target (capture bigger moves)

### C. Filter aggressively for high-edge setups
- ONLY take pullback + ivb_breakout + squeeze with ml>=0.7
- REJECT all reversal setups (47.3% accuracy is worse than random)
- REJECT imbalance_hunting with ml>=0.7 (47.9% accuracy)

### D. V2 audit is still useful
- Catches the OBVIOUS disasters (R1 delta > 500 opposing, R3 big trades)
- Net effect on V8b: +$100 (small but positive)
- Should be used as a safety net, not a primary edge source

## 📁 Artifacts

| File | Purpose |
|---|---|
| Analysis (this doc) | LLM direction quality breakdown |
| `scripts/ml/audit_v2_pnl_sim.py` | PnL simulation by filter |
| `docs/V2_AUDIT_SIM.md` | V2 audit design + V8b validation |
| `docs/V2_VALIDATION.md` | V2 extended testing on V8b/V14/V15 |

## 🔑 Bottom Line

**The V2 audit is helpful but small (+$100 on V8b). The real system improvement needs:**
1. **Better LLM direction** — current 50% accuracy is the bottleneck
2. **Aggressive setup filtering** — pullback/ivb_breakout only, with high ML score
3. **R:R adjustment** — current 8pt/16pt is too tight vs LLM's actual hit rate

The +$766 V8b winner was partly luck (caught a pullback absorption setup) and partly system (proper bias engine + ML filter + V2 would have caught the other 2 disasters).
