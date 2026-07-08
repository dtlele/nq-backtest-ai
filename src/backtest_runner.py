"""
Main backtest loop.
For each day:
  1. Load trades from CSV
  2. Aggregate to 1-min bars
  3. Filter NY window
  4. Build Volume Profile (from all session bars)
  5. Build SessionContext (IB, day_type)
  6. Detect candidates
  7. For each candidate: Fabio → Andrea → Consensus
  8. If consensus=trade: drop to M1 → precision entry/stop/target
  9. TradeSimulator uses M1-refined levels
  10. Log to agent_memory, collect ClosedTrades
"""
import json
import datetime
from pathlib import Path
from src.data_loader import load_day, list_data_files
from src.bar_aggregator import aggregate_to_bars
from src.volume_profile import compute_volume_profile
from src import SessionContext
from src.session_context import filter_ny_window, filter_overnight_window, filter_rth_session, build_session_context, update_day_type
from src.candidate_detector import detect_candidates
from src.agents.fabio_agent import analyze as fabio_analyze, light_analyze as fabio_light, manage_active_trade
from src.agents.andrea_agent import confirm as andrea_confirm
from src.agents.precision_entry import refine_entry, get_m1_context
from src.consensus import build_consensus
from src.trade_simulator import open_trade, step_trade, close_eod, close_early, check_pending_fill
from src.agent_memory import (
    reset_session, log_reasoning, update_pattern_memory, log_trade_result,
    get_already_processed_candidates, is_trade_already_logged,
    load_session, save_session
)
from src.risk_manager import calculate_contracts
from src.agents.nlm_daily import queue_daily_question
from src.signal_context import get_amt_structural_profile, analyze_macro_regime, analyze_trapped_participants, analyze_trap_follow_through, detect_accumulation_breakout
from src import (
    FABIO_MIN_CONFIDENCE, LIGHT_CONFIDENCE_THRESHOLD, 
    CandidateBar, AndreaSignal, FabioSignal, ConsensusSignal, PendingTrade
)
from typing import Optional

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'

MAX_SESSION_BUFFER = 5  # keep last N analyses for cross-bar context

from src.news_manager import NewsManager
news_manager = NewsManager()

def _append_session(buf: list, bar_ts: str, fabio_signal) -> None:
    """Append a 1-line summary to the session buffer, keep last N entries."""
    reason_short = fabio_signal.reasoning[:80].replace('\n', ' ')
    buf.append(
        f"{bar_ts} {fabio_signal.direction}({fabio_signal.confidence}) "
        f"{fabio_signal.setup_type} — {reason_short}"
    )
    if len(buf) > MAX_SESSION_BUFFER:
        buf.pop(0)


def _should_prefilter(candidate: CandidateBar) -> Optional[str]:
    """Return reason string if candidate should be skipped, None to proceed.
    
    NOTE: Volume threshold is intentionally NOT checked here.
    The LLM must always analyze every bar to maintain session context.
    Volume-based execution veto is applied later, at trade-open time.
    """
    return None  # disabled: always run full analysis for every candidate bar

