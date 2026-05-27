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
from src.session_context import filter_ny_window, filter_overnight_window, build_session_context
from src.candidate_detector import detect_candidates
from src.agents.fabio_agent import analyze as fabio_analyze, light_analyze as fabio_light
from src.agents.andrea_agent import confirm as andrea_confirm
from src.agents.precision_entry import refine_entry, get_m1_context
from src.consensus import build_consensus
from src.trade_simulator import open_trade, step_trade, close_eod
from src.agent_memory import (
    reset_session, log_reasoning, update_pattern_memory, log_trade_result,
    get_already_processed_candidates, is_trade_already_logged,
    load_session, save_session
)
from src.risk_manager import calculate_contracts
from src.agents.nlm_daily import queue_daily_question
from src import (
    FABIO_MIN_CONFIDENCE, LIGHT_CONFIDENCE_THRESHOLD, 
    CandidateBar, AndreaSignal, FabioSignal, ConsensusSignal
)
from typing import Optional

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'

MAX_SESSION_BUFFER = 5  # keep last N analyses for cross-bar context


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

    reset_session(date_str)
    trades_raw = load_day(csv_path)

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
    candidates = detect_candidates(bars_ny, ctx, bars_1min_ny=bars_1min_ny)

    closed_trades  = []
    open_t         = None
    trade_start_i  = None   # index in bars_ny where current trade was opened
    session_buffer = []     # OPT 4: cross-bar context (last 5 analyses)
    market_narrative = "Inizio giornata. Nessuna narrativa."
    last_eval_idx = 0

    bar_ts_to_idx = {b.timestamp: i for i, b in enumerate(bars_ny)}
    
    # Load processed candidates to allow fast-forward
    processed_candidates = get_already_processed_candidates()

    import pytz as _ff_pytz
    _ff_ET = _ff_pytz.timezone('America/New_York')

    for candidate in candidates:
        bar_idx = bar_ts_to_idx.get(candidate.bar.timestamp)
        if bar_idx is None:
            continue

        bar_ts = candidate.bar.timestamp.strftime('%H:%M UTC')
        bar_et = candidate.bar.timestamp.astimezone(_ff_ET).strftime('%H:%M')
        
        # FAST-FORWARD: Skip if already in reasoning_log
        if (date_str, bar_et) in processed_candidates:
            if not quiet:
                print(f"  {bar_ts} [SKIPPED] Already processed.")
            # We still need to keep the session_buffer updated for future context if any
            # Note: in a real fast-forward we might want to re-load the fabio_signal from log
            # but for now skipping is enough to prevent duplicates.
            continue

        # If a trade is open, try to advance it up to this bar
        if open_t is not None:
            check_bars = bars_ny[trade_start_i + 1: bar_idx + 1]
            result = step_trade(open_t, check_bars)
            if result:
                closed_trades.append(result)
                update_pattern_memory(result)
                
                # UPDATE EQUITY
                state = load_session()
                state['equity'] += result.pnl_usd
                save_session(state)
                
                # PREVENTION: Only log if not already there
                if not is_trade_already_logged(date_str, result.entry_time.isoformat()):
                    log_trade_result(result)
                open_t = None
                trade_start_i = None
            else:
                continue  # still open, skip new candidate

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

        # Fabio full analysis (passed prefilter + light pass)
        if not quiet:
            category_color = "MOMENTUM" if candidate.setup_category == 'momentum' else "REVERSAL"
            print(f"\n  [CANDIDATE] {bar_ts} | {category_color} | wall={candidate.wall_level:.2f} ({candidate.wall_side}) "
                  f"| near={candidate.proximity_to} @ {candidate.proximity_level:.2f}")

        # OPT: extract M1 context for Fabio V3 Unified
        m1_bars = get_m1_context(bars_1min_ny, candidate.bar)

        if not quiet:
            print(f"  [FABIO V3] predatory analysis...", end=' ', flush=True)
        fabio_signal = fabio_analyze(candidate, session_context=session_buffer, m1_bars=m1_bars, market_narrative=market_narrative, bars_since_last=bars_since_last)
        
        # Hard-coded enforcement of AMT_RULE_001: No counter-trend setups on trend days
        if ctx.day_type == 'trend_up' and fabio_signal.direction == 'short':
            fabio_signal.direction = 'none'
            fabio_signal.confidence = 0
            fabio_signal.reasoning = "[RULE FORCED] Day type is trend_up. Counter-trend short setups are strictly prohibited by AMT_RULE_001."
        elif ctx.day_type == 'trend_down' and fabio_signal.direction == 'long':
            fabio_signal.direction = 'none'
            fabio_signal.confidence = 0
            fabio_signal.reasoning = "[RULE FORCED] Day type is trend_down. Counter-trend long setups are strictly prohibited by AMT_RULE_001."

        # Update Narrative State
        if fabio_signal.market_narrative_update:
            market_narrative = fabio_signal.market_narrative_update
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

        if fabio_signal.confidence < FABIO_MIN_CONFIDENCE or fabio_signal.direction == 'none':
            reason = f'fabio_confidence={fabio_signal.confidence} < {FABIO_MIN_CONFIDENCE}' if fabio_signal.confidence < FABIO_MIN_CONFIDENCE else 'fabio_direction_none'
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
        print(f"  [PRECISION] Refining entry with M1 bars...")
        m1_context = get_m1_context(bars_1min_ny, candidate.bar)
        precision = refine_entry(candidate, consensus, m1_context)

        if precision['abort']:
            print(f" -> ABORTED by Precision: {precision['entry_reasoning']}")
            log_entry['decision'] = 'no_trade'
            log_entry['no_trade_reason'] = f"Precision Abort: {precision['entry_reasoning']}"
            log_reasoning(log_entry)
            continue

        # Apply precision levels
        consensus.entry = precision['entry']
        consensus.stop  = precision['stop']
        consensus.target = precision['target']

        # Log entry handling – ensure Andrea reasoning exists
        log_entry['decision'] = 'trade'
        if fabio_only:
            # Dummy Andrea signal for logging
            class _DummyAndrea:
                reasoning = 'fabio_only_skip_andrea'
            andrea_signal = _DummyAndrea()
            log_entry['andrea_confirmation'] = True
            log_entry['andrea_reasoning'] = andrea_signal.reasoning
        else:
            log_entry['andrea_confirmation'] = True
            log_entry['andrea_reasoning'] = andrea_signal.reasoning
        log_entry['precision_reasoning'] = precision['entry_reasoning']

        # ── EXECUTION ───────────────────────────────────────────────
        state = load_session()
        contracts = calculate_contracts(
            consensus.entry, consensus.stop, 
            state['equity'], risk_pct=0.005, 
            instrument='MNQ',
            setup_category=candidate.setup_category
        )
        
        open_t        = open_trade(consensus, candidate.bar, contracts=contracts)
        trade_start_i = bar_idx
        log_entry['trade_direction'] = consensus.direction
        log_entry['trade_entry']     = consensus.entry
        log_entry['trade_stop']      = consensus.stop
        log_entry['trade_target']    = consensus.target
        log_entry['contracts']       = contracts
        print(f"  [TRADE OPEN] dir={consensus.direction} entry={consensus.entry} "
              f"stop={consensus.stop} target={consensus.target} contracts={contracts}")
            
        log_reasoning(log_entry)

    # EOD: close any trade still open after all candidates processed
    if open_t is not None and bars_ny:
        remaining = bars_ny[trade_start_i + 1:]
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
