"""
Main backtest loop.
For each day:
  1. Load trades from CSV
  2. Aggregate to 1-min bars
  3. Filter NY window
  4. Build Volume Profile (from all session bars)
  5. Build SessionContext (IB, day_type)
  6. Detect candidates
  7. For each candidate: Fabio → Andrea → Consensus → TradeSimulator
  8. Log to agent_memory, collect ClosedTrades
"""
import json
from pathlib import Path
from src.data_loader import load_day, list_data_files
from src.bar_aggregator import aggregate_to_bars
from src.volume_profile import compute_volume_profile
from src.session_context import filter_ny_window, build_session_context
from src.candidate_detector import detect_candidates
from src.agents.fabio_agent import analyze as fabio_analyze
from src.agents.andrea_agent import confirm as andrea_confirm
from src.consensus import build_consensus
from src.trade_simulator import open_trade, step_trade, close_eod
from src.agent_memory import reset_session, log_reasoning, update_pattern_memory
from src import FABIO_MIN_CONFIDENCE

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'

def run_day(csv_path: str, dry_run: bool = False) -> list:
    """Run backtest for one day. Returns list[ClosedTrade]."""
    date_str = Path(csv_path).name.split('-')[2].split('.')[0]  # e.g. 20250430
    date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    reset_session(date_str)
    trades_raw = load_day(csv_path)
    bars_all   = aggregate_to_bars(trades_raw, freq='1min')
    bars_ny    = filter_ny_window(bars_all)
    if not bars_ny:
        return []

    vp  = compute_volume_profile(bars_ny)
    ctx = build_session_context(date_str, bars_ny, vp)
    candidates = detect_candidates(bars_ny, ctx)

    closed_trades = []
    open_t        = None
    trade_start_i = None   # index in bars_ny where current trade was opened

    # Build a mapping from bar timestamp → index for O(1) lookup
    bar_ts_to_idx = {b.timestamp: i for i, b in enumerate(bars_ny)}

    for candidate in candidates:
        bar_idx = bar_ts_to_idx.get(candidate.bar.timestamp)
        if bar_idx is None:
            continue

        # If a trade is open, try to advance it up to this bar
        if open_t is not None:
            check_bars = bars_ny[trade_start_i + 1: bar_idx + 1]
            result = step_trade(open_t, check_bars)
            if result:
                closed_trades.append(result)
                update_pattern_memory(result)
                open_t = None
                trade_start_i = None
            else:
                continue  # still open, skip new candidate

        if dry_run:
            print(f"  [DRY RUN] {candidate.bar.timestamp} "
                  f"| wall={candidate.wall_level} | near={candidate.proximity_to}")
            continue

        # Fabio primary analysis
        fabio_signal = fabio_analyze(candidate)
        log_entry = {
            'date': date_str,
            'bar_time': candidate.bar.timestamp.isoformat(),
            'wall_level': candidate.wall_level,
            'proximity_to': candidate.proximity_to,
            'fabio_direction': fabio_signal.direction,
            'fabio_confidence': fabio_signal.confidence,
        }

        if fabio_signal.confidence < FABIO_MIN_CONFIDENCE:
            log_entry['decision'] = 'no_trade'
            log_entry['reason'] = f'fabio_confidence={fabio_signal.confidence}'
            log_reasoning(log_entry)
            continue

        # Andrea confirmation
        andrea_signal = andrea_confirm(candidate, fabio_signal)
        log_entry['andrea_confirmation'] = andrea_signal.confirmation
        log_entry['andrea_confidence']   = andrea_signal.confidence

        consensus = build_consensus(fabio_signal, andrea_signal)
        log_entry['decision']          = consensus.decision
        log_entry['final_confidence']  = consensus.final_confidence

        if consensus.decision == 'trade':
            open_t        = open_trade(consensus, candidate.bar)
            trade_start_i = bar_idx

        log_reasoning(log_entry)

    # EOD: close any trade still open after all candidates processed
    if open_t is not None and bars_ny:
        remaining = bars_ny[trade_start_i + 1:]
        result    = step_trade(open_t, remaining) or close_eod(open_t, bars_ny[-1])
        closed_trades.append(result)
        update_pattern_memory(result)

    return closed_trades


def run_backtest(data_dir: str, max_days: int = 0, dry_run: bool = False) -> list:
    """Run all days. Returns all ClosedTrades."""
    files = list_data_files(data_dir)
    if max_days:
        files = files[:max_days]
    all_trades = []
    for f in files:
        print(f"Processing {Path(f).name}...")
        day_trades = run_day(f, dry_run=dry_run)
        all_trades.extend(day_trades)
        print(f"  → {len(day_trades)} trades")
    return all_trades
