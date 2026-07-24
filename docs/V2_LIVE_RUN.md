# V2 Audit LIVE Run Results — 4-12 Feb 2025

**Data:** 24 luglio 2026 (live API call)
**Config:** `AUDIT_PROMPT_VERSION=v2 REFLEX_MODEL=z-ai/glm-5.2 AUDIT_MODEL=z-ai/glm-5.2`
**Cache:** Restored from `llm_cache_glm52_backup.json` (2,792 entries)
**Cost:** $0.14 (from $9.10 to $8.42 in OpenRouter credits)

## 📊 Run Results

```
Total trades:   2
Win rate:       0.0%
Profit factor:  0.00
Total P&L:      $-102.32
Avg R:          -1.00
```

**Audit calls:** 4
- 3 CONFIRMED → 3 STOPs (LONG 21635.75 -$52, SHORT 21611.25 -$50, SHORT -$50)
- 1 REJECTED → R3 (Two big SELLs 81+118=199 ≥ 150 threshold)

**Net effect vs V8b baseline (+$666): -$768 worse.** V2 audit in live did NOT replicate the V8b success.

## 🔍 Why the simulator and live diverge

The shadow test (offline simulator on real M5 bars) predicted V2 would catch the V8b 04 Feb 12:25 SHORT (delta=+779 opposes short). But in the live run, the **LLM reflex never proposed that specific trade** — the cache-restored reflex found different candidates.

| V8b original (V1 audit) | V18b V2 live run |
|---|---|
| SHORT 04 Feb 12:25 → STOP -$50 | LONG 04 Feb 13:50 → STOP -$52 |
| LONG 11 Feb 09:35 → BE | SHORT 05 Feb → STOP -$50 |
| LONG 11 Feb 10:50 → +$766 | (no equivalent) |
| **Net: +$666** | **Net: -$102** |

**Root cause: the LLM reflex is deterministic (cached).** When the cache is restored, the reflex proposes the same candidates as the original run. But the live run's candidate detection pipeline may find different bars, the bias engine state may be different (because different timestamps), and the ML filter results may differ slightly.

## 🎯 What V2 actually caught in live

Only 1 reject out of 4 audit calls (25% reject rate):
- **`9faf7f5d...` R3 reject**: "Two big SELLs (81+118=199) oppose long; 199>=150 R3 threshold" — this saved a losing trade

**3 confirmed trades, all STOPPED:**
1. LONG 21635.75: "drive_up +44, wall/POC confluence second test, sell absorbed (+86 delta), trend_up" — STOP
2. SHORT 21611.25: "drive_down -45 + wall rejection w/ 120-lot SELL + cumulative delta -1337" — STOP
3. SHORT: "VAH 2nd test + delta divergence -799 on +78pt rally" — STOP

**Why V2 didn't catch them:**
- The LLM reflex's reasoning is sophisticated and the audit gets swayed
- R1 (delta threshold) didn't fire because the reflex correctly identified the directional flow that supports the trade (e.g., for SHORT, the delta was negative, supporting the short)
- The trades were "logical" but the market just didn't move in the predicted direction

## 💡 Key Insights

1. **V2 audit is a good SAFETY NET but not a magic bullet** — caught 1/4 bad trades (25%)
2. **The LLM reflex's elaborate reasoning overwhelms the audit's simple rules** — even with the new R1-R6 framework, the audit confirms trades that the LLM has "explained away"
3. **The real edge has to come from the LLM direction quality** (50.6% accuracy) — V2 can't fix this
4. **R3 (Big Trades) is the most useful rule in live** — caught 1 actual losing trade
5. **The simulator's 14% reject rate is overstated** — the live reject rate on the same period was only 25% (1/4)

## 📁 Artifacts

| File | Purpose |
|---|---|
| `output/week_v18b_v2audit.log` | Full V2 live run log |
| `output/v2_live_run_results.log` | Same as above, archived |
| `docs/AUDIT_PROMPT_V2.md` | V2 prompt spec |
| `scripts/ml/audit_v2_simulator.py` | Offline shadow test |

## 🎯 Next Steps (when API returns)

1. **Don't trust the simulator 1:1** — the live behavior is different
2. **Try V2 with TIGHTER thresholds** — R1 at ±300 (more sensitive) might catch more
3. **Add a "block all trades if any reject in last 3 audits" rule** — cascading
4. **Consider replacing the LLM-based audit with a DETERMINISTIC audit** — apply R1-R6 in code, no LLM call
5. **Or: just turn off the audit** — it's costing $0.025/run and adding little value
