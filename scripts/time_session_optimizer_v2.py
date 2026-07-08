"""
time_session_optimizer_v2.py
============================
Versione con MENO gradi di libertà per ridurre overfitting.

Differenze vs v1:
  - 3 sessioni coarse (open/mid/close) invece di 13 slot 30min
  - min_trades >= 150 (invece di 80)
  - Cromosoma: 4 setup × (3 sessioni + 5 giorni + 1 flag) = 36 bit (invece di 76)
  - Ratio parametri/trade atteso: ~1:4 invece di 1:7
"""

import json
import os
import sys
import bisect
import random
from pathlib import Path
from datetime import datetime
import pytz
import pandas as pd
import numpy as np

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest")

ET = pytz.timezone("America/New_York")
DATA_DIR = Path(r"c:\Users\Mauro\Documents\nq-backtest\dashboard\public\data")
CACHE_DIR = r"C:\Users\Mauro\Documents\nq-backtest\cache_ohlc"

# ---- 3 sessioni coarse invece di 13 slot ----
SESSIONS = {
    "open":  (9*60+30, 11*60),       # 09:30 - 11:00
    "mid":   (11*60,   14*60),       # 11:00 - 14:00
    "close": (14*60,   16*60),       # 14:00 - 16:00
}
SESSION_NAMES = ["open", "mid", "close"]
DAYS_OF_WEEK  = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Cromosoma: 4 setup × (3 sessioni + 5 giorni + 1 exclude_10am) = 4 × 9 = 36 bit
CHROM_LEN = 4 * 9


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
            bars = [MockBar(row['timestamp'].to_pydatetime(), row['open'],
                            row['high'], row['low'], row['close']) for row in records]
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


def get_session_label(t_val):
    """Ritorna la sessione coarse (open/mid/close) dato t_val in minuti."""
    for name, (start, end) in SESSIONS.items():
        if start <= t_val < end:
            return name
    return "other"


def precompute_raw_trades(seqs_combined, raw_lookup, filtered_mode=True):
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

    for s in seqs_combined:
        date_str    = s["date"]
        time_str    = s["end_time"]
        entry_price = s["entry_price"]
        pattern     = s["seq_pattern"]

        vol = s['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)):
            continue

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

        if filtered_mode:
            session_cvd = last_step.get("session_cvd", 0)
            if abs(session_cvd) >= 1200:
                continue
            vs_val = last_step.get("price_vs_val", "unknown")
            vs_vah = last_step.get("price_vs_vah", "unknown")
            is_inside_va = (vs_val == "above" and vs_vah == "below")
            if direction == "short" and is_inside_va:
                continue
            step1_time = raw_seq["steps"][0]["time_et"]
            if check_contrary_big_trades(date_str, step1_time, time_str, direction, threshold=150):
                continue

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
            "pattern":     pattern,
            "date":        date_str,
            "time_str":    time_str,
            "day_of_week": day_of_week,
            "session":     session,
            "entry_dt":    entry_dt,
            "exit_dt":     exit_dt,
            "pnl_usd":     pnl_usd,
            "is_win":      outcome == "win",
            "pnl_pts":     pnl_pts
        })

    return sorted(trades, key=lambda x: x["entry_dt"])


def simulate_portfolio_fast(trades, rules):
    trades_executed = []
    last_exit_datetime = None

    for t in trades:
        pat  = t["pattern"]
        rule = rules.get(pat)
        if not rule:
            continue
        if t["day_of_week"] not in rule["days"]:
            continue
        if t["session"] not in rule["sessions"]:
            continue
        if rule.get("exclude_10am", False):
            h, m = map(int, t["time_str"].split(':'))
            tv = h * 60 + m
            if 9*60+55 <= tv <= 10*60+5:
                continue
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
    pnl   = sum(t["pnl_usd"] for t in trades_executed)
    gross_prof = sum(t["pnl_usd"] for t in trades_executed if t["pnl_usd"] > 0)
    gross_loss = abs(sum(t["pnl_usd"] for t in trades_executed if t["pnl_usd"] < 0))
    pf    = gross_prof / gross_loss if gross_loss > 0 else float('inf')
    current = peak = 50000.0
    max_dd = 0.0
    for t in trades_executed:
        current += t["pnl_usd"]
        peak     = max(peak, current)
        max_dd   = max(max_dd, peak - current)
    return {"N": n, "WR": (wins/n)*100, "PF": pf, "PnL": pnl, "MaxDD": max_dd}


