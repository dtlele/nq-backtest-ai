import json
import os
import sys
import bisect
from pathlib import Path
from datetime import datetime
import pytz
import pandas as pd
import numpy as np

# Add project root to sys.path
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

daily_range_cache = {}
def get_daily_range(date_str):
    if date_str in daily_range_cache:
        return daily_range_cache[date_str]
    cache_file = Path(CACHE_DIR) / f"{date_str}.csv"
    if cache_file.exists():
        try:
            df = pd.read_csv(cache_file, usecols=['high', 'low'])
            r_high = df['high'].max()
            r_low = df['low'].min()
            val = float(r_high - r_low)
            daily_range_cache[date_str] = val
            return val
        except Exception:
            pass
    daily_range_cache[date_str] = 180.0
    return 180.0

atr_5day_cache = {}
def compute_5day_atr(date_str):
    if date_str in atr_5day_cache:
        return atr_5day_cache[date_str]
    idx = bisect.bisect_left(cached_dates, date_str)
    prev_dates = cached_dates[max(0, idx - 5):idx]
    if len(prev_dates) < 5:
        atr_5day_cache[date_str] = 180.0
        return 180.0
    ranges = [get_daily_range(d) for d in prev_dates]
    val = float(np.mean(ranges))
    atr_5day_cache[date_str] = val
    return val

atr_1day_cache = {}
def compute_1day_atr(date_str):
    if date_str in atr_1day_cache:
        return atr_1day_cache[date_str]
    idx = bisect.bisect_left(cached_dates, date_str)
    if idx == 0:
        atr_1day_cache[date_str] = 180.0
        return 180.0
    prev_date = cached_dates[idx - 1]
    val = get_daily_range(prev_date)
    atr_1day_cache[date_str] = val
    return val

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
    except Exception:
        pass
    return False

def get_prior_mega_levels(date_str, seq_end_time, min_size=300):
    global big_trades_cache
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
    levels = []
    if big_trades:
        try:
            eh, em = map(int, seq_end_time.split(':'))
            seq_end_mins = eh * 60 + em
            
            for t in big_trades:
                if t.get("size", 0) >= min_size:
                    dt = datetime.fromtimestamp(t["time"], tz=pytz.utc).astimezone(ET)
                    trade_mins = dt.hour * 60 + dt.minute
                    if trade_mins < seq_end_mins:
                        levels.append(t["price"])
        except Exception:
            pass
    return levels

# Base average parameters
base_setups_avg = {
    "trend_long": {"direction": "long", "sl": 30.5, "tp": 116.5},
    "absorb_long": {"direction": "long", "sl": 49.5, "tp": 76.0},
    "trend_short": {"direction": "short", "sl": 47.0, "tp": 116.5},
    "absorb_short": {"direction": "short", "sl": 41.5, "tp": 74.5}
}

# Static parameters for Low/High regimes
low_vol_setups_static = {
    "trend_long": {"direction": "long", "sl": 39.0, "tp": 120.0},
    "absorb_long": {"direction": "long", "sl": 49.0, "tp": 37.0},
    "trend_short": {"direction": "short", "sl": 46.0, "tp": 120.0},
    "absorb_short": {"direction": "short", "sl": 49.0, "tp": 114.0}
}
high_vol_setups_static = {
    "trend_long": {"direction": "long", "sl": 22.0, "tp": 113.0},
    "absorb_long": {"direction": "long", "sl": 50.0, "tp": 115.0},
    "trend_short": {"direction": "short", "sl": 48.0, "tp": 113.0},
    "absorb_short": {"direction": "short", "sl": 34.0, "tp": 35.0}
}