def run_day(csv_path: str, dry_run: bool = False, quiet: bool = False, prev_day_vp=None, fabio_only: bool = True, historical_days: list = None, start_time: str = None) -> tuple:
    """Run backtest for one day. Returns (list[ClosedTrade], today_vp, today_close)."""
    date_str = Path(csv_path).name.split('-')[2].split('.')[0]  # e.g. 20250430
    date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    
    # ── BLACKOUT DAY CHECK (Tier 1 News) ──────────────
    is_blackout, reason = news_manager.is_blackout_day(date_str)
    if is_blackout:
        print(f"  [SKIPPED] {date_str} is a Blackout Day due to: {reason}. No trading allowed.")
        return [], prev_day_vp, 0.0

    # ── THURSDAY SKIP (WR 29.2%, only losing day of the week) ───────
    import datetime as _dt
    _dow = _dt.date.fromisoformat(date_str).weekday()  # 0=Mon ... 4=Thu
    if _dow == 3:  # Thursday
        print(f"  [SKIPPED] {date_str} is Thursday (WR 29.2%, net -$165.70 historically). Saving API calls.")
        return [], prev_day_vp, 0.0

    reset_session(date_str)
    trades_raw = load_day(csv_path)

    print("  Aggregating 1-minute bars...")
    bars_1min_all = aggregate_to_bars(trades_raw, freq='1min')
    
    # VP uses overnight bars (midnight to 09:30 ET)
    bars_1min_overnight = filter_overnight_window(bars_1min_all)
    vp = compute_volume_profile(bars_1min_overnight)

    # IB and Day Type use 1-min bars from NY window
    bars_1min_ny = filter_ny_window(bars_1min_all)
    if not bars_1min_ny:
        return [], vp, 0.0   # Return whatever VP was computed from overnight
        
    ctx = build_session_context(date_str, bars_1min_ny, vp, prev_day_vp=prev_day_vp, historical_days=historical_days)
    today_close = bars_1min_ny[-1].close

    # Candidate detection and agent reasoning use M5 bars (only for macro context)
    bars_ny = filter_ny_window(aggregate_to_bars(trades_raw, freq='5min'))
    
    from src.candidate_detector import detect_candidates, detect_m1_candidates
    from src.session_context import is_fabio_active, compute_ib, update_session_memory, get_session_memory_up_to
    
    candidates = detect_candidates(bars_ny, ctx, bars_1min_ny=bars_1min_ny, bars_1min_overnight=bars_1min_overnight)

    # Inject M1 candidates for Imbalance Hunting
    existing_ts = {c.bar.timestamp for c in candidates}
    m1_candidates = []
    
    for idx, m1_bar in enumerate(bars_1min_ny):
        if not is_fabio_active(m1_bar, ctx=ctx) or m1_bar.timestamp in existing_ts:
            continue
        # Find recent M5 bars up to this M1 bar for macro context
        m5_recent = [b for b in bars_ny if b.timestamp <= m1_bar.timestamp][-5:]
        # History of M1 bars up to (but not including) this one, for RVOL/VWAP
        m1_history = bars_1min_ny[:idx]
        
        # --- DYNAMIC IB UPDATE (Eliminates Lookahead Bias) ---
        if m1_history:
            dyn_ib_high, dyn_ib_low = compute_ib(m1_history)
            if dyn_ib_high > 0:
                ctx.ib_high = dyn_ib_high
                ctx.ib_low = dyn_ib_low
                ctx.ib_range = round(dyn_ib_high - dyn_ib_low, 2)
                
                # Check completion using timezone-aware time comparison (matching build_session_context)
                import pytz as _br_pytz
                import datetime as _dt
                from src import IB_DURATION_MIN
                _br_ET = _br_pytz.timezone('America/New_York')
                latest_t = m1_bar.timestamp.astimezone(_br_ET)
                ny_open = latest_t.replace(hour=9, minute=30, second=0, microsecond=0)
                ib_end = ny_open + _dt.timedelta(minutes=IB_DURATION_MIN)
                ctx.ib_complete = latest_t >= ib_end

        # Update dynamic session memory tracker
        update_session_memory(ctx, m1_bar, bars_1min_ny[:idx+1])

        cands = detect_m1_candidates(m1_bar, m5_recent, ctx, m1_history=m1_history)
        m1_candidates.extend(cands)
        
    def get_candidate_eval_ts(c):
        import datetime as _dt
        duration = 1 if c.setup_category == 'imbalance_hunting' else 5
        return c.bar.timestamp + _dt.timedelta(minutes=duration)

    candidates.extend(m1_candidates)
    candidates.sort(key=get_candidate_eval_ts)

    trade_start_i = -1
    closed_trades = []
    
    open_t = None
    pending_t = None
    daily_stops_count = 0
    
    # Session context variables
    session_buffer = []     # OPT 4: cross-bar context (last 5 analyses)
    market_narrative = "Inizio giornata. Nessuna narrativa."
    last_eval_idx = 0
    
    # Money Management state
    daily_stops_count = 0
    last_stop_time = None
    recent_losses = []



    
    def sync_session_state(open_t, closed_trades, ctx, equity_change=0.0, pending_t=None):
        state = load_session()
        if equity_change != 0.0:
            state['equity'] += equity_change
            
        if open_t is not None:
            entry_time_val = getattr(open_t, 'entry_time', None) or open_t.entry_bar.timestamp
            state['open_trade'] = {
                'direction': open_t.direction,
                'entry': open_t.entry,
                'stop': open_t.stop,
                'target': open_t.target,
                'entry_time': entry_time_val.isoformat() if hasattr(entry_time_val, 'isoformat') else entry_time_val,
                'contracts': open_t.contracts,
                'news_flag': open_t.news_flag
            }
        else:
            state['open_trade'] = None
            
        if pending_t is not None:
            state['pending_trade'] = {
                'direction': pending_t.direction,
                'entry': pending_t.limit_price,
                'stop': pending_t.stop,
                'target': pending_t.target,
                'contracts': pending_t.contracts,
                'expires_at': pending_t.expires_at.isoformat() if hasattr(pending_t.expires_at, 'isoformat') else pending_t.expires_at
            }
        else:
            state['pending_trade'] = None
        
        state['daily_pnl_usd'] = sum(t.pnl_usd for t in closed_trades)
        state['trade_count_today'] = len(closed_trades)
        
        if ctx:
            state['ib_high'] = ctx.ib_high
            state['ib_low'] = ctx.ib_low
            state['poc'] = ctx.vp.poc if ctx.vp else None
            state['day_type'] = ctx.day_type
            
        save_session(state)

    def handle_close(result, session_buffer, daily_stops_count):
        closed_trades.append(result)
        from src.memory.quantitative_memory import log_trade_for_quantitative_memory
        log_trade_for_quantitative_memory(result)
        # update_pattern_memory(result)
        
        sync_session_state(None, closed_trades, ctx, equity_change=result.pnl_usd)
        
        if not is_trade_already_logged(date_str, result.entry_time.isoformat(), result.exit_reason):
            log_trade_result(result)
        if result.exit_reason == 'stop' and result.pnl_ticks < 0:
            daily_stops_count += 1
            recent_losses.append({'time': result.exit_time, 'direction': result.direction})
            print(f"  [MONEY MANAGEMENT] Stop loss hit. Daily stops: {daily_stops_count}.")
        elif result.exit_reason == 'stop':
            print(f"  [MONEY MANAGEMENT] Trailing stop hit in profit (+{result.pnl_ticks:.1f} ticks).")

        close_time_str = result.exit_time.strftime('%H:%M UTC')
        session_buffer.append(f"[TRADE CLOSED] {close_time_str} {result.direction.upper()} exit={result.exit_reason} pnl={result.pnl_usd:.1f}$")
        if len(session_buffer) > MAX_SESSION_BUFFER:
            session_buffer.pop(0)
        return daily_stops_count

    # Load processed candidates to allow fast-forward
    processed_candidates = get_already_processed_candidates()

    import pytz as _ff_pytz
    _ff_ET = _ff_pytz.timezone('America/New_York')

    for candidate in candidates:
        eval_ts = get_candidate_eval_ts(candidate)
        
        # Find the index of the M5 bar that is currently open or just closed
        last_m5_idx = None
        for i, b in enumerate(bars_ny):
            if b.timestamp <= candidate.bar.timestamp:
                last_m5_idx = i
            else:
                break
                
        if last_m5_idx is None:
            continue
            
        bar_idx = last_m5_idx

        bar_ts = eval_ts.strftime('%H:%M UTC')
        bar_et = eval_ts.astimezone(_ff_ET).strftime('%H:%M')
        orig_bar_et = candidate.bar.timestamp.astimezone(_ff_ET).strftime('%H:%M')
        
        # --- COOLDOWN CHECK (Avoid overtrading / chain-trading) ---
        last_close_time = None
        if closed_trades:
            last_close_time = closed_trades[-1].exit_time
        if last_close_time is not None:
            strat_config = {}
            try:
                from src.signal_context import get_strategy_config
                strat_config = get_strategy_config()
            except Exception:
                pass
            cooldown_minutes = 0  # Reverted: Cooldown checks delegated to LLM reasoning
            time_since_last_close = (eval_ts - last_close_time).total_seconds() / 60.0
            if time_since_last_close < cooldown_minutes:
                if not quiet:
                    print(f"  {bar_ts} [SKIPPED] Cooldown active. Time since last trade: {time_since_last_close:.1f}m < {cooldown_minutes}m")
                log_entry = {
                    'date': date_str,
                    'bar_time_utc': eval_ts.isoformat(),
                    'bar_time_et': bar_et,
                    'bar_open': candidate.bar.open,
                    'bar_high': candidate.bar.high,
                    'bar_low': candidate.bar.low,
                    'bar_close': candidate.bar.close,
                    'bar_volume': candidate.bar.volume,
                    'bar_delta': candidate.bar.delta,
                    'wall_level': candidate.wall_level,
                    'wall_side': candidate.wall_side,
                    'wall_max_size': candidate.wall_max_size,
                    'wall_trade_count': candidate.wall_trade_count,
                    'proximity_to': candidate.proximity_to,
                    'proximity_level': candidate.proximity_level,
                    'ib_high': ctx.ib_high,
                    'ib_low': ctx.ib_low,
                    'ib_range': ctx.ib_range,
                    'poc': ctx.vp.poc if ctx.vp else None,
                    'va_high': ctx.vp.va_high if ctx.vp else None,
                    'va_low': ctx.vp.va_low if ctx.vp else None,
                    'day_type': ctx.day_type,
                    'market_state': getattr(candidate, 'market_state', 'balance'),
                    'market_structure': ctx.market_structure_state,
                    'delta_divergence': getattr(candidate, 'delta_divergence', False),
                    'effort_no_result': getattr(candidate, 'effort_no_result', False),
                    'top_wick_ratio': getattr(candidate, 'top_wick_ratio', 0.0),
                    'bottom_wick_ratio': getattr(candidate, 'bottom_wick_ratio', 0.0),
                    'close_percentile': getattr(candidate, 'close_percentile', 0.5),
                    'prev_day_poc': ctx.prev_day_vp.poc if ctx.prev_day_vp else None,
                    'prev_day_vah': ctx.prev_day_vp.va_high if ctx.prev_day_vp else None,
                    'prev_day_val': ctx.prev_day_vp.va_low if ctx.prev_day_vp else None,
                    'session_bias': candidate.session_bias,
                    'decision': 'no_trade',
                    'no_trade_reason': f'cooldown_active_time_since_last_close_{time_since_last_close:.1f}m'
                }
                log_reasoning(log_entry)
                continue

        # TIME-SKIP: Skip evaluations before start_time to save tokens
        if start_time and orig_bar_et < start_time:
            import pytz as _pytz
            _ET = _pytz.timezone('America/New_York')
            bar_et_full = eval_ts.astimezone(_ET).strftime('%H:%M')
            if not quiet:
                print(f"  {candidate.bar.timestamp.strftime('%H:%M UTC')} [SKIPPED] before start_time={start_time} (no LLM call)")
            log_entry = {
                'date': date_str,
                'bar_time_utc': eval_ts.isoformat(),
                'bar_time_et': bar_et_full,
                'bar_open': candidate.bar.open,
                'bar_high': candidate.bar.high,
                'bar_low': candidate.bar.low,
                'bar_close': candidate.bar.close,
                'bar_volume': candidate.bar.volume,
                'bar_delta': candidate.bar.delta,
                'wall_level': candidate.wall_level,
                'wall_side': candidate.wall_side,
                'wall_max_size': candidate.wall_max_size,
                'wall_trade_count': candidate.wall_trade_count,
                'proximity_to': candidate.proximity_to,
                'proximity_level': candidate.proximity_level,
                'ib_high': ctx.ib_high,
                'ib_low': ctx.ib_low,
                'ib_range': ctx.ib_range,
                'poc': ctx.vp.poc if ctx.vp else None,
                'va_high': ctx.vp.va_high if ctx.vp else None,
                'va_low': ctx.vp.va_low if ctx.vp else None,
                'day_type': ctx.day_type,
                'market_state': getattr(candidate, 'market_state', 'balance'),
                'market_structure': ctx.market_structure_state,
                'delta_divergence': getattr(candidate, 'delta_divergence', False),
                'effort_no_result': getattr(candidate, 'effort_no_result', False),
                'top_wick_ratio': getattr(candidate, 'top_wick_ratio', 0.0),
                'bottom_wick_ratio': getattr(candidate, 'bottom_wick_ratio', 0.0),
                'close_percentile': getattr(candidate, 'close_percentile', 0.5),
                'prev_day_poc': ctx.prev_day_vp.poc if ctx.prev_day_vp else None,
                'prev_day_vah': ctx.prev_day_vp.va_high if ctx.prev_day_vp else None,
                'prev_day_val': ctx.prev_day_vp.va_low if ctx.prev_day_vp else None,
                'session_bias': candidate.session_bias,
                'fabio_direction': 'none',
                'fabio_imbalance_phase': 'none',
                'fabio_confidence': 0,
                'fabio_setup': 'none',
                'fabio_entry': None,
                'fabio_stop': None,
                'fabio_target': None,
                'fabio_reasoning': f'Skipped because time ({bar_et}) is before start_time ({start_time}).',
                'market_narrative': market_narrative,
                'session_memory': get_session_memory_up_to(ctx, candidate.bar.timestamp),
                'andrea_confirmation': None,
                'andrea_confidence': None,
                'andrea_setup': None,
                'andrea_reasoning': None,
                'final_confidence': None,
                'decision': 'no_trade',
                'no_trade_reason': 'time_skip',
                'trade_direction': None,
                'trade_entry': None,
                'trade_stop': None,
                'trade_target': None,
                'trade_pnl_usd': None,
                'trade_pnl_ticks': None,
                'trade_exit_reason': None,
            }
            log_reasoning(log_entry)
            session_buffer.append(f"{bar_ts} none(0) none — skipped before start_time")
            if len(session_buffer) > MAX_SESSION_BUFFER:
                session_buffer.pop(0)
            update_day_type(ctx, bars_ny[:bar_idx+1])
            last_eval_idx = bar_idx
            continue

        # FAST-FORWARD: Skip if already in reasoning_log
        if (date_str, bar_et) in processed_candidates:
            if not quiet:
                print(f"  {bar_ts} [SKIPPED BUT EVALUATING ANYWAY] Found in cache, but fast-forward is disabled.")
            # We still need to keep the session_buffer updated for future context if any
            # Note: in a real fast-forward we might want to re-load the fabio_signal from log
            # but for now skipping is enough to prevent duplicates.
            # continue  <-- DISABLED FOR NOW TO FORCE FULL BACKTEST

        # If a trade is open or pending, manage it actively candle-by-candle (APM or Pending Fill)
        if open_t is not None or pending_t is not None:
            # Evaluate the trade on every M1 bar since the last evaluation, up to the current candidate
            last_eval_time = None
            if open_t is not None:
                if getattr(open_t, 'last_eval_time', None) is None:
                    open_t.last_eval_time = getattr(open_t, 'entry_time', open_t.entry_bar.timestamp)
                last_eval_time = open_t.last_eval_time
            if pending_t is not None:
                if getattr(pending_t, 'last_eval_time', None) is None:
                    pending_t.last_eval_time = pending_t.signal_bar.timestamp
                
                if last_eval_time is None or pending_t.last_eval_time < last_eval_time:
                    last_eval_time = pending_t.last_eval_time
                
            m1_intermediate = [b for b in bars_1min_ny if last_eval_time < b.timestamp <= eval_ts]
            
            trade_closed_early = False
            for m1_bar in m1_intermediate:
                # 1. Process PENDING trades
                if pending_t is not None:
                    if m1_bar.timestamp >= pending_t.expires_at:
                        print(f"  [PENDING EXPIRED] Limit order at {pending_t.limit_price} expired without fill.")
                        pending_t = None
                    else:
                        filled = check_pending_fill(pending_t, m1_bar)
                        if filled:
                            if open_t is not None:
                                # SCALE-IN: Merge the filled trade into the existing open_t
                                new_contracts = open_t.contracts + filled.contracts
                                new_entry = ((open_t.entry * open_t.contracts) + (filled.entry * filled.contracts)) / new_contracts
                                open_t.entry = new_entry
                                open_t.contracts = new_contracts
                                print(f"  [SCALE-IN FILLED] Limit order triggered! Avg entry now {new_entry:.2f} for {new_contracts} contracts.")
                                sync_session_state(open_t, closed_trades, ctx)
                            else:
                                open_t = filled
                                print(f"  [PENDING FILLED] Limit order triggered at {open_t.entry}!")
                                sync_session_state(open_t, closed_trades, ctx)
                            pending_t = None
                
                # 2. Process OPEN trades
                if open_t is not None:
                    def on_partial(result_part):
                        nonlocal daily_stops_count
                        daily_stops_count = handle_close(result_part, session_buffer, daily_stops_count)
                        print(f"  [PARTIAL TP] Closed 50% of contracts at {result_part.exit_price:.2f}. Remaining contracts: {open_t.contracts:.4f}. Stop moved to BE: {open_t.stop:.2f}")

                    # Keep track of stop and contracts before step_trade to detect trailing stop or partial TP changes
                    old_stop = open_t.stop
                    old_contracts = open_t.contracts

                    result = step_trade(open_t, [m1_bar], 
                                        first_bar_after_entry=(m1_bar.timestamp == getattr(open_t, 'entry_time', open_t.entry_bar.timestamp)),
                                        on_partial_close=on_partial,
                                        session_bars=bars_1min_ny)
                    if result:
                        daily_stops_count = handle_close(result, session_buffer, daily_stops_count)
                        open_t = None
                        trade_closed_early = True
                        break
                    
                    if open_t.stop != old_stop or open_t.contracts != old_contracts:
                        sync_session_state(open_t, closed_trades, ctx)
                    
                    open_t.last_eval_time = m1_bar.timestamp
                    # Enable active APM trailing stop dynamically based on strategy configuration
                    from src.signal_context import get_strategy_config
                    try:
                        strat_config = get_strategy_config()
                    except Exception:
                        strat_config = {}
                        
                    # --- CALCULATE CURRENT R:R ---
                    risk_points = abs(open_t.entry - open_t.stop)
                    if risk_points > 0:
                        if open_t.direction == 'long':
                            pnl_points = m1_bar.close - open_t.entry
                        else:
                            pnl_points = open_t.entry - m1_bar.close
                        current_rr = pnl_points / risk_points
                    else:
                        current_rr = 0.0

                    should_run_apm = False
                    is_runner_mode = False
                    
                    if current_rr >= 2.0:
                        should_run_apm = True
                        is_runner_mode = True
                    elif strat_config.get("apm_trailing_stop_enabled", False) and open_t.contracts >= 3:
                        if m1_bar.timestamp.minute % 2 == 0:
                            should_run_apm = True
                        elif getattr(m1_bar, 'big_trades', []):
                            should_run_apm = True
                        
                    if m1_bar.timestamp > getattr(open_t, 'entry_time', open_t.entry_bar.timestamp) and should_run_apm:
                        print(f"  [MANAGEMENT] Active {open_t.direction.upper()} trade open at {m1_bar.timestamp.strftime('%H:%M UTC')}. Consulting Fabio APM...")
                        m1_context = get_m1_context(bars_1min_ny, m1_bar)
                        
                        from src import CandidateBar
                        dummy_cand = CandidateBar(bar=m1_bar, session_ctx=ctx, wall_level=open_t.entry, wall_side='none', wall_trade_count=0, wall_max_size=0, proximity_to='none', proximity_level=0, bars_in_session=0, is_second_test=False)
                        
                        # INJECT RUNNER MODE PROMPT IF APPLICABLE
                        active_narrative = market_narrative
                        if is_runner_mode:
                            active_narrative += f"\n\n🎯 [RUNNER MODE ACTIVATED — {current_rr:.2f} R:R]\nThe trade has reached {current_rr:.2f} R:R profit. PRIMARY OBJECTIVE: do NOT let this become a loser. However, do NOT trail aggressively without structural confirmation.\n\nTRAIL ONLY if ALL of these are true:\n1. A new structural event has occurred (new swing low for LONG, body close past key structural level)\n2. A Big Trade cluster (>=30 contracts) in your direction has ACCEPTED at a new level\n3. The new stop gives at least 15-20 ticks of breathing room behind the structural event\n\nIf no clear structural event → output 'hold'. Giving the trade room to reach the target is worth more than an early trail. DEFAULT = HOLD."

                        apm = manage_active_trade(
                            trade=open_t,
                            candidate=dummy_cand,
                            session_context=session_buffer,
                            m1_bars=m1_context,
                            market_narrative=active_narrative,
                            bars_since_last=[]
                        )
                        open_t.last_eval_time = m1_bar.timestamp
                        
                        decision = apm.get("decision", "hold")
                        reasoning = apm.get("reasoning", "")
                        safe_reasoning = reasoning.encode('cp1252', 'ignore').decode('cp1252')
                        print(f"  [MANAGEMENT] Fabio APM decision: {decision.upper()} | Reasoning: {safe_reasoning}")
                        
                        # Log APM reasoning to reasoning_log.jsonl so dashboard shows it
                        try:
                            import pytz
                            ET_tz = pytz.timezone('America/New_York')
                            apm_log = {
                                "date": ctx.date,
                                "bar_time_utc": m1_bar.timestamp.isoformat(),
                                "bar_time_et": m1_bar.timestamp.astimezone(ET_tz).strftime('%H:%M'),
                                "bar_open": m1_bar.open,
                                "bar_high": m1_bar.high,
                                "bar_low": m1_bar.low,
                                "bar_close": m1_bar.close,
                                "bar_volume": m1_bar.volume,
                                "bar_delta": m1_bar.delta,
                                "wall_level": open_t.entry,
                                "wall_side": "none",
                                "wall_max_size": 0,
                                "wall_trade_count": 0,
                                "proximity_to": "none",
                                "proximity_level": 0,
                                "ib_high": ctx.ib_high,
                                "ib_low": ctx.ib_low,
                                "ib_range": ctx.ib_range,
                                "poc": ctx.vp.poc if ctx.vp else 0.0,
                                "va_high": ctx.vp.va_high if ctx.vp else 0.0,
                                "va_low": ctx.vp.va_low if ctx.vp else 0.0,
                                "day_type": ctx.day_type,
                                "market_state": "active_trade_mgmt",
                                "session_bias": open_t.direction,
                                "fabio_direction": "none",
                                "fabio_imbalance_phase": "none",
                                "fabio_confidence": 100,
                                "fabio_setup": "apm",
                                "fabio_entry": open_t.entry,
                                "fabio_stop": open_t.stop,
                                "fabio_target": open_t.target,
                                "fabio_reasoning": reasoning,
                                "market_narrative": active_narrative,
                                "decision": f"apm_{decision}",
                                "no_trade_reason": f"APM: {decision.upper()} - {reasoning}",
                                "entry_type": "apm"
                            }
                            log_reasoning(apm_log)
                        except Exception as log_err:
                            print(f"  [MANAGEMENT WARNING] Failed to log APM reasoning: {log_err}")
                        
                        if decision == 'early_exit':
                            result = close_early(open_t, m1_bar, reasoning)
                            daily_stops_count = handle_close(result, session_buffer, daily_stops_count)
                            open_t = None
                            trade_closed_early = True
                            break
                            
                        elif decision == 'reverse':
                            result = close_early(open_t, m1_bar, "reversed")
                            daily_stops_count = handle_close(result, session_buffer, daily_stops_count)
                            
                            # 2. Extract reverse parameters
                            rev_dir = 'short' if open_t.direction == 'long' else 'long'
                            rev_entry = m1_bar.close
                            
                            rev_stop = apm.get("new_stop")
                            if not rev_stop:
                                rev_stop = rev_entry - 30 * 0.25 if rev_dir == 'long' else rev_entry + 30 * 0.25
                            
                            rev_target = apm.get("new_target")
                            if not rev_target:
                                rev_target = rev_entry + 60 * 0.25 if rev_dir == 'long' else rev_entry - 60 * 0.25
                            
                            class _RevConsensus:
                                def __init__(self):
                                    self.direction = rev_dir
                                    self.entry = rev_entry
                                    self.stop = rev_stop
                                    self.target = rev_target
                                    risk = abs(self.entry - self.stop)
                                    reward = abs(self.target - self.entry)
                                    self.r_ratio = round(reward / risk, 2) if risk > 0 else 2.0
                                    class _Sub:
                                        setup_type = 'reverse_continuation'
                                        reasoning = apm.get("reasoning", "")
                                    self.fabio = _Sub()
                                    self.andrea = _Sub()
                                    self.final_confidence = 75
                            
                            rev_consensus = _RevConsensus()
                            risk_pct = strat_config.get("risk_pct", 0.001)
                            rev_contracts = calculate_contracts(
                                rev_entry, rev_stop,
                                load_session()['equity'], risk_pct=risk_pct,
                                instrument='MNQ',
                                setup_category='reversal'
                            )
                            
                            import datetime as _dt
                            open_t = open_trade(rev_consensus, m1_bar, contracts=rev_contracts, entry_time=m1_bar.timestamp + _dt.timedelta(minutes=1))
                            open_t.last_eval_time = m1_bar.timestamp
                            print(f"  [REVERSE OPEN] 🔄 Opened reverse {rev_dir.upper()} at {rev_entry} | stop={rev_stop}")
                            sync_session_state(open_t, closed_trades, ctx)
                            session_buffer.append(f"🔄 [REVERSED] {m1_bar.timestamp.strftime('%H:%M UTC')} {rev_dir.upper()} entry={rev_entry}")
                            
                            trade_closed_early = True
                            break
                            
                        elif decision == 'trail':
                            new_stop = apm.get("new_stop")
                            new_target = apm.get("new_target")
                            updated = False
                            if new_stop:
                                is_valid = False
                                if open_t.direction == 'long' and new_stop > open_t.stop:
                                    is_valid = True
                                elif open_t.direction == 'short' and new_stop < open_t.stop:
                                    is_valid = True
                                    
                                if is_valid:
                                    print(f"  [TRAILING SL] Moving stop from {open_t.stop:.2f} -> {new_stop:.2f} | event: {apm.get('structural_event','?')}")
                                    open_t.stop = new_stop
                                    updated = True
                                    session_buffer.append(f"🛡️ [TRAILED SL] {m1_bar.timestamp.strftime('%H:%M UTC')} stop={new_stop:.2f}")
                            if new_target:
                                open_t.target = new_target
                                updated = True
                            if updated:
                                sync_session_state(open_t, closed_trades, ctx)
                                

                
            # We do NOT skip candidate evaluation when a trade is active because we want to see if
            # new signals confirm holding the trade. However, we will not open a new trade if one is active.
            pass


        if dry_run:
            import pytz
            ET = pytz.timezone('America/New_York')
            print(f"\n  [DRY RUN] {candidate.bar.timestamp.astimezone(ET).strftime('%H:%M ET')} "
                  f"| wall={candidate.wall_level:.2f} ({candidate.wall_side})"
                  f" | near={candidate.proximity_to}@{candidate.proximity_level:.2f}")
            for b in candidate.recent_bars:
                t_et = b.timestamp.astimezone(ET)
                mkr = ' <--' if b is candidate.bar else ''
                print(f"    {t_et.strftime('%H:%M')} O={b.open:.2f} H={b.high:.2f} "
                      f"L={b.low:.2f} C={b.close:.2f} V={b.volume} d={b.delta:+d}"
                      f"{(' BIG='+str(sum(t.size for t in b.big_trades))) if b.big_trades else ''}{mkr}")
            continue

        # ── OPT 2: Pre-filter obvious NO_TRADE candidates ──────────
        bar_ts = candidate.bar.timestamp.strftime('%H:%M UTC')
        prefilter_reason = _should_prefilter(candidate)
        if prefilter_reason:
            print(f"  {bar_ts} [PREFILTERED] {prefilter_reason}")
            import pytz as _pf_pytz
            _pf_ET = _pf_pytz.timezone('America/New_York')
            bar_et = candidate.bar.timestamp.astimezone(_pf_ET).strftime('%H:%M')
            log_reasoning({
                'date': date_str, 'bar_time_utc': candidate.bar.timestamp.isoformat(),
                'bar_time_et': bar_et,
                'bar_open': candidate.bar.open, 'bar_high': candidate.bar.high,
                'bar_low': candidate.bar.low, 'bar_close': candidate.bar.close,
                'bar_volume': candidate.bar.volume, 'bar_delta': candidate.bar.delta,
                'wall_level': candidate.wall_level, 'wall_side': candidate.wall_side,
                'wall_max_size': candidate.wall_max_size,
                'wall_trade_count': candidate.wall_trade_count,
                'proximity_to': candidate.proximity_to,
                'proximity_level': candidate.proximity_level,
                'ib_high': ctx.ib_high, 'ib_low': ctx.ib_low, 'ib_range': ctx.ib_range,
                'poc': ctx.vp.poc if ctx.vp else None,
                'va_high': ctx.vp.va_high if ctx.vp else None,
                'va_low': ctx.vp.va_low if ctx.vp else None,
                'day_type': ctx.day_type,
                'market_state': getattr(candidate, 'market_state', 'balance'),
                'market_structure': ctx.market_structure_state,
                'fabio_direction': 'prefiltered', 'fabio_imbalance_phase': 'none', 'fabio_confidence': 0,
                'fabio_setup': 'none', 'fabio_reasoning': prefilter_reason,
                'decision': 'prefiltered', 'no_trade_reason': prefilter_reason,
            })
            session_buffer.append(f"{bar_ts} prefiltered(0) — {prefilter_reason}")
            continue

        # Extract bars since last evaluation
        bars_since_last = []
        if last_eval_idx < bar_idx:
            bars_since_last = bars_ny[last_eval_idx:bar_idx]
            
        # ── DYNAMIC STOP-HUNT INJECTION ──
        candidate.active_stop_hunt = False
        candidate.stop_hunt_direction = ""
        if recent_losses:
            last_loss = recent_losses[-1]
            if (candidate.bar.timestamp - last_loss['time']).total_seconds() <= 180:
                candidate.active_stop_hunt = True
                candidate.stop_hunt_direction = last_loss['direction']

        # ── OPT 3: Two-pass (light → full) ──────────────────────────
        if not dry_run:
            light_conf = fabio_light(candidate, session_context=session_buffer, market_narrative=market_narrative, bars_since_last=bars_since_last)
            if False:  # disabled: always run full analysis for every candidate bar
                print(f"  {bar_ts} [LIGHT] conf={light_conf} -> skip")
                import pytz as _lt_pytz
                _lt_ET = _lt_pytz.timezone('America/New_York')
                bar_et = candidate.bar.timestamp.astimezone(_lt_ET).strftime('%H:%M')
                log_reasoning({
                    'date': date_str, 'bar_time_utc': candidate.bar.timestamp.isoformat(),
                    'bar_time_et': bar_et,
                    'bar_open': candidate.bar.open, 'bar_high': candidate.bar.high,
                    'bar_low': candidate.bar.low, 'bar_close': candidate.bar.close,
                    'bar_volume': candidate.bar.volume, 'bar_delta': candidate.bar.delta,
                    'wall_level': candidate.wall_level, 'wall_side': candidate.wall_side,
                    'wall_max_size': candidate.wall_max_size,
                    'wall_trade_count': candidate.wall_trade_count,
                    'proximity_to': candidate.proximity_to,
                    'proximity_level': candidate.proximity_level,
                    'ib_high': ctx.ib_high, 'ib_low': ctx.ib_low, 'ib_range': ctx.ib_range,
                    'poc': ctx.vp.poc if ctx.vp else None,
                    'va_high': ctx.vp.va_high if ctx.vp else None,
                    'va_low': ctx.vp.va_low if ctx.vp else None,
                    'day_type': ctx.day_type,
                    'market_state': getattr(candidate, 'market_state', 'balance'),
                    'market_structure': ctx.market_structure_state,
                    'fabio_direction': 'light_skip', 'fabio_imbalance_phase': 'none', 'fabio_confidence': light_conf,
                    'fabio_setup': 'none', 'fabio_reasoning': f'light pass conf={light_conf}',
                    'decision': 'light_skip', 'no_trade_reason': f'light_conf={light_conf} <= {LIGHT_CONFIDENCE_THRESHOLD}',
                })
                session_buffer.append(f"{bar_ts} light_skip({light_conf}) none")
                if len(session_buffer) > MAX_SESSION_BUFFER:
                    session_buffer.pop(0)
                continue

        # Check for Macroeconomic News context
        upcoming_news = news_manager.get_upcoming_news(candidate.bar.timestamp)
        candidate.upcoming_news = upcoming_news

        # --- AUTONOMOUS TELEGRAM CRON ---
        global _last_tele_update
        if '_last_tele_update' not in globals():
            _last_tele_update = datetime.datetime.now()
        
        now_ts = datetime.datetime.now()
        if (now_ts - _last_tele_update).total_seconds() >= 5 * 60:
            try:
                _telegram_periodic_update()
            except Exception as e:
                print(f"  [TELEGRAM] Periodic update error: {e}")
            _last_tele_update = now_ts
        # --------------------------------


        # Fabio full analysis (passed prefilter + light pass)
        if not quiet:
            category_color = candidate.setup_category.upper()
            print(f"\n  [CANDIDATE] {bar_ts} | {category_color} | wall={candidate.wall_level:.2f} ({candidate.wall_side}) "
                  f"| near={candidate.proximity_to} @ {candidate.proximity_level:.2f}")

        # OPT: extract M1 context for Fabio V3 Unified
        m1_bars = get_m1_context(bars_1min_ny, candidate.bar)

        # INTELLIGENT COOLDOWN (2-Loss Rule)
        current_narrative = market_narrative
        if len(recent_losses) >= 2:
            loss1 = recent_losses[-2]
            loss2 = recent_losses[-1]
            
            # If the last two losses were in the same direction and happened within 20 minutes of each other
            if loss1['direction'] == loss2['direction'] and (loss2['time'] - loss1['time']).total_seconds() < 20 * 60:
                time_since_last_loss = candidate.bar.timestamp - loss2['time']
                
                # Apply cooldown for 15 minutes after the SECOND loss
                if time_since_last_loss.total_seconds() < 15 * 60:
                    mins_ago = int(time_since_last_loss.total_seconds() // 60)
                    loss_dir = loss2['direction'].upper()
                    cooldown_warning = (
                        f"⚠️ ATTENZIONE: Hai preso 2 STOP LOSS CONSECUTIVI in direzione {loss_dir} (l'ultimo {mins_ago} minuti fa). "
                        f"Il mercato in questa zona è estremamente volatile e ti sta 'mitragliando'. "
                        f"REGOLA TASSATIVA: NON rientrare in direzione {loss_dir} a meno che non ci sia una CONFERMA "
                        f"ISTITUZIONALE MASSSICCIA (es. pattern di absorption su M1 inequivocabile) o un REVERSAL "
                        f"STRUTTURALE GIGANTESCO. Se vedi lo stesso identico setup di prima, era SBAGLIATO, quindi SKIPPA."
                    )
                    current_narrative += f"\n\n[COOLDOWN 2-LOSS] {cooldown_warning}"

        # ── PRE-FILTRO DIREZIONALE DETERMINISTICO (SHORT SAFETY CHECK) ──
        # Identifichiamo se il tempo o la struttura indica uno SHORT e applichiamo i filtri base prima di chiamare l'LLM
        is_deterministic_short = False
        short_reason = ""
        
        price = candidate.bar.close
        ctx = candidate.session_ctx
        
        is_short_structure = False
        # 1. Breakout sotto i minimi (Bearish Imbalance)
        if candidate.setup_category == 'imbalance_hunting':
            if ctx.ib_complete and price < ctx.ib_low:
                is_short_structure = True
                short_reason = "bearish_ib_breakout"
            elif ctx.vp and price < ctx.vp.va_low:
                is_short_structure = True
                short_reason = "bearish_va_breakout"
                
        # 2. Continuazioni in trend short (sotto POC e VWAP)
        elif candidate.setup_category in ['pullback', 'momentum']:
            poc = ctx.vp.poc if ctx.vp else None
            vwap = candidate.vwap
            if (poc and price < poc) and (vwap and price < vwap):
                is_short_structure = True
                short_reason = "bearish_continuation_below_value"
                
        # 3. Rifiuto di resistenze (Bearish Reversal a VAH / IB High)
        elif candidate.setup_category == 'reversal':
            if candidate.proximity_to in ['overnight_vah', 'prev_vah', 'ib_high']:
                is_short_structure = True
                short_reason = "bearish_reversal_at_resistance"

        # Se è strutturalmente SHORT, verifichiamo i requisiti di base per procedere con l'LLM
        if is_short_structure:
            is_bearish_day = ctx.day_type in ['trend_down', 'transition_state']
            is_inside_ib = ctx.ib_low <= price <= ctx.ib_high if (ctx.ib_high and ctx.ib_low) else False
            
            # Se non rispetta le regole base (giorno non bearish o fuori dall'IB), lo filtriamo deterministicamente
            if not is_bearish_day:
                is_deterministic_short = True
                short_reason += " (not_bearish_day_type)"
            elif not is_inside_ib:
                is_deterministic_short = True
                short_reason += " (chasing_breakout_below_ibl)"

        # Se il trade è classificato come SHORT e non supera il pre-filtro di sicurezza, lo scartiamo subito risparmiando l'LLM
        if False:  # disabled: always run LLM analysis for short candidates
            import pytz as _pytz
            _ET = _pytz.timezone('America/New_York')
            bar_et = candidate.bar.timestamp.astimezone(_ET).strftime('%H:%M')
            if not quiet:
                print(f"\n  [DECISION] NO_TRADE - deterministic_short_filter ({short_reason}) - API CALL SALVATA")
            log_entry = {
                'date': date_str,
                'bar_time_utc': candidate.bar.timestamp.isoformat(),
                'bar_time_et': bar_et,
                'bar_open': candidate.bar.open,
                'bar_high': candidate.bar.high,
                'bar_low': candidate.bar.low,
                'bar_close': candidate.bar.close,
                'bar_volume': candidate.bar.volume,
                'bar_delta': candidate.bar.delta,
                'wall_level': candidate.wall_level,
                'wall_side': candidate.wall_side,
                'wall_max_size': candidate.wall_max_size,
                'wall_trade_count': candidate.wall_trade_count,
                'proximity_to': candidate.proximity_to,
                'proximity_level': candidate.proximity_level,
                'ib_high': ctx.ib_high,
                'ib_low': ctx.ib_low,
                'ib_range': ctx.ib_range,
                'poc': ctx.vp.poc if ctx.vp else None,
                'va_high': ctx.vp.va_high if ctx.vp else None,
                'va_low': ctx.vp.va_low if ctx.vp else None,
                'day_type': ctx.day_type,
                'market_state': getattr(candidate, 'market_state', 'balance'),
                'market_structure': ctx.market_structure_state,
                'delta_divergence': getattr(candidate, 'delta_divergence', False),
                'effort_no_result': getattr(candidate, 'effort_no_result', False),
                'top_wick_ratio': getattr(candidate, 'top_wick_ratio', 0.0),
                'bottom_wick_ratio': getattr(candidate, 'bottom_wick_ratio', 0.0),
                'close_percentile': getattr(candidate, 'close_percentile', 0.5),
                'prev_day_poc': ctx.prev_day_vp.poc if ctx.prev_day_vp else None,
                'prev_day_vah': ctx.prev_day_vp.va_high if ctx.prev_day_vp else None,
                'prev_day_val': ctx.prev_day_vp.va_low if ctx.prev_day_vp else None,
                'session_bias': candidate.session_bias,
                'fabio_direction': 'short',
                'fabio_imbalance_phase': 'none',
                'fabio_confidence': 0,
                'fabio_setup': candidate.setup_category,
                'fabio_entry': None,
                'fabio_stop': None,
                'fabio_target': None,
                'fabio_reasoning': 'Bypassato tramite pre-filtro deterministico LONG ONLY per salvare costi API.',
                'market_narrative': market_narrative,
                'session_memory': get_session_memory_up_to(ctx, candidate.bar.timestamp),
                'decision': 'no_trade',
                'no_trade_reason': f'short_trades_disabled ({short_reason})',
            }
            log_reasoning(log_entry)
            continue
        # ──────────────────────────────────────────────────────────────────

        if not quiet:
            print(f"  [FABIO V3] predatory analysis...", end=' ', flush=True)

        # ── PRE-LLM IGNITION VETO (pure Python, saves API tokens) ───────────
        # RULE: Only enter at the ignition bar OR within 20 bars of it.
        # Block: mid-accumulation, mid/late expansion (chasing), no signal.
        # Modified: We no longer skip candidate evaluation to allow continuous market narrative updates.
        _ign = detect_accumulation_breakout(m1_bars, candidate.bar, session_ctx=ctx)
        _is_ignition       = _ign.get('is_ignition', False)
        _bars_since        = _ign.get('bars_since_ignition', -1)
        _in_early_exp      = 0 <= _bars_since <= 20
        _ign_label         = _ign.get('label', '')
        _ib_complete       = getattr(ctx, 'ib_complete', False)
        # ─────────────────────────────────────────────────────────────────────

        # Get today's trades only for the count and cooldown analysis
        _today_closed = [t for t in closed_trades if t.entry_time.date() == candidate.bar.timestamp.date()]
        _time_since_last_close = -1.0
        _last_trade_pnl = 0.0
        if _today_closed:
            _last_trade = _today_closed[-1]
            _last_trade_pnl = _last_trade.pnl_usd
            _time_since_last_close = (candidate.bar.timestamp - _last_trade.exit_time).total_seconds() / 60.0

        _sess_state = load_session()
        fabio_signal = fabio_analyze(
            candidate, 
            session_context=session_buffer, 
            m1_bars=m1_bars, 
            market_narrative=current_narrative, 
            bars_since_last=bars_since_last,
            equity=_sess_state.get('equity', 50000.0),
            daily_pnl=_sess_state.get('daily_pnl_usd', 0.0),
            trade_count=len(_today_closed),
            last_trade_pnl=_last_trade_pnl,
            time_since_last_close=_time_since_last_close
        )

        # STOP BUFFER: 0.5 points (2 ticks) — minimal spread protection only.
        # Statistical insight: buffer 0-1pt → WR 41.7% (+$905). Buffer 3-6pt → WR 23.1% (-$309).
        # If the level is going to hold, it holds immediately. Don't give it "room to breathe".
        if fabio_signal.direction in ['long', 'short'] and fabio_signal.stop is not None:
            buffer_points = 0.5
            if fabio_signal.direction == 'long':
                fabio_signal.stop -= buffer_points
            else:
                fabio_signal.stop += buffer_points
        
        # (Removed old hardcoded counter-trend block that relied on candidate.excess_tail)

        # Update Narrative State
        if fabio_signal.market_narrative_update:
            market_narrative = fabio_signal.market_narrative_update
        # Update dynamic day type after processing this bar
        update_day_type(ctx, bars_ny[:bar_idx+1])
        last_eval_idx = bar_idx
        if not quiet:
            print(f"dir={fabio_signal.direction} conf={fabio_signal.confidence} "
                  f"setup={fabio_signal.setup_type}")
            print(f"         entry={fabio_signal.entry} stop={fabio_signal.stop} target={fabio_signal.target}")
            print(f"         reason: {fabio_signal.reasoning}")
        else:
            print(f"  {bar_ts} FABIO {fabio_signal.direction}({fabio_signal.confidence})", end='', flush=True)

        import pytz as _pytz
        _ET = _pytz.timezone('America/New_York')
        bar_et_eval = eval_ts.astimezone(_ET).strftime('%H:%M')

        upcoming_news_val = getattr(candidate, 'upcoming_news', "none")
        news_flag = "none"
        if upcoming_news_val and "No high-impact news" not in upcoming_news_val:
            val_lower = upcoming_news_val.lower()
            if "fomc" in val_lower:
                news_flag = "fomc"
            elif "cpi" in val_lower:
                news_flag = "cpi"
            elif "nfp" in val_lower or "nonfarm" in val_lower:
                news_flag = "nfp"
            elif "election" in val_lower:
                news_flag = "election"
            else:
                news_flag = upcoming_news_val

        log_entry = {
            'date': date_str,
            'bar_time_utc': eval_ts.isoformat(),
            'bar_time_et': bar_et_eval,
            'bar_open': candidate.bar.open,
            'bar_high': candidate.bar.high,
            'bar_low': candidate.bar.low,
            'bar_close': candidate.bar.close,
            'bar_volume': candidate.bar.volume,
            'bar_delta': candidate.bar.delta,
            'wall_level': candidate.wall_level,
            'wall_side': candidate.wall_side,
            'wall_max_size': candidate.wall_max_size,
            'wall_trade_count': candidate.wall_trade_count,
            'proximity_to': candidate.proximity_to,
            'proximity_level': candidate.proximity_level,
            'ib_high': ctx.ib_high,
            'ib_low': ctx.ib_low,
            'ib_range': ctx.ib_range,
            'poc': ctx.vp.poc if ctx.vp else None,
            'va_high': ctx.vp.va_high if ctx.vp else None,
            'va_low': ctx.vp.va_low if ctx.vp else None,
            'day_type': ctx.day_type,
            'market_state': getattr(candidate, 'market_state', 'balance'),
            'market_structure': ctx.market_structure_state,
            'delta_divergence': getattr(candidate, 'delta_divergence', False),
            'effort_no_result': getattr(candidate, 'effort_no_result', False),
            'top_wick_ratio': getattr(candidate, 'top_wick_ratio', 0.0),
            'bottom_wick_ratio': getattr(candidate, 'bottom_wick_ratio', 0.0),
            'close_percentile': getattr(candidate, 'close_percentile', 0.5),
            'prev_day_poc': ctx.prev_day_vp.poc if ctx.prev_day_vp else None,
            'prev_day_vah': ctx.prev_day_vp.va_high if ctx.prev_day_vp else None,
            'prev_day_val': ctx.prev_day_vp.va_low if ctx.prev_day_vp else None,
            'session_bias': candidate.session_bias,
            'fabio_direction': fabio_signal.direction,
            'fabio_imbalance_phase': getattr(fabio_signal, 'imbalance_phase', 'none'),
            'fabio_confidence': fabio_signal.confidence,
            'fabio_setup': fabio_signal.setup_type,
            'fabio_entry': fabio_signal.entry,
            'fabio_stop': fabio_signal.stop,
            'fabio_target': fabio_signal.target,
            'fabio_reasoning': fabio_signal.reasoning,
            'market_narrative': market_narrative,
            'session_memory': get_session_memory_up_to(ctx, candidate.bar.timestamp),
            'andrea_confirmation': None,
            'andrea_confidence': None,
            'andrea_setup': None,
            'andrea_reasoning': None,
            'final_confidence': None,
            'decision': None,
            'no_trade_reason': None,
            'trade_direction': None,
            'trade_entry': None,
            'trade_stop': None,
            'trade_target': None,
            'trade_pnl_usd': None,
            'trade_pnl_ticks': None,
            'trade_exit_reason': None,
            # new fields
            'news_flag': news_flag,
            'amt_day_profile': get_amt_structural_profile(ctx),
            'macro_regime': analyze_macro_regime(ctx, candidate.recent_bars),
            'trapped_info': analyze_trapped_participants(candidate.bar),
            'trapped_follow_through': analyze_trap_follow_through(m1_bars),
            'ib_breakouts_count': getattr(ctx, 'ib_breakouts_count', 0),
            'ib_first_breakout_dir': getattr(ctx, 'ib_first_breakout_dir', 'none'),
        }

        # ── Ignition / Accumulation detection (pure Python, no LLM) ──────────
        ignition = detect_accumulation_breakout(m1_bars, candidate.bar, session_ctx=ctx)
        log_entry['ignition_label']        = ignition.get('label', '')
        log_entry['ignition_is_ignition']  = ignition.get('is_ignition', False)
        log_entry['ignition_direction']    = ignition.get('ignition_direction', 'none')
        log_entry['ignition_bars_since']   = ignition.get('bars_since_ignition', -1)
        log_entry['ignition_in_acc']       = ignition.get('in_accumulation', False)
        log_entry['ignition_acc_high']     = ignition.get('accumulation_high', 0.0)
        log_entry['ignition_acc_low']      = ignition.get('accumulation_low', 0.0)
        log_entry['ignition_acc_mins']     = ignition.get('accumulation_mins', 0)

        _append_session(session_buffer, bar_ts, fabio_signal)

        # Threshold always fixed at FABIO_MIN_CONFIDENCE (no post-stop penalty)
        required_confidence = FABIO_MIN_CONFIDENCE


        # POST-ANALYSIS SHORT SAFETY VETO
        if False:  # disabled: allow LLM consensus to decide shorts
            ctx = candidate.session_ctx

            # Filter 1: Macro day type — shorts only on trend_down or transition_state
            is_bearish_day = ctx.day_type in ['trend_down', 'transition_state']

            # Filter 3: Squeeze setups are forbidden for short (squeeze-and-trap risk)
            is_not_squeeze = fabio_signal.setup_type != 'squeeze'

            if not is_bearish_day:
                reason = f'short_veto (not_bearish_day: day_type={ctx.day_type})'
            elif not is_not_squeeze:
                reason = 'short_veto (squeeze_setup_forbidden)'
            else:
                reason = None  # SHORT APPROVATO ✅
        elif fabio_signal.confidence < required_confidence or fabio_signal.direction == 'none':
            if fabio_signal.confidence < required_confidence:
                reason = f'fabio_confidence={fabio_signal.confidence} < {required_confidence}'
            else:
                reason = 'fabio_direction_none'
        else:
            reason = None
            
        if reason is not None:
            if not quiet:
                print(f"  [DECISION] NO_TRADE - {reason}")
            else:
                print(f" -> SKIP")
            log_entry['decision'] = 'no_trade'
            log_entry['no_trade_reason'] = reason
            log_reasoning(log_entry)
            continue

        # (Min stop 15pt veto removed in favor of structural wall invalidation)

        # After Fabio analysis, handle Fabio-only mode
        andrea_signal = None
        if fabio_only:
            # Skip Andrea confirmation, assume trade proceeds
            # Build a simple consensus with required sub-objects
            class _SimpleSubObj:
                pass
            class _SimpleConsensus:
                def __init__(self):
                    # decision and direction
                    self.decision = 'trade'
                    self.direction = fabio_signal.direction
                    self.entry = fabio_signal.entry
                    self.stop = fabio_signal.stop
                    self.target = fabio_signal.target
                    # Calculate r_ratio
                    risk = abs(self.entry - self.stop) if (self.entry and self.stop) else 0.0
                    if self.direction == 'long':
                        reward = (self.target - self.entry) if (self.target and self.entry) else 0.0
                    else:
                        reward = (self.entry - self.target) if (self.target and self.entry) else 0.0
                    self.r_ratio = round(reward / risk, 2) if (risk > 0 and reward > 0) else 0.0
                    # fabio sub-object
                    self.fabio = _SimpleSubObj()
                    self.fabio.setup_type = getattr(fabio_signal, 'setup_type', None)
                    self.fabio.reasoning = getattr(fabio_signal, 'reasoning', '')
                    self.fabio.confidence = getattr(fabio_signal, 'confidence', None)
                    # andrea sub-object
                    self.andrea = _SimpleSubObj()
                    self.andrea.structural_stop = None
                    self.andrea.reasoning = 'fabio_only_skip_andrea'
                    self.final_confidence = getattr(fabio_signal, 'confidence', None)
                    self.context_fingerprint = getattr(candidate, 'context_fingerprint', '')
                    
                    # Set news_flag
                    self.news_flag = "none"
                    upcoming = getattr(candidate, 'upcoming_news', None)
                    if upcoming and "No high-impact news" not in upcoming:
                        val_lower = upcoming.lower()
                        if "fomc" in val_lower:
                            self.news_flag = "fomc"
                        elif "cpi" in val_lower:
                            self.news_flag = "cpi"
                        elif "nfp" in val_lower or "nonfarm" in val_lower:
                            self.news_flag = "nfp"
                        elif "election" in val_lower:
                            self.news_flag = "election"
                        else:
                            self.news_flag = upcoming
                
            consensus = _SimpleConsensus()
        else:
            # ── CONSENSUS VALIDATION (Fabio -> Andrea) ──────────────────
            print(f"  [CONSENSUS] Requesting confirmation from Andrea...")
            andrea_signal = andrea_confirm(candidate, fabio_signal, m1_bars=m1_bars)
            
            # Build consensus object
            consensus = build_consensus(fabio_signal, andrea_signal, candidate=candidate)
            consensus.context_fingerprint = getattr(candidate, 'context_fingerprint', '')

        if consensus.decision != 'trade':
            vetoer = 'Andrea' if 'andrea' in consensus.no_trade_reason else 'Fabio/System'
            print(f" -> REJECTED by {vetoer}: {consensus.no_trade_reason}")
            log_entry['decision'] = 'no_trade'
            if andrea_signal is not None:
                log_entry['andrea_confirmation'] = andrea_signal.confirmation
                log_entry['andrea_confidence'] = andrea_signal.confidence
                log_entry['andrea_setup'] = andrea_signal.setup_type
                log_entry['andrea_reasoning'] = andrea_signal.reasoning
            else:
                log_entry['andrea_confirmation'] = True
                log_entry['andrea_reasoning'] = 'fabio_only_skip_andrea'
            log_entry['no_trade_reason'] = consensus.no_trade_reason
            log_reasoning(log_entry)
            continue

        # Populate consensus details in log_entry
        log_entry['decision'] = 'trade'
        log_entry['final_confidence'] = consensus.final_confidence
        if not fabio_only:
            log_entry['andrea_confirmation'] = andrea_signal.confirmation
            log_entry['andrea_confidence'] = andrea_signal.confidence
            log_entry['andrea_setup'] = andrea_signal.setup_type
            log_entry['andrea_reasoning'] = andrea_signal.reasoning
        else:
            log_entry['andrea_confirmation'] = True
            log_entry['andrea_reasoning'] = 'fabio_only_skip_andrea'

        # ── PRECISION ENTRY (M1 Refinement) ─────────────────────────
        # Bypassed: We trust Fabio's structural levels. Precision module was overriding them with worse M1 extremes.
        print(f"  [PRECISION] Bypassed. Using Fabio's original structural levels.")
        precision = {'entry_reasoning': 'Bypassed'}
        
        # Keep consensus levels as defined by Fabio/Andrea
        # Do not force consensus.entry = candidate.bar.close; respect the LLM's limit/pullback entry!
        consensus.entry = consensus.entry
        consensus.stop  = consensus.stop
        consensus.target = consensus.target
        
        # ── SAFETY: Enforce 15-point (60-tick) minimum stop floor ──
        if consensus.entry is not None and consensus.stop is not None:
            stop_dist = abs(consensus.entry - consensus.stop)
            if stop_dist < 15.0:
                if consensus.direction == 'short':
                    consensus.stop = consensus.entry + 15.0
                elif consensus.direction == 'long':
                    consensus.stop = consensus.entry - 15.0
                print(f"  [SAFETY] Enforced 15-point minimum stop floor. Adjusted stop to: {consensus.stop}")

        # VALIDATION: Reject backward stops (LLM Hallucinations) (Adjust instead of reject)
        if consensus.direction == 'long' and consensus.entry is not None and consensus.stop is not None and consensus.stop >= consensus.entry:
            _new_stop = consensus.entry - 15.0
            print(f"  [ADJUST] Backward stop detected for LONG. Adjusting stop to entry - 15.0 -> {_new_stop}")
            consensus.stop = _new_stop
        if consensus.direction == 'short' and consensus.entry is not None and consensus.stop is not None and consensus.stop <= consensus.entry:
            _new_stop = consensus.entry + 15.0
            print(f"  [ADJUST] Backward stop detected for SHORT. Adjusting stop to entry + 15.0 -> {_new_stop}")
            consensus.stop = _new_stop

        # VALIDATION: Reject backward targets (LLM Hallucinations) (Adjust instead of reject)
        if consensus.direction == 'long' and consensus.entry is not None and consensus.target is not None and consensus.target <= consensus.entry:
            _new_target = consensus.entry + 20.0
            print(f"  [ADJUST] Backward target detected for LONG. Adjusting target to entry + 20.0 -> {_new_target}")
            consensus.target = _new_target
        if consensus.direction == 'short' and consensus.entry is not None and consensus.target is not None and consensus.target >= consensus.entry:
            _new_target = consensus.entry - 20.0
            print(f"  [ADJUST] Backward target detected for SHORT. Adjusting target to entry - 20.0 -> {_new_target}")
            consensus.target = _new_target



        # ── INVALIDATION WALL STOP LOGIC ─────────────────────────────
        active_wall = None
        _is_imbalance_setup = candidate.setup_category == 'imbalance_hunting' or 'imbalance' in str(consensus.fabio.setup_type).lower()

        if _is_imbalance_setup and candidate.wall_level > 0:
            active_wall = candidate.wall_level
            print(f"  [INVALIDATION] Imbalance setup detected. Using M1 wall directly: {active_wall}")
        else:
            # Find the largest Big Trade in the last 6 M5 bars (30-min context) on the correct side of the entry
            largest_bt_price = None
            largest_bt_size = -1
            
            # Scan candidate.recent_bars (if populated) or default to [candidate.bar]
            bars_to_scan = candidate.recent_bars if candidate.recent_bars else [candidate.bar]
            for b in bars_to_scan:
                for bt in getattr(b, 'big_trades', []):
                    # Check side and price relationship
                    if consensus.direction == 'long':
                        if bt.price < consensus.entry:
                            if bt.size > largest_bt_size:
                                largest_bt_size = bt.size
                                largest_bt_price = bt.price
                    elif consensus.direction == 'short':
                        if bt.price > consensus.entry:
                            if bt.size > largest_bt_size:
                                largest_bt_size = bt.size
                                largest_bt_price = bt.price
                                
            if largest_bt_price is not None:
                active_wall = largest_bt_price
                print(f"  [INVALIDATION] Sourced active wall from largest Big Trade in last 6 bars: {active_wall} (size={largest_bt_size})")
            else:
                active_wall = candidate.proximity_level
                print(f"  [INVALIDATION] No Big Trade on correct side. Sourced active wall from candidate proximity level: {active_wall}")

        if active_wall is not None and active_wall > 0 and consensus.entry is not None and consensus.stop is not None:
            # Verify the wall is on the correct side (safeguard)
            is_valid_wall = False
            if consensus.direction == 'long' and active_wall <= consensus.entry:
                is_valid_wall = True
            elif consensus.direction == 'short' and active_wall >= consensus.entry:
                is_valid_wall = True
                
            if is_valid_wall:
                wall_distance = abs(consensus.entry - active_wall)
                # COMMENTED OUT PER USER REQUEST: Avoid hardcoded numeric if-veto for wall distance.
                # The stop_distance > 50.0 cap filter below still protects against excessively wide stops.
                # if wall_distance > 30.0:
                #     print(f"  [VETO] Protective wall is too far ({wall_distance:.1f}pt > 30pt max risk). Vetoing to avoid unprotected stop.")
                #     log_entry['decision'] = 'no_trade'
                #     log_entry['no_trade_reason'] = f'wall_too_far_unprotected_stop ({wall_distance:.1f}pt > 30pt)'
                #     log_reasoning(log_entry)
                #     continue
                
                # Enforce stop behind wall with buffer (2.5pt for imbalance, 1.0pt for structural), but reject the trade if the stop distance would exceed 45.0 points.
                buffer_pt = 2.5 if _is_imbalance_setup else 1.0
                max_stop_distance = 45.0 # Max 180 ticks risk (contracts scale down dynamically to keep $50 risk constant)
                
                if consensus.direction == 'long' and (_is_imbalance_setup or consensus.stop >= active_wall):
                    _new_stop = active_wall - buffer_pt
                    _dist = abs(consensus.entry - _new_stop)
                    if _dist < 15.0:
                        _new_stop = consensus.entry - 15.0
                        _dist = 15.0
                    if _dist <= max_stop_distance:
                        print(f"  [ADJUST] Stop {consensus.stop} moved behind wall {active_wall} -> {_new_stop} (risk: {_dist:.2f} pts, buffer: {buffer_pt})")
                        consensus.stop = _new_stop
                    else:
                        print(f"  [VETO] Wall is too far ({_dist:.2f} pts > {max_stop_distance} pts). Vetoing trade to avoid unprotected/excessive risk.")
                        log_entry['decision'] = 'no_trade'
                        log_entry['no_trade_reason'] = f'wall_too_far_excessive_risk ({_dist:.2f} pts)'
                        log_reasoning(log_entry)
                        continue
                elif consensus.direction == 'short' and (_is_imbalance_setup or consensus.stop <= active_wall):
                    _new_stop = active_wall + buffer_pt
                    _dist = abs(consensus.entry - _new_stop)
                    if _dist < 15.0:
                        _new_stop = consensus.entry + 15.0
                        _dist = 15.0
                    if _dist <= max_stop_distance:
                        print(f"  [ADJUST] Stop {consensus.stop} moved behind wall {active_wall} -> {_new_stop} (risk: {_dist:.2f} pts, buffer: {buffer_pt})")
                        consensus.stop = _new_stop
                    else:
                        print(f"  [VETO] Wall is too far ({_dist:.2f} pts > {max_stop_distance} pts). Vetoing trade to avoid unprotected/excessive risk.")
                        log_entry['decision'] = 'no_trade'
                        log_entry['no_trade_reason'] = f'wall_too_far_excessive_risk ({_dist:.2f} pts)'
                        log_reasoning(log_entry)
                        continue


        # ── OPTIMIZATION: Stop Loss Cap Filter (50 points) ──
        stop_distance = abs(consensus.entry - consensus.stop) if (consensus.entry and consensus.stop) else 0.0
        if stop_distance > 50.0:
            if consensus.direction == 'long':
                _capped_stop = consensus.entry - 50.0
            else:
                _capped_stop = consensus.entry + 50.0
            print(f"  [ADJUST] Stop distance ({stop_distance:.2f} pts) exceeds cap of 50 points. Capping stop at 50 points -> {_capped_stop}")
            consensus.stop = _capped_stop


        # Load dynamic parameters from strategy config
        from src.signal_context import get_strategy_config
        try:
            strat_config = get_strategy_config()
        except Exception:
            strat_config = {}

        # ── TARGET OVERRIDE / SELECTION ─────────────────────────────
        target_mode = strat_config.get("target_mode", "fixed_rr") # choices: "fixed_rr", "structural"
        risk_points = abs(consensus.entry - consensus.stop)
        
        if target_mode == "fixed_rr":
            if consensus.direction == 'long':
                consensus.target = consensus.entry + (risk_points * 2.0)
            else:
                consensus.target = consensus.entry - (risk_points * 2.0)
            consensus.r_ratio = 2.0
            print(f"  [FIXED RR] Target overridden to {consensus.target} to enforce 2.0 R:R.")
        else:
            # "structural" target mode: keep the original consensus target and recalculate r_ratio
            if risk_points > 0 and consensus.target is not None:
                if consensus.direction == 'long':
                    reward_points = consensus.target - consensus.entry
                else:
                    reward_points = consensus.entry - consensus.target
                consensus.r_ratio = round(reward_points / risk_points, 2)
            else:
                consensus.r_ratio = 2.0
            print(f"  [STRUCTURAL RR] Keeping structural target {consensus.target} (R:R = {consensus.r_ratio}).")

            # Enforce Minimax R:R constraint (minimum 1.8 R:R to avoid overtrading/chasing)
            MIN_ACCEPTABLE_RR = 1.8
            if consensus.r_ratio < MIN_ACCEPTABLE_RR and risk_points > 0:
                print(f"  [TARGET OPTIMIZATION] Structural R:R ({consensus.r_ratio}) is too tight (< {MIN_ACCEPTABLE_RR}). Finding next valid structural level...")
                
                # Gather all structural reference levels in the session context
                struct_levels = []
                ctx = candidate.session_ctx
                
                # Current session VP levels
                if ctx.vp:
                    if ctx.vp.poc: struct_levels.append(ctx.vp.poc)
                    if ctx.vp.va_high: struct_levels.append(ctx.vp.va_high)
                    if ctx.vp.va_low: struct_levels.append(ctx.vp.va_low)
                    if ctx.vp.hvn_levels: struct_levels.extend(ctx.vp.hvn_levels)
                    if ctx.vp.lvn_levels: struct_levels.extend(ctx.vp.lvn_levels)
                
                # Yesterday's session VP levels (if available)
                if ctx.prev_day_vp:
                    if ctx.prev_day_vp.poc: struct_levels.append(ctx.prev_day_vp.poc)
                    if ctx.prev_day_vp.va_high: struct_levels.append(ctx.prev_day_vp.va_high)
                    if ctx.prev_day_vp.va_low: struct_levels.append(ctx.prev_day_vp.va_low)
                    if ctx.prev_day_vp.hvn_levels: struct_levels.extend(ctx.prev_day_vp.hvn_levels)
                    if ctx.prev_day_vp.lvn_levels: struct_levels.extend(ctx.prev_day_vp.lvn_levels)
                
                # IB levels
                if ctx.ib_high: struct_levels.append(ctx.ib_high)
                if ctx.ib_low: struct_levels.append(ctx.ib_low)
                
                # Deduplicate and sort
                struct_levels = sorted(list(set([float(l) for l in struct_levels if l is not None and l > 0])))
                
                new_target = None
                min_rr_dist = MIN_ACCEPTABLE_RR * risk_points
                
                if consensus.direction == 'long':
                    # We want a level >= entry + min_rr_dist
                    target_floor = consensus.entry + min_rr_dist
                    valid_levels = [l for l in struct_levels if l >= target_floor]
                    if valid_levels:
                        new_target = min(valid_levels)
                        print(f"    Found structural level for LONG target: {new_target:.2f} (R:R = {abs(new_target - consensus.entry)/risk_points:.2f})")
                    else:
                        print(f"    No further structural level found for LONG to satisfy {MIN_ACCEPTABLE_RR} R:R.")
                elif consensus.direction == 'short':
                    # We want a level <= entry - min_rr_dist
                    target_cap = consensus.entry - min_rr_dist
                    valid_levels = [l for l in struct_levels if l <= target_cap]
                    if valid_levels:
                        new_target = max(valid_levels)
                        print(f"    Found structural level for SHORT target: {new_target:.2f} (R:R = {abs(new_target - consensus.entry)/risk_points:.2f})")
                    else:
                        print(f"    No further structural level found for SHORT to satisfy {MIN_ACCEPTABLE_RR} R:R.")

                if new_target is not None:
                    consensus.target = new_target
                    consensus.r_ratio = round(abs(consensus.target - consensus.entry) / risk_points, 2)
                    print(f"  [TARGET ADJUSTED] Target updated to {consensus.target:.2f} to achieve a better R:R of {consensus.r_ratio}")
                else:
                    if consensus.direction == 'long':
                        consensus.target = consensus.entry + (risk_points * MIN_ACCEPTABLE_RR)
                    else:
                        consensus.target = consensus.entry - (risk_points * MIN_ACCEPTABLE_RR)
                    consensus.r_ratio = MIN_ACCEPTABLE_RR
                    print(f"  [TARGET FALLBACK] No structural level found. Enforcing fixed R:R of {MIN_ACCEPTABLE_RR} -> Target: {consensus.target:.2f}")
                
            # Final R:R Veto check
            if consensus.r_ratio < MIN_ACCEPTABLE_RR:
                print(f"  [VETO] Target R:R ({consensus.r_ratio}) is too tight (< {MIN_ACCEPTABLE_RR}). Vetoing trade to avoid chasing/hyper-extended risk.")
                log_entry['decision'] = 'no_trade'
                log_entry['no_trade_reason'] = f'rr_too_tight_{consensus.r_ratio:.2f}_lt_{MIN_ACCEPTABLE_RR}'
                log_reasoning(log_entry)
                continue

        # ── EXECUTION ───────────────────────────────────────────────
        # Volume gate: LLM has already analyzed this bar (context preserved),
        # but we only OPEN a trade if volume meets the strategy threshold.
        from src.signal_context import get_strategy_config
        try:
            _exec_strat_config = get_strategy_config()
        except Exception:
            _exec_strat_config = {}

        _min_vol = _exec_strat_config.get("min_volume_threshold", 0)
        if _min_vol > 0:
            # For imbalance_hunting (M1 bars), use the parent M5 bar volume
            _exec_vol = candidate.bar.volume
            if candidate.setup_category == 'imbalance_hunting' and candidate.recent_bars:
                _exec_vol = candidate.recent_bars[-1].volume

            if _exec_vol < _min_vol:
                print(f"  [EXEC VETO] Volume {_exec_vol} < threshold {_min_vol}. LLM context updated, trade NOT opened.")
                log_entry['decision'] = 'no_trade'
                log_entry['no_trade_reason'] = f'exec_volume_below_{_min_vol} (vol={_exec_vol})'
                log_reasoning(log_entry)
                continue

        # ENTRY PROXIMITY VETO: If price is sitting exactly on the wall (< 2 pts away)
        # on a non-imbalance setup, we are in the institutional battle zone (WR 28.4%).
        # Statistical insight: entries 2-5pt from wall → WR 42.9%, best P&L generator.
        # Entries 0-2pt → WR 65% only when it's a TIGHT pullback (imbalance setup handles this).
        # For breakout/squeeze setups, exact-wall entries are noise — veto them.
        if candidate.wall_level > 0 and consensus.entry is not None:
            _entry_dist = abs(consensus.entry - candidate.wall_level)
            _is_imbalance_setup = 'imbalance' in str(consensus.fabio.setup_type).lower() or candidate.market_state == 'imbalance'
            if not _is_imbalance_setup and _entry_dist < 2.0:
                print(f"  [PROXIMITY VETO] Entry {consensus.entry:.2f} too close to wall {candidate.wall_level:.2f} ({_entry_dist:.1f}pt < 2pt). Battle zone WR=28.4%.")
                log_entry['decision'] = 'no_trade'
                log_entry['no_trade_reason'] = f'entry_proximity_battle_zone ({_entry_dist:.1f}pt from wall, need >=2pt for non-imbalance)'
                log_reasoning(log_entry)
                continue

        # ── PULLBACK MOMENTUM VETO (Anti-Chasing V-shape Pullback) ──────────────────
        # Veto trend-continuation setups if the entry bar close is too close to its
        # extreme in the opposite direction of the trade (representing adverse momentum
        # without rejection).
        if consensus.direction in ['long', 'short']:
            _is_continuation = str(consensus.fabio.setup_type).lower() in ['momentum_squeeze', 'ivb_model_1_continuation', 'imbalance_hunting', 'continuation', 'squeeze']
            if _is_continuation:
                _close_pct = getattr(candidate, 'close_percentile', 0.5)
                if consensus.direction == 'short' and _close_pct > 0.85:
                    print(f"  [PULLBACK VETO] SHORT rejected: Candle closed too close to high ({_close_pct:.1%} > 85.0%). Adverse pullback momentum.")
                    log_entry['decision'] = 'no_trade'
                    log_entry['no_trade_reason'] = f'pullback_momentum_adverse_close (close_pct={_close_pct:.2f} for SHORT)'
                    log_reasoning(log_entry)
                    continue
                elif consensus.direction == 'long' and _close_pct < 0.15:
                    print(f"  [PULLBACK VETO] LONG rejected: Candle closed too close to low ({_close_pct:.1%} < 15.0%). Adverse pullback momentum.")
                    log_entry['decision'] = 'no_trade'
                    log_entry['no_trade_reason'] = f'pullback_momentum_adverse_close (close_pct={_close_pct:.2f} for LONG)'
                    log_reasoning(log_entry)
                    continue

        if open_t is None and pending_t is None:
            state = load_session()
            
            # Load dynamic parameters from strategy config
            from src.signal_context import get_strategy_config
            try:
                strat_config = get_strategy_config()
            except Exception:
                strat_config = {}
                
            risk_pct = strat_config.get("risk_pct", 0.001)
            
            contracts = calculate_contracts(
                consensus.entry, consensus.stop,
                state['equity'], risk_pct=risk_pct,
                instrument='MNQ',
                setup_category=candidate.setup_category
            )
            
            a_plus_vol_th = strat_config.get("a_plus_volume_threshold", 4500)
            a_plus_mult = strat_config.get("a_plus_size_multiplier", 3)
            
            # Check if this is an A+ setup based on dynamic volume threshold
            is_a_plus = (candidate.bar.volume >= a_plus_vol_th) or (candidate.wall_max_size >= 150)
            if is_a_plus:
                print(f"  [A+ SETUP DETECTED] Volume: {candidate.bar.volume} (th={a_plus_vol_th}) | Big Trade: {candidate.wall_max_size} | Size multipliers are disabled for constant risk.")


            # If the LLM's entry is significantly different from the current close (e.g. > 1 point), place a Limit Order.
            # Otherwise, execute at Market.
            use_limit_order = abs(consensus.entry - candidate.bar.close) > 1.0

            if use_limit_order:
                # Place a pending limit order
                import datetime as _dt
                expires_at = candidate.bar.timestamp + _dt.timedelta(minutes=15) # expires in 15 minutes (3 M5 bars)
                pending_t = PendingTrade(
                    direction=consensus.direction,
                    limit_price=consensus.entry,
                    stop=consensus.stop,
                    target=consensus.target,
                    signal_bar=candidate.bar,
                    consensus=consensus,
                    contracts=contracts,
                    expires_at=expires_at,
                    last_eval_time=candidate.bar.timestamp
                )
                print(f"  [LIMIT ORDER PLACED] dir={consensus.direction} limit={consensus.entry:.2f} "
                      f"stop={consensus.stop:.2f} target={consensus.target:.2f} contracts={contracts} | Expires at: {expires_at.strftime('%H:%M UTC')}")
                
                log_entry['decision'] = 'pending'
                log_entry['no_trade_reason'] = f'limit_order_placed_at_{consensus.entry:.2f}'
                log_reasoning(log_entry)
                sync_session_state(open_t, closed_trades, ctx, pending_t=pending_t)
            else:
                # Execute at Market
                import datetime as _dt
                if candidate.setup_category == 'imbalance_hunting':
                    actual_entry_time = eval_ts + _dt.timedelta(minutes=1)
                else:
                    actual_entry_time = eval_ts + _dt.timedelta(minutes=5)
                    
                # Find the actual bar for entry to get its open price
                entry_bar_actual = next((b for b in m1_bars if b.timestamp == actual_entry_time), candidate.bar)
                
                open_t = open_trade(consensus, entry_bar_actual, contracts=contracts, entry_time=actual_entry_time)
                # Override the entry price to be the exact OPEN of the next candle
                if entry_bar_actual != candidate.bar:
                    open_t.entry = entry_bar_actual.open
                
                open_t.amt_day_profile = log_entry.get('amt_day_profile')
                open_t.macro_regime = log_entry.get('macro_regime')
                open_t.trapped_info = log_entry.get('trapped_info')
                open_t.trapped_follow_through = log_entry.get('trapped_follow_through')
                
                # Check for backward stop, backward target or ruined RR due to slippage (invalidation check before execution)
                is_invalid = False
                if consensus.direction == 'long':
                    if open_t.entry <= open_t.stop:
                        is_invalid = True
                        print(f"  [TRADE CANCELLED] Entry {open_t.entry:.2f} has breached or crossed stop loss {open_t.stop:.2f} before execution.")
                    elif open_t.entry >= open_t.target:
                        is_invalid = True
                        print(f"  [TRADE CANCELLED] Entry {open_t.entry:.2f} has breached or crossed target {open_t.target:.2f} before execution.")
                elif consensus.direction == 'short':
                    if open_t.entry >= open_t.stop:
                        is_invalid = True
                        print(f"  [TRADE CANCELLED] Entry {open_t.entry:.2f} has breached or crossed stop loss {open_t.stop:.2f} before execution.")
                    elif open_t.entry <= open_t.target:
                        is_invalid = True
                        print(f"  [TRADE CANCELLED] Entry {open_t.entry:.2f} has breached or crossed target {open_t.target:.2f} before execution.")
                        
                if not is_invalid:
                    _new_risk = abs(open_t.entry - open_t.stop)
                    _new_reward = abs(open_t.target - open_t.entry)
                    _new_rr = round(_new_reward / _new_risk, 2) if _new_risk > 0 else 0
                    if _new_rr < 1.0:
                        is_invalid = True
                        print(f"  [TRADE CANCELLED] Slippage ruined R:R ({_new_rr} < 1.0). Cancelling trade.")

                if is_invalid:
                    open_t = None
                    consensus.entry = None
                    consensus.stop = None
                    log_entry['decision'] = 'no_trade'
                    log_entry['no_trade_reason'] = 'invalidated_by_slippage_before_execution'
                    log_reasoning(log_entry)
                    continue
                    
                pending_t = None  # Cancel any pending trade to ensure only one active trade at a time
                consensus.entry = open_t.entry 
                consensus.stop = open_t.stop
                print(f"  [TRADE OPEN] dir={consensus.direction} entry={consensus.entry:.2f} "
                      f"stop={consensus.stop:.2f} target={consensus.target:.2f} contracts={contracts} (Market Order)")
                
                log_entry['trade_direction'] = consensus.direction
                log_entry['trade_entry']     = open_t.entry
                log_entry['trade_stop']      = consensus.stop
                log_entry['trade_target']    = consensus.target
                log_entry['contracts']       = contracts
                sync_session_state(open_t, closed_trades, ctx)
        elif open_t is None and pending_t is not None and pending_t.direction == consensus.direction:
            print(f"  [MOMENTUM OVERRIDE] {consensus.direction.upper()} signal repeated while PENDING active. Executing Chaser at market.")
            state = load_session()
            override_contracts = max(1, pending_t.contracts // 2)
            
            # Create a market order mimicking pending_t but at current price and reduced size
            import datetime as _dt
            if candidate.setup_category == 'imbalance_hunting':
                actual_entry_time = candidate.bar.timestamp + _dt.timedelta(minutes=1)
            else:
                actual_entry_time = candidate.bar.timestamp + _dt.timedelta(minutes=5)
            open_t = open_trade(consensus, candidate.bar, contracts=override_contracts, entry_time=actual_entry_time)
            # FORCE the entry to be the current market close (since it is a chaser at market)
            open_t.entry = candidate.bar.close
            # FORCE the stop to be the pending_t structural stop (safeguard)
            open_t.stop = pending_t.stop
            
            open_t.amt_day_profile = log_entry.get('amt_day_profile')
            open_t.macro_regime = log_entry.get('macro_regime')
            open_t.trapped_info = log_entry.get('trapped_info')
            open_t.trapped_follow_through = log_entry.get('trapped_follow_through')
            
            # Check for backward stop (invalidation check before execution)
            is_invalid = False
            if consensus.direction == 'long':
                if open_t.entry <= open_t.stop:
                    is_invalid = True
            elif consensus.direction == 'short':
                if open_t.entry >= open_t.stop:
                    is_invalid = True
                    
            if is_invalid:
                print(f"  [TRADE CANCELLED] (Chaser) Entry {open_t.entry:.2f} has breached or crossed stop loss {open_t.stop:.2f} before execution. Cancelling trade.")
                open_t = None
                pending_t = None
                log_entry['decision'] = 'no_trade'
                log_entry['no_trade_reason'] = 'chaser_entry_breached_stop_before_execution'
                log_reasoning(log_entry)
                continue

            # Cancel the pending trade completely to avoid scale-in / multiple active operations
            pending_t = None
            
            print(f"  [TRADE OPEN] (Chaser Override) dir={consensus.direction} entry={open_t.entry:.2f} "
                  f"stop={open_t.stop:.2f} target={open_t.target:.2f} contracts={override_contracts}")
            
            log_entry['trade_direction'] = consensus.direction
            log_entry['trade_entry']     = open_t.entry
            log_entry['trade_stop']      = open_t.stop
            log_entry['trade_target']    = open_t.target
            log_entry['contracts']       = override_contracts
            sync_session_state(open_t, closed_trades, ctx)
        else:
            if open_t is not None:
                if consensus.direction == open_t.direction:
                    print(f"  [HOLD CONFIRMATION] 👍 Fabio signal confirms holding our active {open_t.direction.upper()} trade.")
                    log_entry['decision'] = 'hold_confirmed'
                else:
                    print(f"  [TRADE IGNORED] Inverse/Opposite signal {consensus.direction.upper()} ignored during active {open_t.direction.upper()} trade.")
                    log_entry['decision'] = 'no_trade'
                    log_entry['no_trade_reason'] = 'inverse_trade_ignored'
            else:
                print(f"  [TRADE SKIPPED] Existing active trade or pending order in progress, new trade ignored.")
                log_entry['decision'] = 'no_trade'
                log_entry['no_trade_reason'] = 'existing_trade_active'
            
        log_reasoning(log_entry)

    # EOD: close any trade still open after all candidates processed
    if open_t is not None and bars_1min_ny:
        eval_t = getattr(open_t, 'last_eval_time', None) or getattr(open_t, 'entry_time', None) or open_t.entry_bar.timestamp
        remaining = [b for b in bars_1min_ny if b.timestamp > eval_t]
        result    = step_trade(open_t, remaining, session_bars=bars_1min_ny) or close_eod(open_t, bars_1min_ny[-1])
        closed_trades.append(result)
        
        # UPDATE EQUITY and sync EOD close
        sync_session_state(None, closed_trades, ctx, equity_change=result.pnl_usd)
        
        # update_pattern_memory(result)
        log_trade_result(result)

    # EOD Post-Mortem Audit Loop
    if not dry_run:
        from src.agents.audit_agent import audit_session
        try:
            pass  # audit_session(date_str)
        except Exception as e:
            print(f"  [AUDIT] EOD Audit failed: {e}")

    # Queue NLM daily question — Claude will answer via MCP after the run
    if candidates and not dry_run:
        day_logs = _read_day_logs(date_str)
        try:
            queue_daily_question(date_str, day_logs, ctx)
        except Exception as e:
            print(f"  [NLM] queue skipped: {e}")

    # Compute RTH volume profile to return as today_vp (so it is carried forward as prev_day_vp tomorrow)
    bars_1min_rth = filter_rth_session(bars_1min_all)
    rth_vp = compute_volume_profile(bars_1min_rth) or vp

    return closed_trades, rth_vp, today_close


def _telegram_periodic_update() -> None:
    """Sends a 5-minute style Telegram update from within the backtest process."""
    import sys, json, datetime, requests, re, os
    from pathlib import Path
    from collections import defaultdict

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id   = os.environ.get('TELEGRAM_CHAT_ID')
    if not bot_token or not chat_id:
        print("  [TELEGRAM] Periodic update skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured in environment.")
        return

    base_dir  = Path(__file__).parent.parent
    trades_log = base_dir / 'agent_memory' / 'trades_log.jsonl'
    marker_file = base_dir / 'agent_memory' / 'run_start_marker.json'

    # Load run start
    run_start = 'N/A'
    run_range_start, run_range_end = None, None
    if marker_file.exists():
        try:
            data = json.loads(marker_file.read_text(encoding='utf-8'))
            run_start = data.get('start_time', 'N/A')
            r = data.get('range', '')
            if '\u2192' in r:
                parts = r.split('\u2192')
                run_range_start, run_range_end = parts[0].strip(), parts[1].strip()
        except: pass

    # Load trades
    trades = []
    if trades_log.exists():
        try:
            with open(trades_log, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    if line.strip():
                        try: trades.append(json.loads(line))
                        except: pass
        except: pass

    if run_range_start and run_range_end:
        trades = [t for t in trades if run_range_start <= t.get('date','') <= run_range_end]

    now = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    if not trades:
        msg = f"<b>\U0001f4ca NQ Backtest — {now}</b>\n<pre>Nessun trade disponibile.</pre>"
    else:
        by_date = defaultdict(list)
        for t in trades:
            by_date[t.get('date','?')].append(t)

        lines = [f"\U0001f550 Aggiornamento: {now}", f"\U0001f680 Avvio run: {run_start}", ""]
        lines.append(f"{'Data':<12} {'T':>3} {'W/L':>6} {'WR%':>6} {'P&L':>9}")
        lines.append("-" * 42)
        total_pnl = 0.0
        for date in sorted(by_date.keys()):
            day = by_date[date]
            wins = sum(1 for t in day if t.get('pnl_usd',0) > 10)
            losses = sum(1 for t in day if t.get('pnl_usd',0) < -10)
            pnl = sum(t.get('pnl_usd',0) for t in day)
            total_pnl += pnl
            wr = (wins / len(day) * 100) if day else 0
            pnl_str = f"+${pnl:.0f}" if pnl >= 0 else f"-${abs(pnl):.0f}"
            lines.append(f"{date:<12} {len(day):>3} {wins}/{losses:>3} {wr:>5.0f}% {pnl_str:>9}")
        lines.append("-" * 42)
        tot_str = f"+${total_pnl:.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):.2f}"
        lines.append(f"{'TOTALE':<12} {'':>3} {'':>6} {'':>6} {tot_str:>9}")
        msg = f"<b>\U0001f4ca NQ Backtest Fabio</b>\n<pre>{''.join(l + chr(10) for l in lines)}</pre>"

    try:
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
        print(f"  [TELEGRAM] Periodic update sent at {now}")
    except Exception as e:
        print(f"  [TELEGRAM] Periodic update failed: {e}")


def _telegram_day_summary(date_str: str, trades: list) -> str:
    """Asks DeepSeek to generate a trading day summary and sends it to Telegram."""
    import os, json, datetime, requests
    from src.agents.llm_client import llm_ask

    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id   = os.environ.get('TELEGRAM_CHAT_ID')
    if not bot_token or not chat_id:
        return

    if not trades:
        # Return early with a simple no-trade message — skip LLM to avoid placeholder templates
        no_trade_msg = (
            f"<b>NQ Backtest (VWAP/NAV) - {date_str}</b>\n"
            f"<i>Aggiornamento ore {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}</i>\n"
            f"<pre>Nessun trade eseguito il {date_str}.\n"
            f"Il sistema non ha identificato setup validi nella sessione odierna.</pre>"
        )
        try:
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": no_trade_msg, "parse_mode": "HTML"},
                timeout=15
            )
        except Exception:
            pass
        return ""


    # Build trades summary (only reached when trades is not empty)
    total_pnl = sum(t.pnl_usd for t in trades)
    wins    = sum(1 for t in trades if t.pnl_usd > 10)
    losses  = sum(1 for t in trades if t.pnl_usd < -10)
    scratch = len(trades) - wins - losses
    trade_lines = []
    for t in trades:
        outcome = 'WIN' if t.pnl_usd > 10 else ('LOSS' if t.pnl_usd < -10 else 'SCRATCH')
        entry_time = getattr(t, 'entry_time', '') or ''
        if len(str(entry_time)) >= 16:
            entry_time = str(entry_time)[11:16]
        trade_lines.append(
            f"- {entry_time} ET | {t.direction.upper()} | entry={t.entry} stop={t.stop} target={t.target} "
            f"exit={t.exit_price} ({t.exit_reason}) | P&L=${t.pnl_usd:.2f} | conf={getattr(t, 'final_confidence', '?')}% | "
            f"reasoning: {str(getattr(t, 'fabio_reasoning', ''))[:200]}"
        )
    trades_summary = (
        f"Data: {date_str} | Trade: {len(trades)} | W/L/S: {wins}/{losses}/{scratch} | "
        f"P&L Giornaliero: ${total_pnl:.2f}\n\n"
        + "\n".join(trade_lines)
    )

    now = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')

    system_prompt = (
        "Sei un analista di trading quantitativo esperto di NQ (Nasdaq Futures). "
        "Il tuo compito e' analizzare i trade della giornata e produrre un breve report di massimo 200 parole "
        "da inviare via Telegram. Il report deve: "
        "1) Aprire con data, P&L totale e numero di trade, "
        "2) Spiegare sinteticamente cosa ha funzionato e cosa no (pattern ricorrenti nei setup vincenti vs perdenti), "
        "3) Identificare 1-2 lezioni chiave dalla giornata, "
        "4) IMPORTANTE: Identificare i 2-3 livelli di prezzo critici (HVN, zone di assorbimento, cluster di stop) emersi oggi, e scrivere un promemoria per il trader di domani spiegando esattamente *perché* deve attenzionarli. "
        "5) Usare un tono professionale e conciso, senza markdown pesante (solo testo). "
        "NON usare asterischi o simboli speciali. Usa solo testo semplice."
    )
    user_msg = f"Ecco i trade della giornata:\n{trades_summary}"

    try:
        analysis = llm_ask(system_prompt, user_msg, use_cache=False)
    except Exception as e:
        analysis = f"(Analisi non disponibile: {e})"

    message = (
        f"<b>NQ Backtest (VWAP/NAV) - {date_str}</b>\n"
        f"<i>Aggiornamento ore {now}</i>\n"
        f"<pre>{analysis}</pre>\n\n"
        f"<b>Dettaglio Trade:</b>\n"
        f"<pre>{trades_summary}</pre>"
    )

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=15)
        if r.status_code == 200:
            print(f"  [TELEGRAM] Giornata {date_str} inviata su Telegram.")
        else:
            print(f"  [TELEGRAM] Errore invio: {r.text[:100]}")
    except Exception as e:
        print(f"  [TELEGRAM] Connessione fallita: {e}")
        
    return analysis


def _read_day_logs(date_str: str) -> list:
    """Read reasoning_log.jsonl entries for a specific date (written this run)."""
    from src.agent_memory import LOG_FILE
    entries = []
    try:
        with open(LOG_FILE, encoding="utf-8-sig") as f:
            for line in f:
                if line.strip():
                    entry = __import__("json").loads(line)
                    if entry.get("date") == date_str:
                        entries.append(entry)
    except (FileNotFoundError, OSError):
        pass
    return entries


def run_backtest(data_dir: str, max_days: int = 0, dry_run: bool = False, quiet: bool = False, start_date: str = None, end_date: str = None, fabio_only: bool = True, start_time: str = None) -> list:
    """Run all days. Returns all ClosedTrades."""
    import re, json, datetime as _dt, os
    
    print(f"  [INIT] Clearing previous active session state...")
    mem_dir = Path('agent_memory')
    if mem_dir.exists():
        state_file = mem_dir / 'session_state.json'
        if state_file.exists():
            try:
                state_file.unlink()
            except Exception as e:
                print(f"    Warning: could not delete session_state.json: {e}")

    print(f"  [INIT] Listing data from: {data_dir}")
    files = list_data_files(data_dir)
    print(f"  [INIT] Total files found in directory: {len(files)}")
    
    if start_date or end_date:
        # Robust regex extraction of YYYYMMDD
        filtered = []
        for f in files:
            name = Path(f).name
            match = re.search(r'(\d{8})', name)
            if not match: continue
            file_date = match.group(1)
            
            keep = True
            if start_date and file_date < start_date:
                keep = False
            if end_date and file_date > end_date:
                keep = False
                
            if keep:
                filtered.append(f)
        files = filtered
        print(f"  [FILTER] Range {start_date} to {end_date}: Kept {len(files)} files.")

    if max_days and max_days > 0:
        files = files[:max_days]
        print(f"  [LIMIT] Applied max_days={max_days}: Processing {len(files)} files.")

    # --- AUTO-WRITE run_start_marker.json based on actual files being processed ---
    try:
        dates_in_run = []
        for f in files:
            m = re.search(r'(\d{8})', Path(f).name)
            if m:
                raw = m.group(1)  # YYYYMMDD
                dates_in_run.append(f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}")
        if dates_in_run:
            dates_in_run.sort()
            range_str = f"{dates_in_run[0]} \u2192 {dates_in_run[-1]}"
        else:
            range_str = "unknown"
        marker_path = Path(__file__).parent.parent / 'agent_memory' / 'run_start_marker.json'
        marker_data = {
            'start_time': _dt.datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'range': range_str
        }
        marker_path.write_text(json.dumps(marker_data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"  [MARKER] run_start_marker.json aggiornato: {range_str}")
    except Exception as _e:
        print(f"  [MARKER] Errore scrittura marker: {_e}")

    # --- SELECTIVE LOG CLEARING: Remove only the days we are about to run ---
    if files:
        dates_to_run = set()
        for f in files:
            m = re.search(r'(\d{8})', Path(f).name)
            if m:
                raw = m.group(1)
                dates_to_run.add(f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}")
        
        if dates_to_run and mem_dir.exists():
            # Filter trades_log.jsonl
            trades_file = mem_dir / 'trades_log.jsonl'
            if trades_file.exists():
                try:
                    lines_to_keep = []
                    with open(trades_file, 'r', encoding='utf-8') as f_in:
                        for line in f_in:
                            if line.strip():
                                data = json.loads(line)
                                if data.get('date') not in dates_to_run:
                                    lines_to_keep.append(line)
                    with open(trades_file, 'w', encoding='utf-8') as f_out:
                        f_out.writelines(lines_to_keep)
                    print(f"  [INIT] Preserved existing trades, selectively cleared entries for dates: {sorted(list(dates_to_run))}")
                except Exception as e:
                    print(f"    Warning: could not filter trades_log.jsonl: {e}")
                    
            # Filter reasoning_log.jsonl
            reasoning_file = mem_dir / 'reasoning_log.jsonl'
            if reasoning_file.exists():
                try:
                    lines_to_keep = []
                    with open(reasoning_file, 'r', encoding='utf-8') as f_in:
                        for line in f_in:
                            if line.strip():
                                data = json.loads(line)
                                if data.get('date') not in dates_to_run:
                                    lines_to_keep.append(line)
                    with open(reasoning_file, 'w', encoding='utf-8') as f_out:
                        f_out.writelines(lines_to_keep)
                    print(f"  [INIT] Preserved existing reasonings, selectively cleared entries for dates: {sorted(list(dates_to_run))}")
                except Exception as e:
                    print(f"    Warning: could not filter reasoning_log.jsonl: {e}")

    if not files:
        print("  [WARNING] No files found matching criteria.")
        return []

    all_trades = []
    prev_day_vp = None  # carry forward yesterday's VP
    historical_days = [] # List[DailySummary] sliding window
    
    for f in files:
        abs_p = str(Path(f).absolute())
        print(f"Processing ({abs_p})...")
        day_trades, today_vp, today_close = run_day(f, dry_run=dry_run, quiet=quiet, prev_day_vp=prev_day_vp, fabio_only=fabio_only, historical_days=historical_days, start_time=start_time)
        all_trades.extend(day_trades)
        if today_vp is not None:
            prev_day_vp = today_vp
            from src import DailySummary
            
            # Extract date from filename for the DailySummary
            date_str = "unknown"
            match = re.search(r'(\d{8})', Path(f).name)
            if match:
                date_str = match.group(1)
                
            # Capture Telegram analysis
            telegram_analysis = _telegram_day_summary(date_str, day_trades)
            
            # Extract final market narrative for the day from reasoning_log
            final_narrative = ""
            log_entries = _read_day_logs(date_str)
            for e in reversed(log_entries):
                nar = e.get('fabio_raw', {}).get('market_narrative_update', '')
                if nar:
                    final_narrative = nar
                    break

            summary = DailySummary(
                vp=today_vp, 
                close_price=today_close, 
                date=date_str,
                telegram_analysis=telegram_analysis,
                market_narrative=final_narrative
            )
            historical_days.insert(0, summary) # T-1 at index 0, T-2 at index 1
            if len(historical_days) > 2:
                historical_days = historical_days[:2] # Keep only last 2 days
                
        print(f"  -> {len(day_trades)} trades")

    return all_trades


if __name__ == "__main__":
    import argparse
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument("--start_date", help="YYYYMMDD")
    parser.add_argument("--end_date", help="YYYYMMDD")
    parser.add_argument("--max_days", type=int, default=0)
    parser.add_argument("--force", action="store_true", help="Force re-processing")
    parser.add_argument("--auto", action="store_true", help="Auto-confirm decisions")
    parser.add_argument("--mailbox", action="store_true", help="Use human mailbox")
    parser.add_argument("--fabio_only", action="store_true", help="Run in Fabio-only mode, skipping Andrea confirmation")
    parser.add_argument("--dspy", action="store_true", help="Use compiled DSPy optimized agent for Fabio")
    parser.add_argument("--start_time", help="HH:MM start time in ET")
    args = parser.parse_args()

    # Environment configuration based on flags
    if args.force:
        os.environ['BACKTEST_FORCE'] = 'true'
    if args.mailbox:
        os.environ['LLM_PROVIDER'] = 'human'
    if args.dspy:
        os.environ['FABIO_USE_DSPY'] = 'true'
    
    # Run the backtest
    run_backtest(DATA_DIR, max_days=args.max_days, start_date=args.start_date, end_date=args.end_date, fabio_only=args.fabio_only, start_time=args.start_time)

    # Save cache snapshot upon successful completion
    try:
        from src.agents.llm_client import snapshot_cache
        snapshot_cache()
    except Exception as e:
        print(f"  [CACHE] Failed to auto-snapshot: {e}")
