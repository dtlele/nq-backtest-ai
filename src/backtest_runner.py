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
from pathlib import Path
from src.data_loader import load_day, list_data_files
from src.bar_aggregator import aggregate_to_bars
from src.volume_profile import compute_volume_profile
from src.session_context import filter_ny_window, filter_overnight_window, build_session_context, update_day_type
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
    """Return reason string if candidate should be skipped, None to proceed."""
    ctx = candidate.session_ctx
    bar = candidate.bar

    # Balance day + price inside IB + weak wall (skip only if not a reversal)
    if (ctx.day_type == 'balance'
            and ctx.ib_low <= bar.close <= ctx.ib_high
            and candidate.wall_max_size < 30
            and candidate.setup_category != 'reversal'):
        return 'balance_inside_ib_weak_wall'

    # Not enough institutional signal (allow at least 1 trade of size 30)
    if candidate.wall_trade_count < 1:
        return 'insufficient_institutional_signal'

    return None

def run_day(csv_path: str, dry_run: bool = False, quiet: bool = False, fabio_only: bool = False, prev_day_vp=None) -> tuple:
    """Run backtest for one day. Returns (list[ClosedTrade], today_vp)."""
    date_str = Path(csv_path).name.split('-')[2].split('.')[0]  # e.g. 20250430
    date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    
    # ── BLACKOUT DAY CHECK (Tier 1 News) ──────────────
    is_blackout, reason = news_manager.is_blackout_day(date_str)
    if is_blackout:
        print(f"  [SKIPPED] {date_str} is a Blackout Day due to: {reason}. No trading allowed.")
        return [], prev_day_vp

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
        return [], vp   # Return whatever VP was computed from overnight
        
    ctx = build_session_context(date_str, bars_1min_ny, vp, prev_day_vp=prev_day_vp)

    # Candidate detection and agent reasoning use M5 bars
    bars_ny = filter_ny_window(aggregate_to_bars(trades_raw, freq='5min'))
    if not bars_ny:
        return [], vp
    candidates = detect_candidates(bars_ny, ctx, bars_1min_ny=bars_1min_ny, bars_1min_overnight=bars_1min_overnight)

    # Inject M1 candidates for Imbalance Hunting
    from src.candidate_detector import detect_m1_candidates
    existing_ts = {c.bar.timestamp for c in candidates}
    m1_candidates = []
    
    from src.session_context import is_fabio_active
    for idx, m1_bar in enumerate(bars_1min_ny):
        if not is_fabio_active(m1_bar) or m1_bar.timestamp in existing_ts:
            continue
        # Find recent M5 bars up to this M1 bar
        m5_recent = [b for b in bars_ny if b.timestamp <= m1_bar.timestamp]
        # History of M1 bars up to (but not including) this one, for RVOL
        m1_history = bars_1min_ny[:idx]
        cands = detect_m1_candidates(m1_bar, m5_recent[-10:], ctx, m1_history=m1_history)
        m1_candidates.extend(cands)
        
    candidates.extend(m1_candidates)
    candidates.sort(key=lambda c: c.bar.timestamp)

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
    
    def handle_close(result, session_buffer, daily_stops_count):
        closed_trades.append(result)
        update_pattern_memory(result)
        state = load_session()
        state['equity'] += result.pnl_usd
        save_session(state)
        if not is_trade_already_logged(date_str, result.entry_time.isoformat()):
            log_trade_result(result)
        if result.exit_reason == 'stop' and result.pnl_ticks < 0:
            daily_stops_count += 1
            print(f"  [MONEY MANAGEMENT] Stop loss hit. Daily stops: {daily_stops_count}.")
        elif result.exit_reason == 'stop':
            print(f"  [MONEY MANAGEMENT] Trailing stop hit in profit (+{result.pnl_ticks:.1f} ticks).")
        close_time_str = result.exit_time.strftime('%H:%M UTC')
        session_buffer.append(f"⚠️ [TRADE CLOSED] {close_time_str} {result.direction.upper()} exit={result.exit_reason} pnl={result.pnl_usd:.1f}$")
        if len(session_buffer) > MAX_SESSION_BUFFER:
            session_buffer.pop(0)
        return daily_stops_count

    # Load processed candidates to allow fast-forward
    processed_candidates = get_already_processed_candidates()

    import pytz as _ff_pytz
    _ff_ET = _ff_pytz.timezone('America/New_York')

    for candidate in candidates:
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

        bar_ts = candidate.bar.timestamp.strftime('%H:%M UTC')
        bar_et = candidate.bar.timestamp.astimezone(_ff_ET).strftime('%H:%M')
        
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
                    open_t.last_eval_time = open_t.entry_bar.timestamp
                last_eval_time = open_t.last_eval_time
            if pending_t is not None:
                if getattr(pending_t, 'last_eval_time', None) is None:
                    pending_t.last_eval_time = pending_t.signal_bar.timestamp
                
                if last_eval_time is None or pending_t.last_eval_time < last_eval_time:
                    last_eval_time = pending_t.last_eval_time
                
            m1_intermediate = [b for b in bars_1min_ny if last_eval_time < b.timestamp <= candidate.bar.timestamp]
            
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
                            else:
                                open_t = filled
                                print(f"  [PENDING FILLED] Limit order triggered at {open_t.entry}!")
                            pending_t = None
                
                # 2. Process OPEN trades
                if open_t is not None:
                    # Step mechanically for this single M1 bar
                    result = step_trade(open_t, [m1_bar], first_bar_after_entry=(m1_bar.timestamp == open_t.entry_bar.timestamp))
                    if result:
                        daily_stops_count = handle_close(result, session_buffer, daily_stops_count)
                        open_t = None
                        trade_closed_early = True
                        break
                    
                    # The trade survived! Run Fabio APM on this M1 bar
                    if m1_bar.timestamp > open_t.entry_bar.timestamp:
                        print(f"  [MANAGEMENT] Active {open_t.direction.upper()} trade open at {m1_bar.timestamp.strftime('%H:%M UTC')}. Consulting Fabio APM...")
                        m1_context = get_m1_context(bars_1min_ny, m1_bar)
                        
                        from src import CandidateBar
                        dummy_cand = CandidateBar(bar=m1_bar, session_ctx=ctx, wall_level=open_t.entry, wall_side='none', wall_trade_count=0, wall_max_size=0, proximity_to='none', proximity_level=0, bars_in_session=0, is_second_test=False)
                        
                        apm = manage_active_trade(
                            trade=open_t,
                            candidate=dummy_cand,
                            session_context=session_buffer,
                            m1_bars=m1_context,
                            market_narrative=market_narrative,
                            bars_since_last=[]
                        )
                        open_t.last_eval_time = m1_bar.timestamp
                        
                        decision = apm.get("decision", "hold")
                        reasoning = apm.get("reasoning", "")
                        print(f"  [MANAGEMENT] Fabio APM decision: {decision.upper()} | Reasoning: {reasoning}")
                        
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
                            rev_contracts = calculate_contracts(rev_entry, rev_stop, load_session()['equity'], risk_pct=0.005)
                            if daily_stops_count > 0:
                                rev_contracts = max(1, rev_contracts // 2)
                            
                            open_t = open_trade(rev_consensus, m1_bar, contracts=rev_contracts)
                            open_t.last_eval_time = m1_bar.timestamp
                            print(f"  [REVERSE OPEN] 🔄 Opened reverse {rev_dir.upper()} at {rev_entry} | stop={rev_stop}")
                            session_buffer.append(f"🔄 [REVERSED] {m1_bar.timestamp.strftime('%H:%M UTC')} {rev_dir.upper()} entry={rev_entry}")
                            
                            trade_closed_early = True
                            break
                            
                        elif decision == 'trail':
                            new_stop = apm.get("new_stop")
                            new_target = apm.get("new_target")
                            if new_stop:
                                # ── HARD GUARD: no trailing before 1:1 R:R ──────────────
                                initial_risk = abs(open_t.entry - open_t.stop)
                                if open_t.direction == 'long':
                                    profit_so_far = m1_bar.close - open_t.entry
                                else:
                                    profit_so_far = open_t.entry - m1_bar.close
                                rr_now = profit_so_far / initial_risk if initial_risk > 0 else 0
                                
                                if rr_now < 1.0:
                                    print(f"  [TRAIL BLOCKED] R:R={rr_now:.2f} < 1.0 — giving trade room to breathe. Holding.")
                                    decision = 'hold'
                                else:
                                    is_valid = False
                                    if open_t.direction == 'long' and new_stop > open_t.stop:
                                        is_valid = True
                                    elif open_t.direction == 'short' and new_stop < open_t.stop:
                                        is_valid = True
                                    if is_valid:
                                        print(f"  [TRAILING SL] R:R={rr_now:.2f} OK | Moving stop from {open_t.stop:.2f} -> {new_stop:.2f} | event: {apm.get('structural_event','?')}")
                                        open_t.stop = new_stop
                                        session_buffer.append(f"🛡️ [TRAILED SL] {m1_bar.timestamp.strftime('%H:%M UTC')} stop={new_stop:.2f} rr={rr_now:.2f}")
                            if new_target:
                                open_t.target = new_target
                                
            if trade_closed_early:
                continue
                
            # Skip searching for new trades if we still have an active open position
            if open_t is not None:
                continue

        # ── MONEY MANAGEMENT CHECKS ──────────────────────────────────
        if daily_stops_count >= 3:
            if not quiet:
                print(f"  {bar_ts} [DAILY STOP OUT] 3 stops hit today. Skipping candidate {bar_et} ET.")
            continue

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
                'fabio_direction': 'prefiltered', 'fabio_confidence': 0,
                'fabio_setup': 'none', 'fabio_reasoning': prefilter_reason,
                'decision': 'prefiltered', 'no_trade_reason': prefilter_reason,
            })
            session_buffer.append(f"{bar_ts} prefiltered(0) — {prefilter_reason}")
            continue

        # Extract bars since last evaluation
        bars_since_last = []
        if last_eval_idx < bar_idx:
            bars_since_last = bars_ny[last_eval_idx:bar_idx]

        # ── OPT 3: Two-pass (light → full) ──────────────────────────
        if not dry_run:
            light_conf = fabio_light(candidate, session_context=session_buffer, market_narrative=market_narrative, bars_since_last=bars_since_last)
            if light_conf <= LIGHT_CONFIDENCE_THRESHOLD:
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
                    'fabio_direction': 'light_skip', 'fabio_confidence': light_conf,
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

        # Fabio full analysis (passed prefilter + light pass)
        if not quiet:
            category_color = candidate.setup_category.upper()
            print(f"\n  [CANDIDATE] {bar_ts} | {category_color} | wall={candidate.wall_level:.2f} ({candidate.wall_side}) "
                  f"| near={candidate.proximity_to} @ {candidate.proximity_level:.2f}")

        # OPT: extract M1 context for Fabio V3 Unified
        m1_bars = get_m1_context(bars_1min_ny, candidate.bar)

        if not quiet:
            print(f"  [FABIO V3] predatory analysis...", end=' ', flush=True)
        fabio_signal = fabio_analyze(candidate, session_context=session_buffer, m1_bars=m1_bars, market_narrative=market_narrative, bars_since_last=bars_since_last)
        
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
        bar_et = candidate.bar.timestamp.astimezone(_ET).strftime('%H:%M')
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
            'fabio_direction': fabio_signal.direction,
            'fabio_confidence': fabio_signal.confidence,
            'fabio_setup': fabio_signal.setup_type,
            'fabio_entry': fabio_signal.entry,
            'fabio_stop': fabio_signal.stop,
            'fabio_target': fabio_signal.target,
            'fabio_reasoning': fabio_signal.reasoning,
            'market_narrative': market_narrative,
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
        }

        _append_session(session_buffer, bar_ts, fabio_signal)

        # Dinamicamente richiedi prudenza maggiore (minimo 75% confidenza anziché 65%) dopo uno stop loss nella stessa sessione
        required_confidence = FABIO_MIN_CONFIDENCE + 10 if daily_stops_count > 0 else FABIO_MIN_CONFIDENCE
        if fabio_signal.confidence < required_confidence or fabio_signal.direction == 'none':
            if fabio_signal.confidence < required_confidence:
                caution_suffix = ' (Prudenza post-stop attiva)' if daily_stops_count > 0 else ''
                reason = f'fabio_confidence={fabio_signal.confidence} < {required_confidence}{caution_suffix}'
            else:
                reason = 'fabio_direction_none'
            if not quiet:
                print(f"  [DECISION] NO_TRADE - {reason}")
            else:
                print(f" -> SKIP")
            log_entry['decision'] = 'no_trade'
            log_entry['no_trade_reason'] = reason
            log_reasoning(log_entry)
            continue

        # After Fabio analysis, handle Fabio-only mode
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
                    reward = abs(self.target - self.entry) if (self.target and self.entry) else 0.0
                    self.r_ratio = round(reward / risk, 2) if risk > 0 else 0.0
                    # fabio sub-object
                    self.fabio = _SimpleSubObj()
                    self.fabio.setup_type = getattr(fabio_signal, 'setup_type', None)
                    self.fabio.reasoning = getattr(fabio_signal, 'reasoning', '')
                    self.fabio.confidence = getattr(fabio_signal, 'confidence', None)
                    # andrea sub-object
                    self.andrea = _SimpleSubObj()
                    self.andrea.structural_stop = None
                    self.andrea.reasoning = 'fabio_only_skip_andrea'
                    # final confidence placeholder
                    self.final_confidence = getattr(fabio_signal, 'confidence', None)
                
            consensus = _SimpleConsensus()
        else:
            # ── CONSENSUS VALIDATION (Fabio -> Andrea) ──────────────────
            print(f"  [CONSENSUS] Requesting confirmation from Andrea...")
            andrea_signal = andrea_confirm(candidate, fabio_signal)
            
            # Build consensus object
            consensus = build_consensus(fabio_signal, andrea_signal)


        if consensus.decision != 'trade':
            print(f" -> REJECTED by Andrea: {consensus.no_trade_reason}")
            log_entry['decision'] = 'no_trade'
            log_entry['andrea_confirmation'] = False
            log_entry['andrea_reasoning'] = andrea_signal.reasoning
            log_entry['no_trade_reason'] = andrea_signal.reasoning
            log_reasoning(log_entry)
            continue

        # ── PRECISION ENTRY (M1 Refinement) ─────────────────────────
        # Bypassed: We trust Fabio's structural levels. Precision module was overriding them with worse M1 extremes.
        print(f"  [PRECISION] Bypassed. Using Fabio's original structural levels.")
        precision = {'entry_reasoning': 'Bypassed'}
        
        # Keep consensus levels as defined by Fabio/Andrea
        consensus.entry = consensus.entry
        consensus.stop  = consensus.stop
        consensus.target = consensus.target

        # VALIDATION: Reject backward stops (LLM Hallucinations)
        if consensus.direction == 'long' and consensus.stop >= consensus.entry:
            print(f"  [ERROR] LLM generated backward stop for LONG (Entry: {consensus.entry}, Stop: {consensus.stop}). Rejecting trade.")
            log_entry['decision'] = 'skip'
            log_entry['fabio_reasoning'] += " [REJECTED: Backward Stop]"
            if not is_trade_already_logged(date_str, log_entry['entry_time']):
                log_reasoning(log_entry)
            continue
        if consensus.direction == 'short' and consensus.stop <= consensus.entry:
            print(f"  [ERROR] LLM generated backward stop for SHORT (Entry: {consensus.entry}, Stop: {consensus.stop}). Rejecting trade.")
            log_entry['decision'] = 'skip'
            log_entry['fabio_reasoning'] += " [REJECTED: Backward Stop]"
            if not is_trade_already_logged(date_str, log_entry['entry_time']):
                log_reasoning(log_entry)
            continue

        # Log entry handling – ensure Andrea reasoning exists
        log_entry['decision'] = 'trade'
        if fabio_only:
            # Dummy Andrea signal for logging
            class _DummyAndrea:
                reasoning = 'fabio_only_skip_andrea'
            andrea_signal = _DummyAndrea()
            log_entry['andrea_confirmation'] = True
            log_entry['andrea_reasoning'] = andrea_signal.reasoning
                # ── EXECUTION ───────────────────────────────────────────────
        if open_t is None and pending_t is None:
            state = load_session()
            contracts = calculate_contracts(
                consensus.entry, consensus.stop,
                state['equity'], risk_pct=0.005,
                instrument='MNQ',
                setup_category=candidate.setup_category
            )

            # Dimezza il rischio (contracts) dopo uno stop nella stessa sessione per prudenza
            if daily_stops_count > 0:
                contracts = max(1, contracts // 2)
                print(f"  [MONEY MANAGEMENT] Prudenza attiva: contratti dimezzati a {contracts} (precedente stop nella sessione)")

            # IMPLEMENTATION: Pullback Limit Order for Imbalance
            # We look for the phrase "imbalance" in the setup, or if it's an imbalance session
            is_imbalance = 'imbalance' in str(consensus.fabio.setup_type).lower() or candidate.market_state == 'imbalance'
            
            if is_imbalance and candidate.wall_level > 0:
                from datetime import timedelta
                limit_price = candidate.wall_level
                
                # Sanity check: ensure limit price is actually a pullback (at least 4 points)
                if consensus.direction == 'long' and limit_price >= candidate.bar.close:
                    limit_price = candidate.bar.close - 4.0
                elif consensus.direction == 'short' and limit_price <= candidate.bar.close:
                    limit_price = candidate.bar.close + 4.0

                pending_t = PendingTrade(
                    direction=consensus.direction,
                    limit_price=limit_price,
                    stop=consensus.stop,
                    target=consensus.target,
                    signal_bar=candidate.bar,
                    consensus=consensus,
                    contracts=contracts,
                    expires_at=candidate.bar.timestamp + timedelta(minutes=15)
                )
                print(f"  [PENDING] Limit order placed at {limit_price} (waiting for pullback). Expires at {pending_t.expires_at.strftime('%H:%M UTC')}")
            else:
                open_t        = open_trade(consensus, candidate.bar, contracts=contracts)
                print(f"  [TRADE OPEN] dir={consensus.direction} entry={consensus.entry} "
                      f"stop={consensus.stop} target={consensus.target} contracts={contracts}")

            log_entry['trade_direction'] = consensus.direction
            log_entry['trade_entry']     = consensus.entry if open_t else pending_t.limit_price
            log_entry['trade_stop']      = consensus.stop
            log_entry['trade_target']    = consensus.target
            log_entry['contracts']       = contracts
        elif open_t is None and pending_t is not None and pending_t.direction == consensus.direction:
            print(f"  [MOMENTUM OVERRIDE] {consensus.direction.upper()} signal repeated while PENDING active. Executing Chaser at market.")
            state = load_session()
            override_contracts = max(1, pending_t.contracts // 2)
            
            # Create a market order mimicking pending_t but at current price and reduced size
            open_t = open_trade(consensus, candidate.bar, contracts=override_contracts)
            # FORCE the stop to be the pending_t structural stop (safeguard)
            open_t.stop = pending_t.stop
            
            # Adjust pending_t contracts so the total doesn't exceed original plan if it fills later
            pending_t.contracts = max(1, pending_t.contracts - override_contracts)
            
            print(f"  [TRADE OPEN] (Chaser Override) dir={consensus.direction} entry={candidate.bar.close} "
                  f"stop={open_t.stop} target={open_t.target} contracts={override_contracts}")
            
            log_entry['trade_direction'] = consensus.direction
            log_entry['trade_entry']     = candidate.bar.close
            log_entry['trade_stop']      = open_t.stop
            log_entry['trade_target']    = open_t.target
            log_entry['contracts']       = override_contracts
        else:
            print(f"  [TRADE SKIPPED] Existing trade active (open or pending), new trade ignored.")
            
        log_reasoning(log_entry)

    # EOD: close any trade still open after all candidates processed
    if open_t is not None and bars_ny:
        remaining = [b for b in bars_ny if b.timestamp > open_t.entry_bar.timestamp]
        result    = step_trade(open_t, remaining) or close_eod(open_t, bars_ny[-1])
        closed_trades.append(result)
        
        # UPDATE EQUITY for EOD close
        state = load_session()
        state['equity'] += result.pnl_usd
        save_session(state)
        
        update_pattern_memory(result)
        log_trade_result(result)

    # EOD Post-Mortem Audit Loop
    if not dry_run:
        from src.agents.audit_agent import audit_session
        try:
            audit_session(date_str)
        except Exception as e:
            print(f"  [AUDIT] EOD Audit failed: {e}")

    # Queue NLM daily question — Claude will answer via MCP after the run
    if candidates and not dry_run:
        day_logs = _read_day_logs(date_str)
        try:
            queue_daily_question(date_str, day_logs, ctx)
        except Exception as e:
            print(f"  [NLM] queue skipped: {e}")

    return closed_trades, vp


def _read_day_logs(date_str: str) -> list:
    """Read reasoning_log.jsonl entries for a specific date (written this run)."""
    from src.agent_memory import LOG_FILE
    entries = []
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entry = __import__("json").loads(line)
                    if entry.get("date") == date_str:
                        entries.append(entry)
    except (FileNotFoundError, OSError):
        pass
    return entries


def run_backtest(data_dir: str, max_days: int = 0, dry_run: bool = False, quiet: bool = False, start_date: str = None, end_date: str = None, fabio_only: bool = False) -> list:
    """Run all days. Returns all ClosedTrades."""
    import re
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

    if not files:
        print("  [WARNING] No files found matching criteria.")
        return []

    all_trades = []
    prev_day_vp = None  # carry forward yesterday's VP
    for f in files:
        abs_p = str(Path(f).absolute())
        print(f"Processing ({abs_p})...")
        day_trades, today_vp = run_day(f, dry_run=dry_run, quiet=quiet, prev_day_vp=prev_day_vp, fabio_only=fabio_only)
        all_trades.extend(day_trades)
        if today_vp is not None:
            prev_day_vp = today_vp
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
    args = parser.parse_args()

    # Environment configuration based on flags
    if args.force:
        os.environ['BACKTEST_FORCE'] = 'true'
    if args.mailbox:
        os.environ['LLM_PROVIDER'] = 'human'
    
    # Run the backtest
    run_backtest(DATA_DIR, max_days=args.max_days, start_date=args.start_date, end_date=args.end_date, fabio_only=args.fabio_only)
