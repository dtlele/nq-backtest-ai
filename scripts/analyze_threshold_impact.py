import json
import os
import sys
import bisect
import time
from pathlib import Path
from datetime import datetime
import pytz
import pandas as pd
import numpy as np

sys.path.append(r"C:\Users\Mauro\Documents\nq-backtest")

ET = pytz.timezone("America/New_York")
DATA_DIR = Path(r"C:\Users\Mauro\Documents\nq-backtest\dashboard\public\data")
CACHE_DIR = r"C:\Users\Mauro\Documents\nq-backtest\cache_ohlc"

class MockBar:
    def __init__(self, timestamp, open_, high, low, close):
        self.timestamp = timestamp
        self.open = open_
        self.high = high
        self.low = low
        self.close = close

bars_cache = {}
cached_dates = []

def get_bars_for_date(date_str):
    if date_str in bars_cache:
        return bars_cache[date_str]
    cache_file = Path(CACHE_DIR) / f"{date_str}.csv"
    if cache_file.exists():
        try:
            df = pd.read_csv(cache_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            records = df.to_dict(orient='records')
            bars = [MockBar(row['timestamp'].to_pydatetime(), row['open'], row['high'], row['low'], row['close']) for row in records]
            bars_cache[date_str] = bars
            return bars
        except Exception:
            pass
    return None

def compute_5day_atr(date_str):
    idx = bisect.bisect_left(cached_dates, date_str)
    prev_dates = cached_dates[max(0, idx - 5):idx]
    if len(prev_dates) < 5:
        return 180.0
    ranges = []
    for d in prev_dates:
        bars = get_bars_for_date(d)
        if bars:
            r_high = max(b.high for b in bars)
            r_low  = min(b.low  for b in bars)
            ranges.append(r_high - r_low)
    if len(ranges) >= 3:
        return np.mean(ranges)
    return 180.0

big_trades_cache = {}

def check_contrary_big_trades(date_str, step1_time_str, end_time_str, direction, threshold=150):
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    if date_str not in big_trades_cache:
        day_file = DATA_DIR / f"{formatted_date}.json"
        if day_file.exists():
            try:
                with open(day_file, "r", encoding="utf-8") as f:
                    day_data = json.load(f)
                big_trades_cache[date_str] = day_data.get("big_trades", [])
            except Exception:
                big_trades_cache[date_str] = []
        else:
            big_trades_cache[date_str] = []

    big_trades = big_trades_cache[date_str]
    if not big_trades:
        return False
    try:
        dt_start = ET.localize(datetime.strptime(f"{date_str} {step1_time_str}", "%Y%m%d %H:%M"))
        dt_end   = ET.localize(datetime.strptime(f"{date_str} {end_time_str}",   "%Y%m%d %H:%M"))
        start_ts = int(dt_start.timestamp())
        end_ts   = int(dt_end.timestamp())
        contrary_side = 'B' if direction == "long" else 'A'
        for bt in big_trades:
            if start_ts <= bt["time"] <= end_ts:
                if bt["side"] == contrary_side and bt["size"] >= threshold:
                    return True
    except Exception:
        pass
    return False

SESSIONS = {
    "open":  (9*60+30, 11*60),       # 09:30 - 11:00
    "mid":   (11*60,   14*60),       # 11:00 - 14:00
    "close": (14*60,   16*60),       # 14:00 - 16:00
}

def get_session_label(t_val):
    for name, (start, end) in SESSIONS.items():
        if start <= t_val < end:
            return name
    return "other"

def precompute_all_trades_no_filter(seqs_combined, raw_lookup):
    """Precompute all trades without any volume filter so we can filter dynamically later."""
    low_vol_setups = {
        "trend_long":  {"direction": "long",  "sl": 39.0, "tp": 120.0},
        "absorb_long": {"direction": "long",  "sl": 49.0, "tp":  37.0},
        "trend_short": {"direction": "short", "sl": 46.0, "tp": 120.0},
        "absorb_short":{"direction": "short", "sl": 49.0, "tp": 114.0}
    }
    high_vol_setups = {
        "trend_long":  {"direction": "long",  "sl": 22.0, "tp": 113.0},
        "absorb_long": {"direction": "long",  "sl": 50.0, "tp": 115.0},
        "trend_short": {"direction": "short", "sl": 48.0, "tp": 113.0},
        "absorb_short":{"direction": "short", "sl": 34.0, "tp":  35.0}
    }

    trades = []
    base_contracts = 3
    point_value    = 2.0
    commission     = 0.50

    total = len(seqs_combined)
    print(f"Starting precomputation for {total} combined sequences...")
    
    count = 0
    for s in seqs_combined:
        count += 1
        if count % 200 == 0:
            print(f"Processed {count}/{total} sequences...")
            
        date_str    = s["date"]
        time_str    = s["end_time"]
        entry_price = s["entry_price"]
        pattern     = s["seq_pattern"]
        vol         = s['entry_vol']

        h, m = int(time_str.split(':')[0]), int(time_str.split(':')[1])
        t_val = h * 60 + m
        if not (9*60+30 <= t_val < 16*60):
            continue

        atr = compute_5day_atr(date_str)
        setup_info = (low_vol_setups if atr < 200.0 else high_vol_setups).get(pattern)
        if not setup_info:
            continue

        direction = setup_info["direction"]
        sl = setup_info["sl"]
        tp = setup_info["tp"]

        raw_seq = raw_lookup.get((date_str, time_str))
        if not raw_seq or not raw_seq.get("steps"):
            continue

        last_step = raw_seq["steps"][-1]

        # Extract features for filtering
        session_cvd = last_step.get("session_cvd", 0)
        vs_val = last_step.get("price_vs_val", "unknown")
        vs_vah = last_step.get("price_vs_vah", "unknown")
        is_inside_va = (vs_val == "above" and vs_vah == "below")
        
        step1_time = raw_seq["steps"][0]["time_et"]
        has_contrary_150 = check_contrary_big_trades(date_str, step1_time, time_str, direction, threshold=150)

        bars = get_bars_for_date(date_str)
        if not bars:
            continue

        entry_idx = -1
        for i, b in enumerate(bars):
            t_et = b.timestamp.astimezone(ET)
            if t_et.strftime("%H:%M") == time_str:
                entry_idx = i
                break
        if entry_idx == -1:
            continue

        outcome = None
        pnl_pts = 0.0
        exit_time_str = None

        for i in range(entry_idx + 1, len(bars)):
            bar = bars[i]
            t_et = bar.timestamp.astimezone(ET)
            if t_et.hour >= 16:
                outcome = "eod"
                exit_price = bar.close
                pnl_pts = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
                exit_time_str = t_et.strftime("%H:%M")
                break
            if direction == "long":
                if bar.low <= entry_price - sl:
                    pnl_pts = -sl; outcome = "loss"; exit_time_str = t_et.strftime("%H:%M"); break
                elif bar.high >= entry_price + tp + 0.25:
                    pnl_pts = tp;  outcome = "win";  exit_time_str = t_et.strftime("%H:%M"); break
            else:
                if bar.high >= entry_price + sl:
                    pnl_pts = -sl; outcome = "loss"; exit_time_str = t_et.strftime("%H:%M"); break
                elif bar.low <= entry_price - tp - 0.25:
                    pnl_pts = tp;  outcome = "win";  exit_time_str = t_et.strftime("%H:%M"); break

        if outcome is None:
            last_bar = bars[-1]
            t_et = last_bar.timestamp.astimezone(ET)
            outcome = "eod"
            exit_price = last_bar.close
            pnl_pts = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
            exit_time_str = t_et.strftime("%H:%M")

        pnl_pts -= 1.5
        pnl_usd  = ((pnl_pts * point_value) - commission) * base_contracts

        dt_obj     = datetime.strptime(date_str, "%Y%m%d")
        day_of_week = dt_obj.strftime("%A")
        session    = get_session_label(t_val)

        entry_dt = ET.localize(pd.to_datetime(date_str + ' ' + time_str, format='%Y%m%d %H:%M'))
        exit_dt  = ET.localize(pd.to_datetime(date_str + ' ' + exit_time_str, format='%Y%m%d %H:%M'))
        if exit_dt < entry_dt:
            exit_dt += pd.Timedelta(days=1)

        trades.append({
            "pattern":        pattern,
            "date":           date_str,
            "time_str":       time_str,
            "day_of_week":    day_of_week,
            "session":        session,
            "entry_dt":       entry_dt,
            "exit_dt":        exit_dt,
            "pnl_usd":        pnl_usd,
            "is_win":         outcome == "win",
            "pnl_pts":        pnl_pts,
            "vol":            vol,
            "session_cvd":    session_cvd,
            "is_inside_va":   is_inside_va,
            "has_contrary":   has_contrary_150,
            "direction":      direction
        })

    return sorted(trades, key=lambda x: x["entry_dt"])

def simulate_portfolio(trades, rules, vol_ranges, apply_filters=True, disable_time_rules=False):
    trades_executed = []
    last_exit_datetime = None

    for t in trades:
        pat  = t["pattern"]
        rule = rules.get(pat)
        if not rule:
            continue
        
        # Volume Filter: check if volume is in any of the specified ranges
        vol = t["vol"]
        in_range = any(min_v <= vol < max_v for min_v, max_v in vol_ranges)
        if not in_range:
            continue
            
        # Time and Day rules check (optional, to increase sample size)
        if not disable_time_rules:
            # Day of week
            if t["day_of_week"] not in rule["days"]:
                continue
                
            # Session
            if t["session"] not in rule["sessions"]:
                continue
                
            # Exclude 10 AM Economic News Release Block (09:55 - 10:05)
            if rule.get("exclude_10am", False):
                h, m = map(int, t["time_str"].split(':'))
                tv = h * 60 + m
                if 9*60+55 <= tv <= 10*60+5:
                    continue

        # CVD, VA, and Contrary Filters
        if apply_filters:
            if abs(t["session_cvd"]) >= 1200:
                continue
            if t["direction"] == "short" and t["is_inside_va"]:
                continue
            if t["has_contrary"]:
                continue

        # Concurrency Lock
        if last_exit_datetime is not None and t["entry_dt"] < last_exit_datetime:
            continue
            
        trades_executed.append(t)
        last_exit_datetime = t["exit_dt"]

    return trades_executed

def calculate_metrics(trades_executed):
    if not trades_executed:
        return {"N": 0, "WR": 0.0, "PF": 0.0, "PnL": 0.0, "MaxDD": 0.0}
    n     = len(trades_executed)
    wins  = sum(1 for t in trades_executed if t["is_win"])
    wr    = (wins / n) * 100
    pnl   = sum(t["pnl_usd"] for t in trades_executed)
    
    gross_prof = sum(t["pnl_usd"] for t in trades_executed if t["pnl_usd"] > 0)
    gross_loss = abs(sum(t["pnl_usd"] for t in trades_executed if t["pnl_usd"] < 0))
    pf = gross_prof / gross_loss if gross_loss > 0 else float('inf')
    
    # Calculate Max Drawdown
    current = 50000.0
    peak = 50000.0
    max_dd = 0.0
    for t in trades_executed:
        current += t["pnl_usd"]
        peak = max(peak, current)
        max_dd = max(max_dd, peak - current)
        
    return {"N": n, "WR": wr, "PF": pf, "PnL": pnl, "MaxDD": max_dd}

def main():
    global cached_dates
    print("Scanning CSV files in cache_ohlc...")
    cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    print(f"Found {len(cached_dates)} cache files.")

    print("Loading sequences...")
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined_2025.json", encoding="utf-8") as f:
        seqs_combined_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2025.json", encoding="utf-8") as f:
        seqs_raw_2025 = json.load(f)
        
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        seqs_combined_2026 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2026.json", encoding="utf-8") as f:
        seqs_raw_2026 = json.load(f)
        
    raw_lookup = {}
    for s in seqs_raw_2025 + seqs_raw_2026:
        k = (s["date"], s["end_time"])
        raw_lookup[k] = s
        
    seqs_combined = seqs_combined_2025 + seqs_combined_2026
    seqs_combined = sorted(seqs_combined, key=lambda x: (x["date"], x["end_time"]))

    # Precompute all possible trades
    all_trades = precompute_all_trades_no_filter(seqs_combined, raw_lookup)
    print(f"Precomputed {len(all_trades)} total possible trades.")

    # Rules that allow trading any day and session during RTH hours to increase sample size
    relaxed_rules = {
        "trend_long": {"days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "sessions": ["open", "mid", "close"]},
        "absorb_long": {"days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "sessions": ["open", "mid", "close"]},
        "trend_short": {"days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "sessions": ["open", "mid", "close"]},
        "absorb_short": {"days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "sessions": ["open", "mid", "close"]}
    }

    # Volume ranges to test
    ranges_to_test = [
        ("80 - 150 (Baseline)", [(80, 150)]),
        ("80 - 120 (Optimal Medium)", [(80, 120)]),
        ("100 - 120 (Institutional)", [(100, 120)]),
        ("120 - 150 (Toxic Mid-High)", [(120, 150)]),
        ("150 - 200 (High Vol)", [(150, 200)]),
        ("200 - 300 (Very High Vol)", [(200, 300)]),
        ("300 - 500 (Extreme Vol)", [(300, 500)]),
        ("500+ (Mega Trades)", [(500, 9999999)]),
        ("80-120 OR 200-300 (Dual Band)", [(80, 120), (200, 300)]),
    ]

    print("\nRunning High Sample Size analysis (No Day/Time restrictions)...")

    results_portfolio_high_n = []
    for label, vol_ranges in ranges_to_test:
        # Simulate with disabled time/day rules (allowing trading Mon-Fri, all standard sessions)
        t = simulate_portfolio(all_trades, relaxed_rules, vol_ranges, apply_filters=True, disable_time_rules=True)
        m = calculate_metrics(t)
        results_portfolio_high_n.append({"label": label, **m})

    print("\n--- HIGH SAMPLE SIZE RESULTS (All 4 setups, No Day/Time rules) ---")
    for r in results_portfolio_high_n:
        print(f"{r['label']:<30} | N={r['N']:<4} | WR={r['WR']:.1f}% | PF={r['PF']:.2f} | PnL=${r['PnL']:,.2f} | DD=${r['MaxDD']:,.2f}")

    # Write results to a json file
    output_path = Path(r"C:\Users\Mauro\Documents\nq-backtest\scratch\volume_high_n_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results_portfolio_high_n, f, indent=4)
    print(f"\nSaved raw high-N results to {output_path}")

if __name__ == "__main__":
    main()
