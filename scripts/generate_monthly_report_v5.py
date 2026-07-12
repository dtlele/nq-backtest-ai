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

sys.path.append(r"C:\Users\Mauro\Documents\nq-backtest-clean")

ET = pytz.timezone("America/New_York")
DATA_DIR = Path(r"C:\Users\Mauro\Documents\nq-backtest-clean\dashboard\public\data")
CACHE_DIR = r"C:\Users\Mauro\Documents\nq-backtest-clean\cache_ohlc"

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
    base_contracts = 1
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
            "pnl_usd_1c":     pnl_usd,         # 1 contract
            "pnl_usd_3c":     pnl_usd * 3,     # 3 contracts
            "is_win":         outcome == "win",
            "pnl_pts":        pnl_pts,
            "vol":            vol,
            "session_cvd":    session_cvd,
            "is_inside_va":   is_inside_va,
            "has_contrary":   has_contrary_150,
            "direction":      direction
        })

    return sorted(trades, key=lambda x: x["entry_dt"])

def simulate_portfolio(trades, rules, vol_ranges):
    trades_executed = []
    last_exit_datetime = None

    for t in trades:
        pat  = t["pattern"]
        rule = rules.get(pat)
        if not rule:
            continue
        
        # Volume Filter
        vol = t["vol"]
        in_range = any(min_v <= vol < max_v for min_v, max_v in vol_ranges)
        if not in_range:
            continue
            
        # Day of week (ALLOW MON-FRI for all)
        # Session Filter (Keep strict)
        if t["session"] not in rule["sessions"]:
            continue
            
        # Exclude 10 AM Economic News Release Block (09:55 - 10:05)
        if rule.get("exclude_10am", False):
            h, m = map(int, t["time_str"].split(':'))
            tv = h * 60 + m
            if 9*60+55 <= tv <= 10*60+5:
                continue
                
        # CVD Climax, Value Area, and Contrary Filters
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

def evaluate_metrics(df_trades, size_label="1c"):
    if df_trades.empty:
        return {"N": 0, "WR": 0.0, "PF": 0.0, "PnL": 0.0, "MaxDD": 0.0}
        
    pnl_col = "pnl_usd_1c" if size_label == "1c" else "pnl_usd_3c"
    
    n = len(df_trades)
    wins = sum(df_trades["is_win"])
    wr = (wins / n) * 100
    
    gross_prof = sum(p for p in df_trades[pnl_col] if p > 0)
    gross_loss = abs(sum(p for p in df_trades[pnl_col] if p < 0))
    pf = gross_prof / gross_loss if gross_loss > 0 else float("inf")
    pnl = df_trades[pnl_col].sum()
    
    peak = 50000.0
    current = 50000.0
    max_dd = 0.0
    for p in df_trades[pnl_col]:
        current += p
        peak = max(peak, current)
        max_dd = max(max_dd, peak - current)
        
    return {"N": n, "WR": wr, "PF": pf, "PnL": pnl, "MaxDD": max_dd}

def get_monthly_breakdown(df_trades, size_label="1c"):
    if df_trades.empty:
        return {}
    pnl_col = "pnl_usd_1c" if size_label == "1c" else "pnl_usd_3c"
    months = sorted(df_trades["month"].unique())
    monthly_stats = {}
    for m in months:
        m_df = df_trades[df_trades["month"] == m]
        metrics = evaluate_metrics(m_df, size_label)
        monthly_stats[m] = metrics
    return monthly_stats

