import sys
import os
import json
from pathlib import Path
import pytz
import pandas as pd
import numpy as np

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest-clean")

from scripts.inject_optimal_trades_to_localhost import inject
from scripts.run_unified_backtest_with_filters import check_contrary_big_trades

ET = pytz.timezone("America/New_York")
CACHE_DIR = r"C:\Users\Mauro\Documents\nq-backtest-clean\cache_ohlc"

class MockBar:
    def __init__(self, timestamp, open_, high, low, close):
        self.timestamp = timestamp
        self.open = open_
        self.high = high
        self.low = low
        self.close = close

bars_cache = {}

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

def main():
    # Carichiamo sequenze sia del 2025 che del 2026 per avere lo storico completo sulla dashboard
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined_2025.json", encoding="utf-8") as f:
        seqs_combined_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2025.json", encoding="utf-8") as f:
        raw_seqs_2025 = json.load(f)
        
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        seqs_combined_2026 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2026.json", encoding="utf-8") as f:
        raw_seqs_2026 = json.load(f)
        
    raw_lookup = {}
    for s in raw_seqs_2025 + raw_seqs_2026:
        k = (s["date"], s["end_time"])
        raw_lookup[k] = s
        
    seqs = seqs_combined_2025 + seqs_combined_2026
    seqs = sorted(seqs, key=lambda x: (x["date"], x["end_time"]))
        
    setups = {
        "Trend LONG (Buy Aggressives + Price Up)": {
            "cond": lambda s: s["seq_pattern"] == "trend_long",
            "direction": "long",
            "sl": 22.0,
            "tp": 113.0
        },
        "Absorption LONG (Sell Aggressives Absorbed + Price Up)": {
            "cond": lambda s: s["seq_pattern"] == "absorb_long",
            "direction": "long",
            "sl": 50.0,
            "tp": 115.0
        },
        "Trend SHORT (Sell Aggressives + Price Down)": {
            "cond": lambda s: s["seq_pattern"] == "trend_short",
            "direction": "short",
            "sl": 55.0,
            "tp": 120.0
        },
        "Absorption SHORT (Buy Aggressives Absorbed + Price Down)": {
            "cond": lambda s: s["seq_pattern"] == "absorb_short",
            "direction": "short",
            "sl": 34.0,
            "tp": 35.0
        }
    }
    
    # Position Sizing (MNQ: 3 contracts)
    contracts = 3
    point_value = 2.0
    commission = 0.50
    equity = 50000.0
    
    # Pre-scan OHLC files
    for f in Path(CACHE_DIR).glob("*.csv"):
        get_bars_for_date(f.stem)
        
    trades_executed = []
    last_exit_datetime = None
    
    for s in seqs:
        # Check setup
        triggered_setup = None
        for name, setup in setups.items():
            if setup["cond"](s):
                triggered_setup = name
                setup_info = setup
                break
                
        if not triggered_setup:
            continue
            
        date_str = s["date"]
        time_str = s["end_time"]
        entry_price = s["entry_price"]
        direction = setup_info["direction"]
        sl = setup_info["sl"]
        tp = setup_info["tp"]
        
        # Volume & Time filters
        vol = s['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)):
            continue
            
        time_parts = time_str.split(':')
        h, m = int(time_parts[0]), int(time_parts[1])
        t_val = h * 60 + m
        is_morning = (9 * 60 + 30 <= t_val < 11 * 60)
        is_afternoon = (14 * 60 + 30 <= t_val < 15 * 60 + 30) # A_Start=14:30
        if not (is_morning or is_afternoon):
            continue
            
        # CVD Climax Filter (Th=2000)
        raw_seq = raw_lookup.get((date_str, time_str))
        if not raw_seq or not raw_seq.get("steps"):
            continue
        last_step = raw_seq["steps"][-1]
        session_cvd = last_step.get("session_cvd", 0)
        if abs(session_cvd) >= 2000:
            continue
            
        # Value Area Filter (Block short inside VA, Block long below VA)
        vs_val = last_step.get("price_vs_val", "unknown")
        vs_vah = last_step.get("price_vs_vah", "unknown")
        is_inside_va = (vs_val == "above" and vs_vah == "below")
        is_below_va = (vs_val == "below")
        
        if direction == "short" and is_inside_va:
            continue
        if direction == "long" and is_below_va:
            continue
            
        # Contrary Big Trade Filter (Th=250)
        step1_time = raw_seq["steps"][0]["time_et"]
        if check_contrary_big_trades(date_str, step1_time, time_str, direction, threshold=250):
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
        
        # CFD Dynamic Risk Sizing (1.20% del capitale fissa)
        risk_pct = 0.0120
        contracts = round((equity * risk_pct) / (sl * point_value), 2)
        if contracts < 0.01:
            contracts = 0.01
            
        pnl_usd = ((pnl_pts * point_value) - commission) * contracts
        equity += pnl_usd
        
        # Enrich steps from raw sequences
        raw_seq = raw_lookup.get((date_str, time_str))
        formatted_steps = []
        if raw_seq and raw_seq.get("steps"):
            for step in raw_seq["steps"]:
                formatted_steps.append({
                    "time_et": step.get("time_et"),
                    "price": step.get("price"),
                    "dominant_side": step.get("dominant_side"),
                    "volume": step.get("volume"),
                    "cumulative_delta": step.get("cumulative_delta", 0)
                })
        else:
            # Fallback
            for step in s["steps"]:
                formatted_steps.append({
                    "time_et": step.get("time_et"),
                    "price": entry_price,
                    "dominant_side": "A" if direction == "long" else "B",
                    "volume": step.get("volume"),
                    "cumulative_delta": 0
                })
        
        trade_info = {
            "date": date_str,
            "time": time_str,
            "exit_time": exit_time_str,
            "setup": triggered_setup,
            "direction": direction.upper(),
            "entry": entry_price,
            "sl_pts": sl,
            "tp_pts": tp,
            "mae": s["mae_long_pts"] if direction == "long" else s["mae_short_pts"],
            "mfe": s["mae_long_pts"] if direction == "long" else s["mae_short_pts"],
            "mae_actual_pts": round(sl if outcome == "loss" else 10.0, 2),
            "outcome": outcome,
            "pnl_pts": round(pnl_pts, 2),
            "pnl_usd": round(pnl_usd, 2),
            "equity": round(equity, 2),
            "contracts": contracts,
            "steps": formatted_steps
        }
        trades_executed.append(trade_info)
        
        exit_dt = pd.to_datetime(date_str + ' ' + exit_time_str, format='%Y%m%d %H:%M')
        exit_dt = ET.localize(exit_dt)
        if exit_dt < entry_dt:
            exit_dt = exit_dt + pd.Timedelta(days=1)
        last_exit_datetime = exit_dt
        
    print(f"Executed {len(trades_executed)} combined trades for 2025-2026.")
    
    # Save to optimal_backtest_trades.json
    output_path = Path("agent_memory/optimal_backtest_trades.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(trades_executed, f, indent=2)
    print(f"Saved trades to {output_path}")
    
    # Run injector
    inject()

if __name__ == "__main__":
    main()

