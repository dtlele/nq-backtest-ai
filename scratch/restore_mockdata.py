import json
import os
from pathlib import Path

memory_dir = Path("c:/Users/Mauro/Documents/nq-backtest/agent_memory")
trades_file = memory_dir / "trades_log.jsonl"
session_file = memory_dir / "session_state.json"
reasoning_file = memory_dir / "reasoning_log.jsonl"
marker_file = memory_dir / "run_start_marker.json"

import datetime

trades = []
if trades_file.exists():
    with open(trades_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    t = json.loads(line)
                    trades.append(t)
                except:
                    pass

# Extract all Fabio proposals (conf >= 60) and all reasoning lines
proposals = []
all_reasonings = []
if reasoning_file.exists():
    with open(reasoning_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                
                # Check for proposal (conf >= 60)
                conf = r.get('fabio_confidence', 0) or 0
                direction = r.get('fabio_direction', '')
                entry = r.get('fabio_entry')
                stop = r.get('fabio_stop')
                target = r.get('fabio_target')
                if direction in ('long', 'short') and conf >= 60 and entry and stop and target:
                    proposals.append({
                        'date': r.get('date'),
                        'bar_time_et': r.get('bar_time_et'),
                        'bar_time_utc': r.get('bar_time_utc'),
                        'direction': direction,
                        'confidence': conf,
                        'entry': entry,
                        'stop': stop,
                        'target': target,
                        'decision': r.get('decision', 'no_trade'),
                        'no_trade_reason': r.get('no_trade_reason', ''),
                        'fabio_reasoning': r.get('fabio_reasoning', ''),
                        'setup_type': r.get('fabio_setup', ''),
                    })
                
                # Add to all reasonings
                all_reasonings.append({
                    'date': r.get('date'),
                    'bar_time_et': r.get('bar_time_et'),
                    'bar_time_utc': r.get('bar_time_utc'),
                    'direction': direction,
                    'confidence': conf,
                    'decision': r.get('decision', 'no_trade'),
                    'no_trade_reason': r.get('no_trade_reason', ''),
                    'fabio_reasoning': r.get('fabio_reasoning', ''),
                    'setup_type': r.get('fabio_setup', 'none'),
                    'andrea_reasoning': r.get('andrea_reasoning', ''),
                    'market_narrative': r.get('market_narrative', ''),
                    'poc': r.get('poc'),
                    'va_high': r.get('va_high'),
                    'va_low': r.get('va_low'),
                    'ib_high': r.get('ib_high'),
                    'ib_low': r.get('ib_low'),
                    'day_type': r.get('day_type'),
                    'prev_day_poc': r.get('prev_day_poc'),
                    'prev_day_vah': r.get('prev_day_vah'),
                    'prev_day_val': r.get('prev_day_val'),
                    'bar_volume': r.get('bar_volume'),
                    'bar_delta': r.get('bar_delta'),
                    'delta_divergence': r.get('delta_divergence'),
                    'effort_no_result': r.get('effort_no_result'),
                    'top_wick_ratio': r.get('top_wick_ratio'),
                    'bottom_wick_ratio': r.get('bottom_wick_ratio'),
                    'close_percentile': r.get('close_percentile'),
                    'session_memory': r.get('session_memory', [])
                })
            except:
                pass

session_state = {}
if session_file.exists():
    try:
        with open(session_file, 'r', encoding='utf-8') as f:
            session_state = json.load(f)
    except:
        pass

# Extract unique dates that were actually analyzed
# Use ALL chart JSON files available — not just reasoning log dates.
# This ensures the sidebar shows every day that has been exported,
# even if the current run's reasoning_log doesn't include it.
chart_data_dir = Path("c:/Users/Mauro/Documents/nq-backtest/dashboard/public/data")
analyzed_dates = sorted([
    f.stem for f in chart_data_dir.glob("????-??-??.json")
])

latest_reasoning = {}
if reasoning_file.exists():
    try:
        with open(reasoning_file, 'rb') as f:
            f.seek(0, os.SEEK_END)
            position = f.tell()
            line = b''
            while position >= 0:
                f.seek(position)
                next_char = f.read(1)
                if next_char == b'\n' and line:
                    break
                line = next_char + line
                position -= 1
            if line:
                latest_reasoning = json.loads(line.decode('utf-8'))
    except Exception as e:
        print("Error reading latest reasoning:", e)

# Calculate KPIs
def calc_kpi(trades_list):
    wins = [t for t in trades_list if t.get('pnl_usd', 0) > 0]
    losses = [t for t in trades_list if t.get('pnl_usd', 0) <= 0]
    total_pnl = sum(t.get('pnl_usd', 0) for t in trades_list)
    dates = list(set(t.get('date') for t in trades_list))
    
    avg_win = sum(t.get('pnl_usd', 0) for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t.get('pnl_usd', 0) for t in losses) / len(losses)) if losses else 0
    asimmetria = round(avg_win / avg_loss, 2) if avg_loss else 2.00
    
    peak = 0
    running = 0
    max_dd = 0
    for t in trades_list:
        running += t.get('pnl_usd', 0)
        peak = max(peak, running)
        max_dd = max(max_dd, peak - running)
    max_drawdown = round((max_dd / 50000) * 100, 2)
    
    midday_rejections = len([p for p in proposals if 'midday' in str(p.get('no_trade_reason', '')).lower()])
    
    return {
        'totalTrades': len(trades_list),
        'totalDays': len(dates),
        'winRate': round(len(wins) / len(trades_list) * 100, 1) if trades_list else 0,
        'totalPnL': total_pnl,
        'wins': len(wins),
        'losses': len(losses),
        'asimmetria': asimmetria,
        'maxDrawdown': max_drawdown,
        'navAlerts': len([p for p in proposals if 'abnormal' in str(p.get('fabio_reasoning', '')).lower()]),
        'middayRejections': midday_rejections
    }

def group_by_date(trades_list):
    groups = {}
    for t in trades_list:
        d = t.get('date')
        if d not in groups:
            groups[d] = []
        groups[d].append(t)
        
    live_date = session_state.get('date')
    if live_date and live_date not in groups:
        groups[live_date] = []
        
    for d in analyzed_dates:
        if d not in groups:
            groups[d] = []
            
    result = []
    for date in sorted(groups.keys()):
        day_trades = groups[date]
        wins = len([t for t in day_trades if t.get('pnl_usd', 0) > 0])
        losses = len([t for t in day_trades if t.get('pnl_usd', 0) <= 0])
        pnl = sum(t.get('pnl_usd', 0) for t in day_trades)
        has_new_run = any(t.get('run') == 'vwap_nav' for t in day_trades)
        day_proposals = len([p for p in proposals if p.get('date') == date])
        result.append({
            'date': date,
            'trades': len(day_trades),
            'wins': wins,
            'losses': losses,
            'pnl': pnl,
            'hasNewRun': has_new_run,
            'proposals': day_proposals
        })
    return result

status_data = {
    "ALL_TRADES": trades,
    "ALL_PROPOSALS": proposals,
    "ALL_REASONINGS": all_reasonings,
    "ANALYZED_DATES": analyzed_dates,
    "OPEN_TRADE": session_state.get('open_trade', None),
    "LIVE_SESSION_STATE": session_state,
    "LATEST_REASONING": latest_reasoning,
    "MOCK_SESSIONS": group_by_date(trades),
    "MOCK_KPI": calc_kpi(trades),
    "KPI_VWAP_NAV": calc_kpi([t for t in trades if t.get('run') == 'vwap_nav'])
}

out_path = Path("c:/Users/Mauro/Documents/nq-backtest/dashboard/public/data/status.json")
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(status_data, f, indent=2)

print("Restored status.json successfully!")
print(f"  Trades chiusi: {len(trades)}")
print(f"  Proposals Fabio (conf>=60): {len(proposals)}")
print(f"  Giorni con proposals: {len(set(p['date'] for p in proposals))}")