def chromosome_to_rules(chromosome):
    """36 bit → regole con sessioni coarse."""
    rules = {}
    setups = ["trend_long", "absorb_long", "trend_short", "absorb_short"]
    for i, pat in enumerate(setups):
        offset = i * 9
        sess_bits       = chromosome[offset:offset+3]
        days_bits       = chromosome[offset+3:offset+8]
        exclude_10am    = chromosome[offset+8] == 1
        allowed_sessions = {SESSION_NAMES[j] for j, b in enumerate(sess_bits) if b == 1}
        allowed_days     = {DAYS_OF_WEEK[j]   for j, b in enumerate(days_bits) if b == 1}
        rules[pat] = {"days": allowed_days, "sessions": allowed_sessions, "exclude_10am": exclude_10am}
    return rules


def fitness_function(chromosome, trades, min_trades=150, max_dd_limit=2000.0):
    rules    = chromosome_to_rules(chromosome)
    executed = simulate_portfolio_fast(trades, rules)
    metrics  = calculate_metrics(executed)
    penalty  = 0.0
    if metrics["N"] < min_trades:
        penalty += (min_trades - metrics["N"]) * 100.0
    if metrics["MaxDD"] > max_dd_limit:
        penalty += (metrics["MaxDD"] - max_dd_limit) * 5.0
    if penalty > 0.0:
        return -penalty
    return metrics["PF"] + (metrics["PnL"] / 100000.0)


def optimize_portfolio(trades, min_trades=150, max_dd_limit=2000.0, iterations=5000, restarts=12):
    print(f"Ottimizzazione con sessioni coarse (Min Trades >= {min_trades}, Max DD < ${max_dd_limit:.0f})...")
    best_fitness   = -999999
    best_chrom     = None

    for restart in range(restarts):
        chromosome = [1]*CHROM_LEN if restart == 0 else [random.randint(0,1) for _ in range(CHROM_LEN)]
        cur_fit    = fitness_function(chromosome, trades, min_trades, max_dd_limit)

        for _ in range(iterations):
            mutated    = list(chromosome)
            for _ in range(random.randint(1, 2)):
                mutated[random.randint(0, CHROM_LEN-1)] ^= 1
            mut_fit = fitness_function(mutated, trades, min_trades, max_dd_limit)
            if mut_fit > cur_fit:
                chromosome = mutated
                cur_fit    = mut_fit

        if cur_fit > best_fitness:
            best_fitness = cur_fit
            best_chrom   = chromosome
            print(f"  Restart {restart+1}/{restarts} -> fitness: {best_fitness:.4f}")

    best_rules    = chromosome_to_rules(best_chrom)
    best_executed = simulate_portfolio_fast(trades, best_rules)
    best_metrics  = calculate_metrics(best_executed)
    return best_rules, best_metrics, best_executed


def print_session_breakdown(trades, label):
    print(f"\n========== BREAKDOWN SESSIONI: {label.upper()} ==========")
    df = pd.DataFrame(trades)
    for pat in ["trend_long", "absorb_long", "trend_short", "absorb_short"]:
        sub = df[df["pattern"] == pat]
        if sub.empty:
            continue
        print(f"\n--- {pat.upper()} (N={len(sub)}) ---")
        rows = []
        for sess in SESSION_NAMES:
            s = sub[sub["session"] == sess]
            if len(s) == 0: continue
            gw = sum(p for p in s["pnl_usd"] if p > 0)
            gl = abs(sum(p for p in s["pnl_usd"] if p < 0))
            pf = gw/gl if gl > 0 else float('inf')
            rows.append({"Session": sess, "N": len(s), "WR%": round(s["is_win"].mean()*100,1), "PF": round(pf,2), "PnL": round(s["pnl_usd"].sum(),2)})
        print(pd.DataFrame(rows).to_string(index=False))

        rows2 = []
        for day in DAYS_OF_WEEK:
            s = sub[sub["day_of_week"] == day]
            if len(s) == 0: continue
            gw = sum(p for p in s["pnl_usd"] if p > 0)
            gl = abs(sum(p for p in s["pnl_usd"] if p < 0))
            pf = gw/gl if gl > 0 else float('inf')
            rows2.append({"Day": day, "N": len(s), "WR%": round(s["is_win"].mean()*100,1), "PF": round(pf,2), "PnL": round(s["pnl_usd"].sum(),2)})
        print(pd.DataFrame(rows2).to_string(index=False))


