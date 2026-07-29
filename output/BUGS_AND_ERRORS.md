# Bugs & Errors Audit — V2 System

## Top 5 dangerous issues (production blockers)

### 1. **Parse error fallback is dangerous**
- **File:** `src/agents/fabio_agent.py:786`
- **Code:** `except Exception: return {"decision": "hold", "new_stop": None, ...}`
- **Risk:** When LLM returns malformed JSON (or 8x in run Apr-May), APM defaults to "hold" with the OLD stop. Trade keeps running with no progression. In a real crash scenario, this means the trailing logic can stall for 1-2 minutes until the next M1 bar.
- **Fix:** On parse error, call the model again OR move stop to a safe mechanical level (entry + 50% of risk).

### 2. **OPEN_TRADE visibility only via live_sync**
- **File:** `scripts/live_sync_dashboard.py:38` (now fixed), `sync_loop.py:232`
- **Status:** ✅ Fixed in commit 3169e54
- **Note:** Without the fix, the dashboard overlay only showed AFTER trade closed. Currently OK.

### 3. **Race condition on session_state.json**
- **Files:** `src/agent_memory.py` (load_session/save_session are not atomic), `scripts/live_sync_dashboard.py` (reads every 2s)
- **Risk:** backtest_runner writes mid-trade, live_sync reads mid-write → corrupted JSON. Last error in Apr-May run: `Extra data: line 93298 column 3 (char 3784205)` was the JSON parser failing on partial write.
- **Fix:** Use atomic file write (write to .tmp, rename). 1 hour.

### 4. **`reasoning_log.jsonl` not truncated on reruns**
- **File:** `src/backtest_runner.py:init` clears `trades_log` for selected dates but NOT `reasoning_log`. The reasoning log grows unbounded.
- **Risk:** Disk fills, log analysis becomes slow. Also: 1 day of run produces 500+ reasonings, all 7 days of run = 3500+ in the log.
- **Fix:** Also clear reasonings for selected dates at run start, OR archive them.

### 5. **CACHE invalidation on prompt change**
- **Files:** `src/agents/llm_client.py:llm_ask`
- **Behavior:** LLM calls are cached by hash of (prompt + message). When we updated the 4-step prompt, R6, absorption hint, the cache STILL served old responses until cleared.
- **Risk:** A "validated" backtest could be running on stale LLM responses. This is why I saw inconsistent results between runs.
- **Fix:** Add a prompt_version to the cache key. 30 min.

---

## Recurring error patterns (from Apr-May run)

| Error | Count | Impact |
|---|---|---|
| `[WARN] content=None from model. finish_reason=length` | 6 | LLM hit token limit, response truncated |
| `[DEEP AUDIT WARN] audit fallito (Expecting value: line 1 column 1 (char 0))` | 2 | Deep audit returned empty string |
| `[GEX WARNING] No real GEX data found for 2025-05-26` | 38 | Day skipped, runs without GEX (correctly) but no signal |
| LLM call returned `model returned None` (finish_reason=error) | 0 in Apr-May run | OK in this run, but present in others |

The 6 `content=None` warnings mean **6 LLM calls returned incomplete output**. The system didn't retry, just took the (truncated) decision. This is a quality issue: a model that runs out of tokens probably truncated its reasoning, and the JSON might be malformed.

---

## Silent failure modes

### 1. `fabio_setup=reversal` reasonings present in log
- 6 reasonings in `reasoning_log.jsonl` have `fabio_setup: "reversal"` — which should be **globally disabled** per R5.
- The validator catches it (decision=no_trade, no_trade_reason="fabio_confidence=0"), but the LLM is still being called and consuming API budget. 6 wasted calls * $0.005 = $0.03/run. Trivial but wasteful.
- **Fix:** Add the setup_type check to the prompt (hardcode "DO NOT USE reversal") AND short-circuit before LLM call if setup is reversal.

### 2. Trailing "parse error" silently continues
- When APM gets parse error, returns "hold". The next APM call (1 min later) re-asks the LLM. The trade is effectively unmanaged for 1 min.
- In a fast market, 1 min = 30-50pt = $30-50 potential slippage.
- **Fix:** After 2 consecutive parse errors, force-close at market.

