"""
sync_loop.py — Aggiorna status.json ogni 5 secondi mentre il backtest gira.
"""
import time
import sys
import json
import os
from pathlib import Path

memory_dir = Path("c:/Users/Mauro/Documents/nq-backtest/agent_memory")
trades_file = memory_dir / "trades_log.jsonl"
session_file = memory_dir / "session_state.json"
reasoning_file = memory_dir / "reasoning_log.jsonl"
chart_data_dir = Path("c:/Users/Mauro/Documents/nq-backtest/dashboard/public/data")
out_path = chart_data_dir / "status.json"

def read_jsonl(path):
    rows = []
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        rows.append(json.loads(line))
                    except:
                        pass
    return rows

def get_latest_line(path):
    if not path.exists():
        return {}
    try:
        with open(path, 'rb') as f:
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
                return json.loads(line.decode('utf-8'))
    except:
        pass
    return {}

def build_status():
    trades = read_jsonl(trades_file)
    reasonings = read_jsonl(reasoning_file)

    proposals = []
    all_reasonings = []
    for r in reasonings:
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
                'fabio_imbalance_phase': r.get('fabio_imbalance_phase', 'none'),
                'session_bias': r.get('session_bias', 'none'),
                'news_flag': r.get('news_flag', 'none'),
                'amt_day_profile': r.get('amt_day_profile', 'Price Discovery Phase'),
                'macro_regime': r.get('macro_regime'),
                'trapped_info': r.get('trapped_info'),
                'trapped_follow_through': r.get('trapped_follow_through'),
            })
        all_reasonings.append({
            'date': r.get('date'),
            'bar_time_et': r.get('bar_time_et'),
            'bar_time_utc': r.get('bar_time_utc'),
            'bar_open': r.get('bar_open'),
            'bar_high': r.get('bar_high'),
            'bar_low': r.get('bar_low'),
            'bar_close': r.get('bar_close'),
            'bar_volume': r.get('bar_volume'),
            'bar_delta': r.get('bar_delta'),
            'direction': direction,
            'confidence': conf,
            'decision': r.get('decision', 'no_trade'),
            'no_trade_reason': r.get('no_trade_reason', ''),
            'fabio_reasoning': r.get('fabio_reasoning', ''),
            'fabio_setup': r.get('fabio_setup', 'none'),
            'fabio_entry': r.get('fabio_entry'),
            'fabio_stop': r.get('fabio_stop'),
            'fabio_target': r.get('fabio_target'),
            'fabio_direction': r.get('fabio_direction', 'none'),
            'fabio_imbalance_phase': r.get('fabio_imbalance_phase', 'none'),
            'andrea_reasoning': r.get('andrea_reasoning', ''),
            'market_narrative': r.get('market_narrative', ''),
            'market_structure': r.get('market_structure', '---'),
            'market_state': r.get('market_state', '---'),
            'poc': r.get('poc'),
            'va_high': r.get('va_high'),
            'va_low': r.get('va_low'),
            'ib_high': r.get('ib_high'),
            'ib_low': r.get('ib_low'),
            'ib_range': r.get('ib_range'),
            'day_type': r.get('day_type'),
            'prev_day_poc': r.get('prev_day_poc'),
            'prev_day_vah': r.get('prev_day_vah'),
            'prev_day_val': r.get('prev_day_val'),
            'delta_divergence': r.get('delta_divergence'),
            'effort_no_result': r.get('effort_no_result'),
            'top_wick_ratio': r.get('top_wick_ratio'),
            'bottom_wick_ratio': r.get('bottom_wick_ratio'),
            'close_percentile': r.get('close_percentile'),
            'session_memory': r.get('session_memory', []),
            'session_bias': r.get('session_bias', 'none'),
            'news_flag': r.get('news_flag', 'none'),
            'amt_day_profile': r.get('amt_day_profile', 'Price Discovery Phase'),
            'macro_regime': r.get('macro_regime'),
            'trapped_info': r.get('trapped_info'),
            'trapped_follow_through': r.get('trapped_follow_through'),
            'ib_breakouts_count': r.get('ib_breakouts_count', 0),
            'ib_first_breakout_dir': r.get('ib_first_breakout_dir', 'none'),
            'entry_type': r.get('entry_type', 'setup'),
        })

    session_state = {}
    if session_file.exists():
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_state = json.load(f)
        except:
            pass

    analyzed_dates = sorted([f.stem for f in chart_data_dir.glob("????-??-??.json")])
    latest_reasoning = get_latest_line(reasoning_file)

    def calc_kpi(tl):
        wins = [t for t in tl if t.get('pnl_usd', 0) > 0]
        losses = [t for t in tl if t.get('pnl_usd', 0) <= 0]
        total_pnl = sum(t.get('pnl_usd', 0) for t in tl)
        dates = list(set(t.get('date') for t in tl))
        avg_win = sum(t.get('pnl_usd', 0) for t in wins) / len(wins) if wins else 0
        avg_loss = abs(sum(t.get('pnl_usd', 0) for t in losses) / len(losses)) if losses else 0
        asimmetria = round(avg_win / avg_loss, 2) if avg_loss else 2.00
        peak, running, max_dd = 0, 0, 0
        for t in tl:
            running += t.get('pnl_usd', 0)
            peak = max(peak, running)
            max_dd = max(max_dd, peak - running)
        return {
            'totalTrades': len(tl),
            'totalDays': len(dates),
            'winRate': round(len(wins) / len(tl) * 100, 1) if tl else 0,
            'totalPnL': total_pnl,
            'wins': len(wins),
            'losses': len(losses),
            'asimmetria': asimmetria,
            'maxDrawdown': round((max_dd / 50000) * 100, 2),
            'navAlerts': 0,
            'middayRejections': 0,
        }

    def group_by_date(tl):
        groups = {}
        for t in tl:
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
            result.append({'date': date, 'trades': len(day_trades), 'wins': wins, 'losses': losses, 'pnl': pnl, 'proposals': len([p for p in proposals if p.get('date') == date])})
        return result

    return {
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

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    print("[SYNC] Sync loop avviato -- aggiornamento status.json ogni 5 secondi")
    print(f"   Output: {out_path}")
    iteration = 0
    while True:
        try:
            data = build_status()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                temp_path = out_path.with_suffix('.tmp')
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                # On Windows, replace can fail if the file is being read by the dev server
                import os
                if out_path.exists():
                    os.remove(out_path)
                os.rename(temp_path, out_path)
            except PermissionError:
                # If Vite is currently locking the file, we just skip this 5-sec update
                pass
            iteration += 1
            trades_count = len(data["ALL_TRADES"])
            latest = data["LATEST_REASONING"]
            bar_time = latest.get("bar_time_et", "---")
            date = latest.get("date", "---")
            decision = latest.get("decision", "---")
            print(f"[{iteration}] OK status.json aggiornato | trades={trades_count} | ultimo: {date} {bar_time} -> {decision}", flush=True)
        except Exception as e:
            print(f"[ERRORE] {e}", flush=True)
        time.sleep(5)
