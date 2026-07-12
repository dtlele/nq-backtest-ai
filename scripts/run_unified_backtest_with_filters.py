import json
import os
import sys
import bisect
from pathlib import Path
from datetime import datetime
import pytz
import pandas as pd
import numpy as np

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest-clean")

ET = pytz.timezone("America/New_York")
DATA_DIR = Path(r"c:\Users\Mauro\Documents\nq-backtest-clean\dashboard\public\data")
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
        except Exception as e:
            pass
    return None

def compute_5day_atr(date_str):
    """Compute 5-day historical ATR using cached_dates (in-memory binary search)."""
    # Find index of first date >= date_str
    idx = bisect.bisect_left(cached_dates, date_str)
    # Get previous 5 dates
    prev_dates = cached_dates[max(0, idx - 5):idx]
    if len(prev_dates) < 5:
        return 180.0
        
    ranges = []
    for d in prev_dates:
        bars = get_bars_for_date(d)
        if bars:
            r_high = max(b.high for b in bars)
            r_low = min(b.low for b in bars)
            ranges.append(r_high - r_low)
            
    if len(ranges) >= 3:
        return np.mean(ranges)
    return 180.0

def get_prior_mega_levels(date_str, seq_end_time, min_size=300):
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    day_file = DATA_DIR / f"{formatted_date}.json"
    levels = []
    if day_file.exists():
        try:
            with open(day_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                big_trades = data.get("big_trades", [])
                
                eh, em = map(int, seq_end_time.split(':'))
                seq_end_mins = eh * 60 + em
                
                for t in big_trades:
                    if t.get("size", 0) >= min_size:
                        dt = datetime.fromtimestamp(t["time"], tz=pytz.utc).astimezone(ET)
                        trade_mins = dt.hour * 60 + dt.minute
                        if trade_mins < seq_end_mins:
                            levels.append(t["price"])
        except:
            pass
    return levels

big_trades_cache = {}

def check_contrary_big_trades(date_str, step1_time_str, end_time_str, direction, threshold=150):
    global big_trades_cache
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    if date_str not in big_trades_cache:
        day_file = DATA_DIR / f"{formatted_date}.json"
        if day_file.exists():
            try:
                with open(day_file, "r", encoding="utf-8") as f:
                    day_data = json.load(f)
                big_trades_cache[date_str] = day_data.get("big_trades", [])
            except:
                big_trades_cache[date_str] = []
        else:
            big_trades_cache[date_str] = []
            
    big_trades = big_trades_cache[date_str]
    if not big_trades:
        return False
        
    try:
        dt_start = datetime.strptime(f"{date_str} {step1_time_str}", "%Y%m%d %H:%M")
        dt_start = ET.localize(dt_start)
        start_ts = int(dt_start.timestamp())
        
        dt_end = datetime.strptime(f"{date_str} {end_time_str}", "%Y%m%d %H:%M")
        dt_end = ET.localize(dt_end)
        end_ts = int(dt_end.timestamp())
        
        contrary_side = 'B' if direction == "long" else 'A'
        
        for bt in big_trades:
            if start_ts <= bt["time"] <= end_ts:
                if bt["side"] == contrary_side and bt["size"] >= threshold:
                    return True
    except Exception as e:
        pass
    return False

def run_simulation(seqs_combined, raw_lookup, scenario="all_filters", atr_threshold=200.0, size_scaling=False):
    # Setup parameters by volatility regime
    low_vol_setups = {
        "trend_long": {"direction": "long", "sl": 39.0, "tp": 120.0},
        "absorb_long": {"direction": "long", "sl": 49.0, "tp": 37.0},
        "trend_short": {"direction": "short", "sl": 46.0, "tp": 120.0},
        "absorb_short": {"direction": "short", "sl": 49.0, "tp": 114.0}
    }
    high_vol_setups = {
        "trend_long": {"direction": "long", "sl": 22.0, "tp": 113.0},
        "absorb_long": {"direction": "long", "sl": 50.0, "tp": 115.0},
        "trend_short": {"direction": "short", "sl": 48.0, "tp": 113.0},
        "absorb_short": {"direction": "short", "sl": 34.0, "tp": 35.0}
    }

    trades_executed = []
    last_exit_datetime = None
    
    # MNQ contract settings
    base_contracts = 3
    point_value = 2.0
    commission = 0.50
    equity = 50000.0
    
    for s in seqs_combined:
        date_str = s["date"]
        time_str = s["end_time"]
        entry_price = s["entry_price"]
        pattern = s["seq_pattern"]
        
        # Determine setup parameters based on dynamic ATR
        atr = compute_5day_atr(date_str)
        if atr < atr_threshold:
            setup_info = low_vol_setups.get(pattern)
            regime_label = "LOW"
        else:
            setup_info = high_vol_setups.get(pattern)
            regime_label = "HIGH"
            
        if not setup_info:
            continue
            
        direction = setup_info["direction"]
        sl = setup_info["sl"]
        tp = setup_info["tp"]
        
        # ── 1. Volume & Time Filters ──────────────────────────────────────────
        vol = s['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)):
            continue
            
        time_parts = time_str.split(':')
        h, m = int(time_parts[0]), int(time_parts[1])
        t_val = h * 60 + m
        is_morning = (9 * 60 + 30 <= t_val < 11 * 60)
        is_lunch_core = (12 * 60 + 30 <= t_val < 13 * 60 + 30)
        is_afternoon = (14 * 60 + 30 <= t_val < 15 * 60 + 30) # A_Start=14:30
        
        # Filtro orario: gli scenari 'no_lunch' ed 'optimized' escludono il pranzo
        if "no_lunch" in scenario or "optimized" in scenario:
            if not (is_morning or is_afternoon):
                continue
        else:
            if not (is_morning or is_lunch_core or is_afternoon):
                continue
            
        # ── 2. CVD Climax Filter ──────────────────────────────────────────────
        raw_seq = raw_lookup.get((date_str, time_str))
        if not raw_seq or not raw_seq.get("steps"):
            continue
            
        last_step = raw_seq["steps"][-1]
        session_cvd = last_step.get("session_cvd", 0)
        
        # CVD Climax
        if "cvd" in scenario or scenario in ["va_cvd_filters", "all_filters", "all_filters_optimized"]:
            if "no_cvd" not in scenario:
                if abs(session_cvd) >= 2000:  # Ottimizzato a 2000
                    continue
                
        # ── 3. Value Area Exclusion Filter ────────────────────────────────────
        vs_val = last_step.get("price_vs_val", "unknown")
        vs_vah = last_step.get("price_vs_vah", "unknown")
        is_inside_va = (vs_val == "above" and vs_vah == "below")
        
        # Filtro VA attivo in tutti gli scenari tranne la baseline
        if scenario != "baseline":
            # Block SHORT trades inside VA
            if direction == "short" and is_inside_va:
                continue
                
        # ── 4. Contrary Big Trade Filter (Soglia >= 250) ──────────────────────
        if "contrary" in scenario or "optimized" in scenario:
            step1_time = raw_seq["steps"][0]["time_et"]
            if check_contrary_big_trades(date_str, step1_time, time_str, direction, threshold=250): # Ottimizzato a 250
                continue
                
        # ── 5. Mega Trade Proximity Filter ────────────────────────────────────
        is_near_mega = False
        if scenario in ["all_filters", "all_filters_optimized"] or size_scaling:
            prior_megas = get_prior_mega_levels(date_str, time_str, min_size=300)
            if prior_megas:
                min_dist = min(abs(entry_price - p) for p in prior_megas)
                is_near_mega = (min_dist <= 15.0)
                
            if size_scaling and "absorb" in pattern:
                if not is_near_mega:
                    continue
                    
        # Concurrency check
        entry_dt = pd.to_datetime(date_str + ' ' + time_str, format='%Y%m%d %H:%M')
        entry_dt = ET.localize(entry_dt)
        if last_exit_datetime is not None and entry_dt < last_exit_datetime:
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
                
            high = bar.high
            low = bar.low
            if direction == "long":
                if low <= entry_price - sl:
                    pnl_pts = -sl
                    outcome = "loss"
                    exit_time_str = t_et.strftime("%H:%M")
                    break
                elif high >= entry_price + tp + 0.25:
                    pnl_pts = tp
                    outcome = "win"
                    exit_time_str = t_et.strftime("%H:%M")
                    break
            else:
                if high >= entry_price + sl:
                    pnl_pts = -sl
                    outcome = "loss"
                    exit_time_str = t_et.strftime("%H:%M")
                    break
                elif low <= entry_price - tp - 0.25:
                    pnl_pts = tp
                    outcome = "win"
                    exit_time_str = t_et.strftime("%H:%M")
                    break
                    
        if outcome is None:
            last_bar = bars[-1]
            t_et = last_bar.timestamp.astimezone(ET)
            outcome = "eod"
            exit_price = last_bar.close
            pnl_pts = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
            exit_time_str = t_et.strftime("%H:%M")
            
        pnl_pts = pnl_pts - 1.5  # slippage
        
        # CFD Dynamic Risk Sizing: Rischio fisso in percentuale (es. 0.20%)
        # contracts = (equity * RISK_PCT) / (sl * point_value)
        # Arrotondato a 2 cifre decimali (lotti/microlotti su MT5 CFD)
        risk_pct = 0.0120  # 1.20% del capitale
        contracts = round((equity * risk_pct) / (sl * point_value), 2)
        if contracts < 0.01:
            contracts = 0.01
            
        pnl_usd = ((pnl_pts * point_value) - commission) * contracts
        equity += pnl_usd
        
        trades_executed.append({
            "date": date_str,
            "pnl_pts": pnl_pts,
            "pnl_usd": pnl_usd,
            "is_win": outcome == "win",
            "regime": regime_label,
            "atr": atr,
            "pattern": pattern
        })
        
        exit_dt = pd.to_datetime(date_str + ' ' + exit_time_str, format='%Y%m%d %H:%M')
        exit_dt = ET.localize(exit_dt)
        if exit_dt < entry_dt:
            exit_dt = exit_dt + pd.Timedelta(days=1)
        last_exit_datetime = exit_dt
        
    df_trades = pd.DataFrame(trades_executed)
    return df_trades

def print_scenario_report(df_trades, label):
    if df_trades.empty:
        print(f"Scenario {label} produced 0 trades.")
        return
        
    total_trades = len(df_trades)
    wins = sum(df_trades["is_win"])
    wr = (wins / total_trades) * 100
    net_pnl = df_trades["pnl_usd"].sum()
    avg_pnl = df_trades["pnl_usd"].mean()
    
    gross_prof = sum(p for p in df_trades["pnl_usd"] if p > 0)
    gross_loss = abs(sum(p for p in df_trades["pnl_usd"] if p < 0))
    pf = gross_prof / gross_loss if gross_loss > 0 else float('inf')
    
    peak = 50000.0
    current = 50000.0
    max_dd = 0.0
    for p in df_trades["pnl_usd"]:
        current += p
        peak = max(peak, current)
        max_dd = max(max_dd, peak - current)
        
    print(f"\n=================== REPORT SCENARIO: {label.upper()} ===================")
    print(f"  Trade Eseguiti:     {total_trades}")
    print(f"  Win Rate:           {wr:.1f}%")
    print(f"  Profit Factor:      {pf:.2f}")
    print(f"  Net P&L (USD):      ${net_pnl:,.2f}")
    print(f"  Avg Trade P&L:      ${avg_pnl:,.2f}")
    print(f"  Max Drawdown (USD): ${max_dd:,.2f}")
    
    print("\n  Dettaglio per Setup:")
    for pat in ["trend_long", "absorb_long", "trend_short", "absorb_short"]:
        sub = df_trades[df_trades["pattern"] == pat]
        n_sub = len(sub)
        if n_sub == 0:
            continue
        s_wins = sum(sub["is_win"])
        s_wr = (s_wins / n_sub) * 100
        s_pnl = sub["pnl_usd"].sum()
        s_gross_w = sum(p for p in sub["pnl_usd"] if p > 0)
        s_gross_l = abs(sum(p for p in sub["pnl_usd"] if p < 0))
        s_pf = s_gross_w / s_gross_l if s_gross_l > 0 else float('inf')
        print(f"    - Setup {pat.upper():<12} | N={n_sub:<3} | WR={s_wr:5.1f}% | PF={s_pf:4.2f} | PnL=${s_pnl:8,.2f}")

def main():
    global cached_dates
    print("Pre-scansione file OHLC e caching della struttura date...")
    cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    
    # Pre-load all bars into memory cache (Disabled for speed when running on a single month)
    # for d in cached_dates:
    #     get_bars_for_date(d)
    print("Caching delle date completato. I file verranno caricati on-demand.")

    print("\nCaricamento sequenze storiche (2025 + 2026)...")
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
        
    # Filter sequences specifically from January 2025 to November 2025
    seqs_combined = seqs_combined_2025 + seqs_combined_2026
    seqs_combined = [s for s in seqs_combined if "20250101" <= s["date"] <= "20251130"]
    seqs_combined = sorted(seqs_combined, key=lambda x: (x["date"], x["end_time"]))
    
    print(f"\nAvvio simulazioni su {len(seqs_combined)} sequenze (1 Anno)...")
    
    # Eseguiamo con tutti i filtri ottimali calcolati
    df_opt = run_simulation(seqs_combined, raw_lookup, scenario="all_filters_optimized")
    print_scenario_report(df_opt, "TRIPLE A TRAP OPTIMIZED (1 ANNO)")

if __name__ == "__main__":
    main()

