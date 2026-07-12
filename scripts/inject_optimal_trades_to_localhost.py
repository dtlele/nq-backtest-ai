import json
import pytz
from datetime import datetime, timedelta
from pathlib import Path

def inject():
    trades_path = Path("agent_memory/optimal_backtest_trades.json")
    status_path = Path("dashboard/public/data/status.json")

    if not trades_path.exists():
        print("Error: optimal_backtest_trades.json not found. Run scripts/run_optimal_backtest.py first.")
        return

    with open(trades_path, encoding='utf-8') as f:
        raw_trades = json.load(f)

    print(f"Loaded {len(raw_trades)} trades from optimal backtest.")

    tz_ny = pytz.timezone('America/New_York')

    formatted_trades = []
    for t in raw_trades:
        # Convert date from YYYYMMDD to YYYY-MM-DD
        raw_date = t["date"]
        date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
        
        # Convert time to UTC ISO format
        time_str = t["time"]
        dt_et = datetime.strptime(f"{raw_date} {time_str}", "%Y%m%d %H:%M")
        dt_et = tz_ny.localize(dt_et)
        dt_utc = dt_et.astimezone(pytz.utc)
        entry_time_iso = dt_utc.strftime("%Y-%m-%dT%H:%M:00+00:00")
        
        exit_time_str = t["exit_time"]
        dt_exit_et = datetime.strptime(f"{raw_date} {exit_time_str}", "%Y%m%d %H:%M")
        dt_exit_et = tz_ny.localize(dt_exit_et)
        if dt_exit_et < dt_et:
            dt_exit_et += timedelta(days=1)
        dt_exit_utc = dt_exit_et.astimezone(pytz.utc)
        exit_time_iso = dt_exit_utc.strftime("%Y-%m-%dT%H:%M:00+00:00")

        direction = t["direction"].lower()
        entry = t["entry"]
        sl_pts = t["sl_pts"]
        # Support both old format (tp_pts) and new format (mfe_pts / fixed targets)
        tp_pts = t.get("tp_pts", t.get("mfe_pts", sl_pts * 2.0))

        # Recompute levels
        stop = entry - sl_pts if direction == 'long' else entry + sl_pts
        target = entry + tp_pts if direction == 'long' else entry - tp_pts

        pnl_pts = t["pnl_pts"]
        exit_price = entry + pnl_pts if direction == 'long' else entry - pnl_pts
        
        raw_outcome = t.get("outcome", "")
        if "win" in str(raw_outcome):
            exit_reason = "target"
        elif raw_outcome == "loss":
            exit_reason = "stop"
        else:
            exit_reason = "eod"

        formatted_steps = []
        for step in t.get("steps", []):
            step_time_str = step["time_et"]
            try:
                dt_step_et = datetime.strptime(f"{raw_date} {step_time_str}", "%Y%m%d %H:%M")
                dt_step_et = tz_ny.localize(dt_step_et)
                dt_step_utc = dt_step_et.astimezone(pytz.utc)
                step_time_iso = dt_step_utc.strftime("%Y-%m-%dT%H:%M:00+00:00")
            except Exception as e:
                step_time_iso = None
            
            formatted_steps.append({
                "time_et": step["time_et"],
                "time_utc_iso": step_time_iso,
                "price": step["price"],
                "dominant_side": step["dominant_side"],
                "volume": step["volume"],
                "cumulative_delta": step.get("cumulative_delta", 0)
            })

        formatted_trades.append({
            "date": date_str,
            "entry_time": entry_time_iso,
            "exit_time": exit_time_iso,
            "direction": direction,
            "entry": entry,
            "stop": stop,
            "target": target,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "pnl_ticks": t["pnl_pts"] * 4.0,
            "pnl_usd": t["pnl_usd"],
            "r_ratio": round(tp_pts / sl_pts, 1),
            "setup_type": t["setup"].split(':')[0].lower().replace(' ', '_'),
            "final_confidence": 100,
            "fabio_reasoning": f"Optimized Execution Trade - {t['setup']}",
            "andrea_reasoning": "Confirm setup via rule execution engine.",
            "contracts": t.get("contracts", 1.0),
            "news_flag": "none",
            "amt_day_profile": "Price Discovery Phase",
            "macro_regime": {
                "regime": "EXPANSIVE (Initiative Momentum)",
                "duration_mins": 30,
                "trigger": "Optimized cluster setup trigger",
                "bias": direction
            },
            "trapped_info": "",
            "trapped_follow_through": "Confirmed",
            "logged_at": entry_time_iso,
            "run": "optimal_backtest",
            "steps": formatted_steps
        })

    # Group by date for MOCK_SESSIONS
    groups = {}
    for t in formatted_trades:
        d = t["date"]
        if d not in groups:
            groups[d] = []
        groups[d].append(t)

    # Load list of JSON files in data directory to populate ANALYZED_DATES
    data_dir = Path("dashboard/public/data")
    analyzed_dates = sorted([f.stem for f in data_dir.glob("????-??-??.json")])

    for d in analyzed_dates:
        if d not in groups:
            groups[d] = []

    mock_sessions = []
    for d in sorted(groups.keys()):
        day_trades = groups[d]
        wins = len([t for t in day_trades if t["pnl_usd"] > 0])
        losses = len([t for t in day_trades if t["pnl_usd"] <= 0])
        pnl = sum(t["pnl_usd"] for t in day_trades)
        mock_sessions.append({
            "date": d,
            "trades": len(day_trades),
            "wins": wins,
            "losses": losses,
            "pnl": pnl,
            "proposals": len(day_trades)
        })

    def calc_kpi(tl):
        wins = [t for t in tl if t["pnl_usd"] > 0]
        losses = [t for t in tl if t["pnl_usd"] <= 0]
        total_pnl = sum(t["pnl_usd"] for t in tl)
        dates = list(set(t["date"] for t in tl))
        
        gross_profit = sum(t["pnl_usd"] for t in wins)
        gross_loss = abs(sum(t["pnl_usd"] for t in losses))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.9
        
        avg_win = gross_profit / len(wins) if wins else 0
        avg_loss = gross_loss / len(losses) if losses else 0
        asimmetria = round(avg_win / avg_loss, 2) if avg_loss else 2.00
        
        win_rate = len(wins) / len(tl) if tl else 0
        loss_rate = len(losses) / len(tl) if tl else 0
        expectancy = round((win_rate * avg_win) - (loss_rate * avg_loss), 2)
        
        # Drawdown and Streaks
        peak, running, max_dd = 0, 0, 0
        curr_win_streak, max_win_streak = 0, 0
        curr_loss_streak, max_loss_streak = 0, 0
        
        for t in tl:
            running += t["pnl_usd"]
            peak = max(peak, running)
            max_dd = max(max_dd, peak - running)
            
            if t["pnl_usd"] > 0:
                curr_win_streak += 1
                curr_loss_streak = 0
                max_win_streak = max(max_win_streak, curr_win_streak)
            else:
                curr_loss_streak += 1
                curr_win_streak = 0
                max_loss_streak = max(max_loss_streak, curr_loss_streak)
        
        # Edge KPIs (Per Setup)
        setups = set(t["setup_type"] for t in tl)
        edge_kpis = {}
        for s in setups:
            stl = [t for t in tl if t["setup_type"] == s]
            s_wins = [t for t in stl if t["pnl_usd"] > 0]
            s_losses = [t for t in stl if t["pnl_usd"] <= 0]
            s_gross_profit = sum(t["pnl_usd"] for t in s_wins)
            s_gross_loss = abs(sum(t["pnl_usd"] for t in s_losses))
            s_pf = round(s_gross_profit / s_gross_loss, 2) if s_gross_loss > 0 else 99.9
            s_avg_win = s_gross_profit / len(s_wins) if s_wins else 0
            s_avg_loss = s_gross_loss / len(s_losses) if s_losses else 0
            s_wr = len(s_wins) / len(stl) if stl else 0
            s_lr = len(s_losses) / len(stl) if stl else 0
            s_exp = round((s_wr * s_avg_win) - (s_lr * s_avg_loss), 2)
            edge_kpis[s] = {
                'totalTrades': len(stl),
                'winRate': round(s_wr * 100, 1),
                'totalPnL': sum(t["pnl_usd"] for t in stl),
                'profitFactor': s_pf,
                'expectancy': s_exp
            }

        return {
            'totalTrades': len(tl),
            'totalDays': len(dates),
            'winRate': round(win_rate * 100, 1),
            'totalPnL': total_pnl,
            'wins': len(wins),
            'losses': len(losses),
            'asimmetria': asimmetria,
            'maxDrawdown': round((max_dd / 50000) * 100, 2),
            'profitFactor': profit_factor,
            'expectancy': expectancy,
            'maxWinStreak': max_win_streak,
            'maxLossStreak': max_loss_streak,
            'edgeKpis': edge_kpis,
            'navAlerts': 0,
            'middayRejections': 0,
        }

    kpi = calc_kpi(formatted_trades)

    status_data = {
        "ALL_TRADES": formatted_trades,
        "ALL_PROPOSALS": formatted_trades,
        "ALL_REASONINGS": [],
        "ANALYZED_DATES": analyzed_dates,
        "OPEN_TRADE": None,
        "LIVE_SESSION_STATE": {},
        "LATEST_REASONING": {},
        "MOCK_SESSIONS": mock_sessions,
        "MOCK_KPI": kpi,
        "KPI_VWAP_NAV": kpi
    }

    with open(status_path, 'w', encoding='utf-8') as f:
        json.dump(status_data, f, indent=2)

    print(f"Successfully injected {len(formatted_trades)} trades into {status_path}")

if __name__ == "__main__":
    inject()