def simulate_backtest(
    seqs_precomputed,
    atr_type="5-day",
    scaling_mode="proportional", # "static", "proportional", "proportional_mult"
    atr_threshold=180.0,         # for static LOW/HIGH
    t_low_trend=0.0,             # disable Trend if ATR < t_low_trend
    t_high_absorb=999.0,         # disable Absorption if ATR >= t_high_absorb
    scaling_multiplier=1.0,      # global multiplier for SL/TP proportional
    use_contrary_filter=False,
    exclude_lunch=False,
    use_mega_proximity=True,
    base_contracts_trend=3,
    base_contracts_absorb=3,
    size_scaling_absorb=False
):
    trades_executed = []
    last_exit_datetime = None
    point_value = 2.0
    commission = 0.50
    equity = 50000.0

    for s in seqs_precomputed:
        pattern = s["seq_pattern"]
        atr = s["atr_5day"] if atr_type == "5-day" else s["atr_1day"]
        
        # Volatility toggles
        is_trend = "trend" in pattern
        is_absorb = "absorb" in pattern
        
        if is_trend and atr < t_low_trend:
            continue
        if is_absorb and atr >= t_high_absorb:
            continue
            
        # Determine SL/TP
        if scaling_mode == "static":
            if atr < atr_threshold:
                setup_info = low_vol_setups_static.get(pattern)
            else:
                setup_info = high_vol_setups_static.get(pattern)
            if not setup_info: continue
            sl = setup_info["sl"]
            tp = setup_info["tp"]
            direction = setup_info["direction"]
        elif scaling_mode == "proportional":
            setup_info = base_setups_avg.get(pattern)
            if not setup_info: continue
            direction = setup_info["direction"]
            ratio = atr / 180.0
            sl = max(5.0, setup_info["sl"] * ratio)
            tp = max(10.0, setup_info["tp"] * ratio)
        elif scaling_mode == "proportional_mult":
            setup_info = base_setups_avg.get(pattern)
            if not setup_info: continue
            direction = setup_info["direction"]
            ratio = (atr / 180.0) * scaling_multiplier
            sl = max(5.0, setup_info["sl"] * ratio)
            tp = max(10.0, setup_info["tp"] * ratio)
        else:
            continue

        # ── 1. Volume & Time Filters ──────────────────────────────────────────
        vol = s['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)):
            continue
            
        t_val = s["t_val"]
        is_morning = (9 * 60 + 30 <= t_val < 11 * 60)
        is_lunch_core = (12 * 60 + 30 <= t_val < 13 * 60 + 30)
        is_afternoon = (14 * 60 <= t_val < 15 * 60 + 30)
        
        if exclude_lunch:
            if not (is_morning or is_afternoon):
                continue
        else:
            if not (is_morning or is_lunch_core or is_afternoon):
                continue
                
        # ── 2. CVD Climax Filter ──────────────────────────────────────────────
        if s["session_cvd_abs"] >= 1200:
            continue
            
        # ── 3. Value Area Exclusion Filter ────────────────────────────────────
        if direction == "short" and s["is_inside_va"]:
            continue
            
        # ── 4. Contrary Big Trade Filter ──────────────────────────────────────
        if use_contrary_filter and s["has_contrary_big_trade"]:
            continue
                
        # ── 5. Mega Trade Proximity Filter ────────────────────────────────────
        is_near_mega = s["is_near_mega"]
        if use_mega_proximity and is_absorb:
            if not is_near_mega:
                continue

        # Concurrency check
        entry_dt = s["entry_dt"]
        if last_exit_datetime is not None and entry_dt < last_exit_datetime:
            continue
            
        bars = s["bars"]
        entry_idx = s["entry_idx"]
        if entry_idx == -1 or entry_idx >= len(bars):
            continue
            
        # ── MODELLO DI INGRESSO CLOSE (CORRETTO SENZA LOOKAHEAD BIAS) ─────────
        entry_price = bars[entry_idx].close
        
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
        
        # Position sizing
        if is_trend:
            contracts = base_contracts_trend
        else:
            if size_scaling_absorb:
                contracts = 5 if is_near_mega else 1
            else:
                contracts = base_contracts_absorb
                
        pnl_usd = ((pnl_pts * point_value) - commission) * contracts
        equity += pnl_usd
        
        exit_dt = pd.to_datetime(s["date"] + ' ' + exit_time_str, format='%Y%m%d %H:%M')
        exit_dt = ET.localize(exit_dt)
        if exit_dt < entry_dt:
            exit_dt = exit_dt + pd.Timedelta(days=1)
        last_exit_datetime = exit_dt
        
        trades_executed.append({
            "pnl_usd": pnl_usd,
            "is_win": outcome == "win"
        })

    if not trades_executed:
        return 0, 0.0, 0.0, 0.0, 0.0
        
    total_trades = len(trades_executed)
    wins = sum(1 for t in trades_executed if t["is_win"])
    wr = (wins / total_trades) * 100
    net_pnl = sum(t["pnl_usd"] for t in trades_executed)
    
    gross_prof = sum(t["pnl_usd"] for t in trades_executed if t["pnl_usd"] > 0)
    gross_loss = abs(sum(t["pnl_usd"] for t in trades_executed if t["pnl_usd"] < 0))
    pf = gross_prof / gross_loss if gross_loss > 0 else float('inf')
    
    peak = 50000.0
    current = 50000.0
    max_dd = 0.0
    for t in trades_executed:
        current += t["pnl_usd"]
        peak = max(peak, current)
        max_dd = max(max_dd, peak - current)
        
    return total_trades, wr, pf, net_pnl, max_dd

def main():
    global cached_dates
    print("Pre-scansione file OHLC e caching della struttura date...")
    cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    
    # Le barre verranno caricate lazily on-demand.
    print("Inizializzazione date completata. Le barre verranno caricate on-demand.")

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
        
    seqs_combined = seqs_combined_2025 + seqs_combined_2026
    seqs_combined = sorted(seqs_combined, key=lambda x: (x["date"], x["end_time"]))
    
    # Precalcolo statico per le sequenze
    print("Precalcolo filtri statici e indici per velocizzare la griglia...")
    seqs_precomputed = []
    
    for s in seqs_combined:
        date_str = s["date"]
        time_str = s["end_time"]
        entry_price = s["entry_price"]
        pattern = s["seq_pattern"]
        
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
            
        # Parse entry_dt
        entry_dt = pd.to_datetime(date_str + ' ' + time_str, format='%Y%m%d %H:%M')
        entry_dt = ET.localize(entry_dt)
        
        # Volume info
        vol = s['entry_vol']
        time_parts = time_str.split(':')
        h, m = int(time_parts[0]), int(time_parts[1])
        t_val = h * 60 + m
        
        # CVD Climax info
        raw_seq = raw_lookup.get((date_str, time_str))
        if not raw_seq or not raw_seq.get("steps"):
            continue
        last_step = raw_seq["steps"][-1]
        session_cvd_abs = abs(last_step.get("session_cvd", 0))
        
        # Value Area info
        vs_val = last_step.get("price_vs_val", "unknown")
        vs_vah = last_step.get("price_vs_vah", "unknown")
        is_inside_va = (vs_val == "above" and vs_vah == "below")
        
        # ATR Info
        atr_5d = compute_5day_atr(date_str)
        atr_1d = compute_1day_atr(date_str)
        
        # Contrary Big Trades info
        direction = "long" if "long" in pattern else "short"
        step1_time = raw_seq["steps"][0]["time_et"]
        has_contrary = check_contrary_big_trades(date_str, step1_time, time_str, direction, threshold=150)
        
        # Mega Levels proximity info
        prior_megas = get_prior_mega_levels(date_str, time_str, min_size=300)
        is_near_mega = False
        if prior_megas:
            min_dist = min(abs(entry_price - p) for p in prior_megas)
            is_near_mega = (min_dist <= 15.0)
            
        seqs_precomputed.append({
            "seq_pattern": pattern,
            "entry_vol": vol,
            "t_val": t_val,
            "session_cvd_abs": session_cvd_abs,
            "is_inside_va": is_inside_va,
            "atr_5day": atr_5d,
            "atr_1day": atr_1d,
            "has_contrary_big_trade": has_contrary,
            "is_near_mega": is_near_mega,
            "entry_dt": entry_dt,
            "bars": bars,
            "entry_idx": entry_idx,
            "date": date_str
        })
        
    print(f"Precalcolo completato per {len(seqs_precomputed)} sequenze.")
    print("Avvio simulazioni di ottimizzazione (griglia di regime)...")
    
    # Optimization parameters (COMPACT GRID to keep CPU cool and run instantly)
    atr_types = ["5-day"]
    scaling_modes = ["static", "proportional"]
    t_low_trend_vals = [0.0, 120.0, 160.0, 200.0]
    t_high_absorb_vals = [200.0, 240.0, 280.0, 999.0]
    scaling_multipliers = [1.0]
    exclude_lunch_vals = [True]
    use_contrary_filter_vals = [True, False]
    use_mega_proximity_vals = [True, False]
    
    contract_options = [
        (2, 3), # Safe size (2 Mini Trend, 3 Mini Absorb)
        (3, 3)  # Standard size
    ]
    
    best_results = []
    count = 0
    
    for atr_type in atr_types:
        for scaling_mode in scaling_modes:
            atr_thresholds = [180.0, 200.0] if scaling_mode == "static" else [180.0]
            for atr_thresh in atr_thresholds:
                for t_low_trend in t_low_trend_vals:
                    for t_high_absorb in t_high_absorb_vals:
                        if t_low_trend >= t_high_absorb:
                            continue
                        mults = scaling_multipliers if scaling_mode == "proportional_mult" else [1.0]
                        for mult in mults:
                            for ex_lunch in exclude_lunch_vals:
                                for use_contrary in use_contrary_filter_vals:
                                    for use_mega in use_mega_proximity_vals:
                                        for c_trend, c_absorb in contract_options:
                                            
                                            n_trades, wr, pf, net, dd = simulate_backtest(
                                                seqs_precomputed,
                                                atr_type=atr_type,
                                                scaling_mode=scaling_mode,
                                                atr_threshold=atr_thresh,
                                                t_low_trend=t_low_trend,
                                                t_high_absorb=t_high_absorb,
                                                scaling_multiplier=mult,
                                                use_contrary_filter=use_contrary,
                                                exclude_lunch=ex_lunch,
                                                use_mega_proximity=use_mega,
                                                base_contracts_trend=c_trend,
                                                base_contracts_absorb=c_absorb,
                                                size_scaling_absorb=False
                                            )
                                            
                                            count += 1
                                            if count % 5000 == 0:
                                                print(f"Simulati {count} scenari...")
                                                
                                            # Filter out bad setups
                                            if n_trades >= 40 and dd < 2000.0 and pf > 1.2:
                                                best_results.append({
                                                    "atr_type": atr_type,
                                                    "scaling_mode": scaling_mode,
                                                    "atr_thresh": atr_thresh,
                                                    "t_low_trend": t_low_trend,
                                                    "t_high_absorb": t_high_absorb,
                                                    "mult": mult,
                                                    "exclude_lunch": ex_lunch,
                                                    "use_contrary": use_contrary,
                                                    "use_mega": use_mega,
                                                    "contracts": (c_trend, c_absorb),
                                                    "trades": n_trades,
                                                    "wr": wr,
                                                    "pf": pf,
                                                    "net_pnl": net,
                                                    "max_dd": dd
                                                })
                                                
    print(f"\nFine ottimizzazione. Trovati {len(best_results)} scenari validi su {count} simulati.")
    
    best_results = sorted(best_results, key=lambda x: (-x["pf"], -x["wr"]))
    
    output_file = Path("scripts/regime_volatility_optimizer_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(best_results[:100], f, indent=4)
        
    print(f"\nTop 15 Scenari Ottimizzati (Con Ingresso CLOSE M1 Corretto):")
    for i, res in enumerate(best_results[:15]):
        print(f"{i+1:2d}. ATR={res['atr_type']} | Mode={res['scaling_mode']} | T_trend={res['t_low_trend']} | T_absorb={res['t_high_absorb']} | Multi={res['mult']} | ExLunch={res['exclude_lunch']} | Contr={res['use_contrary']} | Mega={res['use_mega']} | Size={res['contracts']} | N={res['trades']} | WR={res['wr']:.1f}% | PF={res['pf']:.2f} | Net=${res['net_pnl']:.2f} | DD=${res['max_dd']:.2f}")

if __name__ == "__main__":
    main()