### 3. `fabio_confidence=0 < 70` is reported but not the real reason
- The no_trade_reason says "fabio_confidence=0 < 70" for many trades, but the actual reason was that the LLM never proposed a direction (e.g., directional = 'none').
- This is misleading for the dashboard. User saw this as "Motivo No Trade: Sconosciuto" because the field was unclear.
- **Fix:** When `decision=no_trade` and `direction=none`, set no_trade_reason to the LLM's actual reasoning excerpt (first 80 chars).

### 4. Trades silently dropped from log on rerun
- `src/agent_memory.py:log_trade_result` has idempotency check that drops duplicates. But this is good — actually a feature, not a bug. Noted for clarity.

### 5. `is_trade_already_logged` has timestamp precision issue
- Entry time is stored as ISO string. Two runs that open a trade at "14:20:00" would dedup correctly, but two runs opening at "14:20:00.123456" vs "14:20:00.654321" would NOT dedup → silent duplicate.

---

## Prompt fragility findings

### 1. 4-step prompt is 4300+ chars
- Tested in 4 different versions: 2K, 2.5K, 3.5K, 4.3K chars.
- At 4.3K, the model is more cautious (good for safety) but skips setups (bad for edge).
- The **soft absorption hint** (commit 130f974) was the right balance: lets model cite absorption, defers verification to deep audit.
- **No improvement from going >4.3K** — model attention drops after first 3K tokens.

### 2. STEP 3 absorption exception varies in interpretation
- The 4-step prompt says: "if bar.delta > 0 and big SELLS at the wall = absorption, bullish".
- But "AT the wall" is ambiguous: is the wall at the same price as the bar's low/high? Or at a nearby level?
- Result: model sometimes calls absorption, sometimes doesn't. Inconsistent application.
- **Fix:** Specify "at the bar's H or L, within 5pt". Be precise.

### 3. The "Sconosciuto" no_trade_reason
- When decision=`no_trade` and fabio_confidence=0, the no_trade_reason is set to "fabio_confidence=0 < 70" by the orchestrator, NOT by the LLM.
- The user saw "Motivo No Trade: Sconosciuto" on the dashboard — this came from a different field (`market_narrative.reasoning` was empty).
- **Fix:** Populate `no_trade_reason` from LLM's reasoning when `fabio_confidence < 70`.

---

## Trailing stop risk assessment

### 1. Trailing at rr=0.3 is aggressive
- With 8pt stop, trailing kicks in at +2.4pt profit.
- That's just 3pt above breakeven. A typical NQ bar has 4-6pt range, so a pullback to +1.5pt would NOT trigger trail but might hit BE on a reversion.
- **Reality:** trailing fires frequently on noise, and locks in micro-profits ($10-20) too often. This is **why 29 trail wins average only $55**.
- **Fix:** Trail at rr=0.8 (just under 1R), lock 50% of profit at rr=1.5. Result: fewer trailing activations, but bigger winners.

### 2. `_fmt_m1_window` default is 10
- The function is called with `max_bars=bars_held` (= 10 by default in M1).
- But the call site in `backtest_runner.py:547` passes `context_before=10` — so 10 bars *before* current.
- Total M1 context: 10 bars. That's 10 minutes of M1 data. **Not bad, not great.** The 4-step reflex sees 10 M5 bars, trailing sees 10 M1 bars. The asymmetry is intentional but could be more carefully tuned.
- **Fix:** For trailing, use 20 M1 bars (20 minutes) — enough to see one swing formation properly.

### 3. No safety: new_stop > target
- If LLM says "trail, new_stop = 21000" but target was 20990, the safety check `new_stop > trade.stop` passes (good for long), but no check that new_stop < target.
- Result: trailing can move stop ABOVE target, leaving no profit potential.
- **Fix:** Cap new_stop at `min(new_stop, target - 4)` for long, `max(new_stop, target + 4)` for short.