def main():
    global cached_dates
    print("Pre-scanning cache dates...")
    cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    for d in cached_dates:
        get_bars_for_date(d)

    print("Loading sequence files...")
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

    all_trades = precompute_all_trades_no_filter(seqs_combined, raw_lookup)

    # Relaxed rules: all setups enabled on all days of the week, but keeping the coarse sessions
    relaxed_rules = {
        "trend_long": {
            "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "sessions": ["open"],
            "exclude_10am": False
        },
        "absorb_long": {
            "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "sessions": ["mid", "open"],
            "exclude_10am": True
        },
        "trend_short": {
            "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "sessions": ["close"],
            "exclude_10am": False
        },
        "absorb_short": {
            "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "sessions": ["open"],
            "exclude_10am": True
        }
    }

    # Run Option 1: 80 - 120 (Optimal Medium)
    trades_opt1 = simulate_portfolio(all_trades, relaxed_rules, [(80, 121)])
    df_opt1 = pd.DataFrame(trades_opt1)
    df_opt1["month"] = df_opt1["date"].apply(lambda x: f"{x[:4]}-{x[4:6]}")

    # Run Option 2: 80 - 120 OR 200 - 300 (Dual Band)
    trades_opt2 = simulate_portfolio(all_trades, relaxed_rules, [(80, 121), (200, 301)])
    df_opt2 = pd.DataFrame(trades_opt2)
    df_opt2["month"] = df_opt2["date"].apply(lambda x: f"{x[:4]}-{x[4:6]}")

    # Compute overall metrics
    m1_1c = evaluate_metrics(df_opt1, "1c")
    m1_3c = evaluate_metrics(df_opt1, "3c")
    m2_1c = evaluate_metrics(df_opt2, "1c")
    m2_3c = evaluate_metrics(df_opt2, "3c")

    # Compute monthly breakdowns
    monthly_opt1_1c = get_monthly_breakdown(df_opt1, "1c")
    monthly_opt2_1c = get_monthly_breakdown(df_opt2, "1c")
    
    monthly_opt1_3c = get_monthly_breakdown(df_opt1, "3c")
    monthly_opt2_3c = get_monthly_breakdown(df_opt2, "3c")

    # Combine all months
    all_months = sorted(list(set(df_opt1["month"].unique()) | set(df_opt2["month"].unique())))

    # Format values for neat alignment in print
    wr1_str = f"{m1_1c['WR']:.1f}%"
    wr2_str = f"{m2_1c['WR']:.1f}%"
    pf1_str = f"{m1_1c['PF']:.2f}"
    pf2_str = f"{m2_1c['PF']:.2f}"
    
    p1c_1 = f"${m1_1c['PnL']:,.2f}"
    p1c_2 = f"${m2_1c['PnL']:,.2f}"
    dd1_1 = f"${m1_1c['MaxDD']:,.2f}"
    dd1_2 = f"${m2_1c['MaxDD']:,.2f}"
    
    p3c_1 = f"${m1_3c['PnL']:,.2f}"
    p3c_2 = f"${m2_3c['PnL']:,.2f}"
    dd3_1 = f"${m1_3c['MaxDD']:,.2f}"
    dd3_2 = f"${m2_3c['MaxDD']:,.2f}"

    # Generate MD and print
    print("\n" + "="*85)
    print("      CONFRONTO STATISTICHE (NO FILTRI GIORNO, SOLO FILTRI ORARI E MICROSTRUTTURA)")
    print("="*85)
    print(f"{'Metrica':<30} | {'Opzione 1 (80-120)':<25} | {'Opzione 2 (80-120 OR 200-300)':<25}")
    print("-"*85)
    print(f"{'Trade Eseguiti (N)':<30} | {m1_1c['N']:<25} | {m2_1c['N']:<25}")
    print(f"{'Win Rate (%)':<30} | {wr1_str:<25} | {wr2_str:<25}")
    print(f"{'Profit Factor (PF)':<30} | {pf1_str:<25} | {pf2_str:<25}")
    print("-"*85)
    print(f"{'PnL Netto (1 Contratto MNQ)':<30} | {p1c_1:<25} | {p1c_2:<25}")
    print(f"{'Max Drawdown (1 Contr. MNQ)':<30} | {dd1_1:<25} | {dd1_2:<25}")
    print("-"*85)
    print(f"{'PnL Netto (3 Contratti MNQ)':<30} | {p3c_1:<25} | {p3c_2:<25}")
    print(f"{'Max Drawdown (3 Contr. MNQ)':<30} | {dd3_1:<25} | {dd3_2:<25}")
    print("="*85)

    print("\nCONFRONTO MENSILE (PnL con 1 Contratto MNQ):")
    print(f"{'Mese':<10} | {'Opz. 1: N':<9} | {'Opz. 1: PnL':<13} | {'Opz. 2: N':<9} | {'Opz. 2: PnL':<13}")
    print("-"*65)
    for m in all_months:
        op1_n = monthly_opt1_1c.get(m, {}).get("N", 0)
        op1_pnl = monthly_opt1_1c.get(m, {}).get("PnL", 0.0)
        op2_n = monthly_opt2_1c.get(m, {}).get("N", 0)
        op2_pnl = monthly_opt2_1c.get(m, {}).get("PnL", 0.0)
        op1_pnl_str = f"${op1_pnl:,.2f}"
        op2_pnl_str = f"${op2_pnl:,.2f}"
        print(f"{m:<10} | {op1_n:<9} | {op1_pnl_str:<13} | {op2_n:<9} | {op2_pnl_str:<13}")
    print("="*85)

    print("\nCONFRONTO MENSILE (PnL con 3 Contratti MNQ):")
    print(f"{'Mese':<10} | {'Opz. 1: N':<9} | {'Opz. 1: PnL':<13} | {'Opz. 2: N':<9} | {'Opz. 2: PnL':<13}")
    print("-"*65)
    for m in all_months:
        op1_n = monthly_opt1_3c.get(m, {}).get("N", 0)
        op1_pnl = monthly_opt1_3c.get(m, {}).get("PnL", 0.0)
        op2_n = monthly_opt2_3c.get(m, {}).get("N", 0)
        op2_pnl = monthly_opt2_3c.get(m, {}).get("PnL", 0.0)
        op1_pnl_str = f"${op1_pnl:,.2f}"
        op2_pnl_str = f"${op2_pnl:,.2f}"
        print(f"{m:<10} | {op1_n:<9} | {op1_pnl_str:<13} | {op2_n:<9} | {op2_pnl_str:<13}")
    print("="*85)

    print("\nCONFRONTO DETTAGLIO PER SETUP (Sizing 1 Contratto):")
    for pat in ["trend_long", "absorb_long", "trend_short", "absorb_short"]:
        # Option 1
        s_df1 = df_opt1[df_opt1["pattern"] == pat]
        n1 = len(s_df1)
        wr1 = (sum(s_df1["is_win"]) / n1 * 100) if n1 > 0 else 0.0
        pnl1 = s_df1["pnl_usd_1c"].sum() if n1 > 0 else 0.0
        
        # Option 2
        s_df2 = df_opt2[df_opt2["pattern"] == pat]
        n2 = len(s_df2)
        wr2 = (sum(s_df2["is_win"]) / n2 * 100) if n2 > 0 else 0.0
        pnl2 = s_df2["pnl_usd_1c"].sum() if n2 > 0 else 0.0
        
        print(f"Setup {pat.upper():<12}:")
        print(f"  - Opzione 1 (80-120):      N={n1:<3} | WR={wr1:5.1f}% | PnL=${pnl1:8,.2f}")
        print(f"  - Opzione 2 (Dual Band):   N={n2:<3} | WR={wr2:5.1f}% | PnL=${pnl2:8,.2f}")
    print("="*85 + "\n")

    # Save to a JSON file
    output_path = Path(r"C:\Users\Mauro\Documents\nq-backtest-clean\scratch\monthly_comparison_no_day_filter.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "option1": {
                "overall_1c": m1_1c,
                "overall_3c": m1_3c,
                "monthly_1c": monthly_opt1_1c
            },
            "option2": {
                "overall_1c": m2_1c,
                "overall_3c": m2_3c,
                "monthly_1c": monthly_opt2_1c
            }
        }, f, indent=4)

if __name__ == "__main__":
    main()