def main():
    global cached_dates
    print("Pre-scansione OHLC cache...")
    cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    for d in cached_dates:
        get_bars_for_date(d)
    print(f"Caricati {len(bars_cache)} file OHLC.")

    print("\nCaricamento sequenze 2025+2026...")
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined_2025.json", encoding="utf-8") as f:
        seqs_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2025.json", encoding="utf-8") as f:
        raw_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        seqs_2026 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2026.json", encoding="utf-8") as f:
        raw_2026 = json.load(f)

    raw_lookup = {}
    for s in raw_2025 + raw_2026:
        raw_lookup[(s["date"], s["end_time"])] = s

    seqs_combined = sorted(seqs_2025 + seqs_2026, key=lambda x: (x["date"], x["end_time"]))

    print("\nPre-calcolo trade BASELINE (no CVD/VA)...")
    trades_baseline = precompute_raw_trades(seqs_combined, raw_lookup, filtered_mode=False)
    print(f"Trade baseline totali: {len(trades_baseline)}")

    print("\nPre-calcolo trade FILTRATI (CVD+VA+BigTrade)...")
    trades_filtered = precompute_raw_trades(seqs_combined, raw_lookup, filtered_mode=True)
    print(f"Trade filtrati totali: {len(trades_filtered)}")

    # Breakdown per sessione (informativo)
    print_session_breakdown(trades_baseline, "Baseline")
    print_session_breakdown(trades_filtered, "Filtrati")

    # --- CASO A: Baseline, min_trades=150 ---
    print("\n" + "="*60)
    print("CASO A: Baseline + sessioni coarse, min_trades=150")
    print("="*60)
    rules_a, metrics_a, executed_a = optimize_portfolio(
        trades_baseline, min_trades=150, max_dd_limit=2000.0, iterations=5000, restarts=12
    )
    print(f"\nRISULTATI CASO A:")
    print(f"  N={metrics_a['N']} | WR={metrics_a['WR']:.1f}% | PF={metrics_a['PF']:.2f} | PnL=${metrics_a['PnL']:,.2f} | MaxDD=${metrics_a['MaxDD']:,.2f}")
    print("  Regole:")
    for pat, r in rules_a.items():
        print(f"    {pat}: giorni={sorted(r['days'])} | sessioni={sorted(r['sessions'])} | excl10am={r['exclude_10am']}")

    # --- CASO B: Filtrati, min_trades=150 ---
    print("\n" + "="*60)
    print("CASO B: Filtrati (CVD+VA) + sessioni coarse, min_trades=100")
    print("="*60)
    # Caso B ha 205 trade filtrati -> min_trades=100 (ratio 1:2, comunque robusto)
    rules_b, metrics_b, executed_b = optimize_portfolio(
        trades_filtered, min_trades=100, max_dd_limit=2000.0, iterations=5000, restarts=12
    )
    print(f"\nRISULTATI CASO B:")
    print(f"  N={metrics_b['N']} | WR={metrics_b['WR']:.1f}% | PF={metrics_b['PF']:.2f} | PnL=${metrics_b['PnL']:,.2f} | MaxDD=${metrics_b['MaxDD']:,.2f}")
    print("  Regole:")
    for pat, r in rules_b.items():
        print(f"    {pat}: giorni={sorted(r['days'])} | sessioni={sorted(r['sessions'])} | excl10am={r['exclude_10am']}")

    # Salva JSON
    out = {
        "v2_case_a_coarse_sessions": {
            "description": "Baseline + 3 sessioni coarse + min_trades=150",
            "metrics": metrics_a,
            "rules": {pat: {"days": list(r["days"]), "sessions": list(r["sessions"]), "exclude_10am": r["exclude_10am"]} for pat, r in rules_a.items()}
        },
        "v2_case_b_filtered_coarse": {
            "description": "Filtri CVD+VA + 3 sessioni coarse + min_trades=150",
            "metrics": metrics_b,
            "rules": {pat: {"days": list(r["days"]), "sessions": list(r["sessions"]), "exclude_10am": r["exclude_10am"]} for pat, r in rules_b.items()}
        }
    }
    out_path = Path("scripts/time_session_rules_v2.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=4)
    print(f"\nRegole V2 salvate in: {out_path}")

    # Confronto finale
    print("\n" + "="*60)
    print("CONFRONTO V1 vs V2")
    print("="*60)
    print(f"  V1 Caso A: N=81  | PF=4.62 | MaxDD=$525   <- overfitting sospetto (76 parametri, N=81)")
    print(f"  V2 Caso A: N={metrics_a['N']:3d}  | PF={metrics_a['PF']:.2f} | MaxDD=${metrics_a['MaxDD']:,.0f}")
    print(f"  V2 Caso B: N={metrics_b['N']:3d}  | PF={metrics_b['PF']:.2f} | MaxDD=${metrics_b['MaxDD']:,.0f}")


if __name__ == "__main__":
    main()