### 4. APM runs on every M1 bar from rr=0.3
- For a 30-min hold, that's ~30 LLM calls per trade just for trailing.
- At $0.005/call: $0.15 per trade. 100 trade/month: $15/month. Negligible.
- But if 10% of calls hit the `content=None` warning, that's wasted budget.
- **Fix:** Run APM every 5th M1 bar, not every 1st. Costs <$5/month, fewer parse errors.

---

## Data integrity issues

### 1. `trades_log.jsonl` had 2 duplicates
- Confirmed in audit. From `BACKTEST_FORCE=true` re-runs that re-opened the same trade.
- The idempotency check is good but has a precision issue (see Silent Failure 5).

### 2. Timestamps inconsistent
- `entry_time` is stored as ISO string.
- Some have `+00:00`, some don't.
- `backtest_runner.py` uses `pd.to_datetime()` and accepts both, but a strict parser would fail.

### 3. `equity` field in session_state not preserved correctly between runs
- Each backtest starts with `--reset-equity` flag, which sets to $50,000.
- But the equity I see in session_state.json is $50,570.90 — this is preserved from PREVIOUS runs.
- If the user runs `--reset-equity`, does that override the saved equity?
- **Bug:** `force_reset_equity(50000.0)` only fires if `--reset-equity` flag is set. Otherwise the saved equity is used.
- **Risk:** User thinks they're starting fresh at $50k but they're actually at $50,570. The PnL reported is correct, but the **equity baseline is inconsistent**.

---

## Specific bug investigations

### "Motivo No Trade: Sconosciuto"
- **Cause:** `latestReasoning.no_trade_reason` was empty string. UI fallback returned "Setup non confermato" → "Sconosciuto" if both empty.
- **Fix applied:** `AgentSidebar.jsx:103` now uses `openTrade` to detect active trade and skip the no-trade panel.

### Dashboard not showing open trade
- **Cause:** `live_sync_dashboard.py` was not writing `OPEN_TRADE` to status.json.
- **Fix applied:** `live_sync_dashboard.py:38` now writes `status['OPEN_TRADE'] = session.get('open_trade', None)`.
- **Followup fix:** `AgentSidebar.jsx:ContextAgentCard` had missing `openTrade` prop → ReferenceError broke the entire dashboard. Fixed in 619c6f7.

### Trade opened at 14:20, allegedly stopped at 14:21 not detected by backtest
- **Investigation:** Trade LONG @ 21388, stop 21371.43. Bar 18:20 had low=21376.00.
- **Math:** 21376 > 21371.43. The low did NOT touch the stop. Trade was NOT stopped.
- **UI bug:** The dashboard showed "Motivo No Trade: Sconosciuto" (see above). User thought the trade stopped. It didn't.
- **Status:** Confirmed false alarm, UI bug fixed.

### Trades with fabio_setup="reversal" still in log
- 6 reasonings show reversal as proposed setup.
- R5 (validator) blocks them at the orchestrator level. But the LLM is being called.
- **Fix:** Add a pre-LLM filter in `light_analyze()` (fabio_agent.py) to skip reversal setups before LLM call.

---

## Recommended fixes (priority-ordered)

1. **Production blocker:** Atomic session_state.json writes (1 hour, prevents corruption)
2. **High impact:** Cap new_stop at target level in trailing (1 hour, prevents stuck trades)
3. **High impact:** Populate no_trade_reason from LLM reasoning when direction=none (2 hours, fixes UI confusion)
4. **Medium:** Add pre-LLM filter for reversal setups (1 hour, saves API cost)
5. **Medium:** Clear reasonings for selected dates at run start (1 hour, prevents disk fill)
6. **Medium:** Add prompt_version to LLM cache key (30 min, prevents stale responses)
7. **Low:** Run APM every 5th M1 bar instead of every 1st (2 hours, reduces parse errors)
8. **Low:** Trail at rr=0.8 instead of rr=0.3 (2 hours, lets winners run)
9. **Low:** Force-close on 2 consecutive APM parse errors (1 hour, safety)

Total estimated: 11.5 hours for all fixes.

---

*Generated by Code & Log Detective. Sources: `output/v2_*.log` (Apr-May run), `src/`, `agent_memory/`.*
