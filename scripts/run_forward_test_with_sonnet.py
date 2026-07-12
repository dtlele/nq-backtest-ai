import sys
import os
import json
import pandas as pd
from pathlib import Path
import pytz
from datetime import datetime

# Reconfigure terminal encoding to UTF-8 to prevent emoji crash
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure paths are set correctly
sys.path.insert(0, r"C:\Users\Mauro\Documents\nq-production-bot\src")
sys.path.append(r"C:\Users\Mauro\Documents\nq-backtest-clean")

import agent_filter

# Mock Telegram to avoid spamming the channel during backtest
agent_filter.send_telegram_message = lambda text: None

# Use configure filter model from environment
agent_filter.OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL_FILTER", "z-ai/glm-5.2")

ET = pytz.timezone("America/New_York")
CACHE_DIR = r"C:\Users\Mauro\Documents\nq-backtest-clean\cache_ohlc"
DATA_DIR = Path(r"C:\Users\Mauro\Documents\nq-backtest-clean\dashboard\public\data")

def compute_5day_atr(date_str, cached_dates, bars_cache):
    import bisect
    import numpy as np
    
    idx = bisect.bisect_left(cached_dates, date_str)
    prev_dates = cached_dates[max(0, idx - 5):idx]
    if len(prev_dates) < 5:
        return 180.0
        
    ranges = []
    for d in prev_dates:
        bars = bars_cache.get(d)
        if bars:
            r_high = max(b["high"] for b in bars)
            r_low = min(b["low"] for b in bars)
            ranges.append(r_high - r_low)
            
    if len(ranges) >= 3:
        return np.mean(ranges)
    return 180.0

def load_bars_cache():
    bars_cache = {}
    cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    for d in cached_dates:
        cache_file = Path(CACHE_DIR) / f"{d}.csv"
        if cache_file.exists():
            try:
                df = pd.read_csv(cache_file)
                bars_cache[d] = df.to_dict(orient='records')
            except:
                pass
    return cached_dates, bars_cache

def main():
    print("Loading OHLC bars cache...")
    cached_dates, bars_cache = load_bars_cache()
    print(f"Loaded {len(bars_cache)} OHLC bar files.")

    # Load 2026 sequences
    print("Loading historical sequences...")
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        seqs_combined = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_2026.json", encoding="utf-8") as f:
        seqs_raw = json.load(f)
        
    raw_lookup = {}
    for s in seqs_raw:
        k = (s["date"], s["end_time"])
        raw_lookup[k] = s

    # Filter to March 1, 2026 -> June 30, 2026 (Out-Of-Sample)
    oos_seqs = [s for s in seqs_combined if "20260301" <= s["date"] <= "20260630"]
    oos_seqs = sorted(oos_seqs, key=lambda x: (x["date"], x["end_time"]))
    print(f"Found {len(oos_seqs)} total candidate sequences in Out-Of-Sample period (March-June 2026).")

    # Pre-cache all big trades and M1 bars files in memory
    big_trades_cache = {}
    m1_ny_cache = {}
    print("Pre-caching all daily files in memory...")
    for s in oos_seqs:
        date_str = s["date"]
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        if date_str not in big_trades_cache:
            day_file = DATA_DIR / f"{formatted_date}.json"
            if day_file.exists():
                try:
                    with open(day_file, "r", encoding="utf-8") as f:
                        day_data = json.load(f)
                    big_trades_cache[date_str] = day_data.get("big_trades", [])
                    m1_ny_cache[date_str] = day_data.get("m1_ny", [])
                except:
                    big_trades_cache[date_str] = []
                    m1_ny_cache[date_str] = []
            else:
                big_trades_cache[date_str] = []
                m1_ny_cache[date_str] = []

    # We will apply the optimal quant filters (Rank 2 Case B configuration):
    # Setups: trend_long, absorb_long, trend_short
    # CVD Climax: Th=2000 (only_absorption)
    # Contrary Big Trade: Th=150
    # Trading Hours: Morning End: 11:00 | Afternoon Start: 14:30 | Lunch Excl: True
    # VA Filters: Short Inside VA: True | Long Inside VA: True | Long Below VA: False
    # Volume Filter: original (80 <= vol < 150 or vol >= 500)
    
    quant_passed_seqs = []
    
    for s in oos_seqs:
        date_str = s["date"]
        time_str = s["end_time"]
        pattern = s["seq_pattern"]
        
        # 0. Active setup check
        if pattern not in ["trend_long", "absorb_long", "trend_short"]:
            continue
            
        # 1. Entry volume filter (original)
        vol = s["entry_vol"]
        if not ((80 <= vol < 150) or (vol >= 500)):
            continue
            
        # 2. Trading hour windows
        time_parts = time_str.split(':')
        h, m = int(time_parts[0]), int(time_parts[1])
        t_val = h * 60 + m
        is_morning = (9 * 60 + 30 <= t_val < 11 * 60)
        is_afternoon = (14 * 60 + 30 <= t_val < 15 * 60 + 30)
        if not (is_morning or is_afternoon):
            continue
            
        raw_seq = raw_lookup.get((date_str, time_str))
        if not raw_seq or not raw_seq.get("steps"):
            continue
            
        last_step = raw_seq["steps"][-1]
        session_cvd = last_step.get("session_cvd", 0)
        
        # 3. CVD Climax filter (Th=2000 on only_absorption)
        if "absorb" in pattern and abs(session_cvd) >= 2000:
            continue
            
        # 4. Value Area Filters
        vs_val = last_step.get("price_vs_val", "unknown")
        vs_vah = last_step.get("price_vs_vah", "unknown")
        is_inside_va = (vs_val == "above" and vs_vah == "below")
        
        direction = "long" if "long" in pattern else "short"
        if direction == "short" and is_inside_va:
            continue
        if direction == "long" and is_inside_va:
            continue
            
        # 5. Contrary Big Trade Filter (Th=150)
        # Use contrary trade fields from raw_seq
        contrary_max_size = raw_seq.get("contrary_max_size", 0)
        if contrary_max_size >= 150:
            continue
            
        quant_passed_seqs.append((s, raw_seq))
        
    print(f"Number of trades that passed the Quant Filters in OOS period: {len(quant_passed_seqs)}")
    
    if len(quant_passed_seqs) == 0:
        print("No trades passed quant filters. Exiting.")
        return
        
    # Now run them through Sonnet Agentic Filter
    results = []
    
    # MNQ contract settings
    base_contracts = 3
    point_value = 2.0
    commission = 0.50
    
    print("\nStarting out-of-sample forward-testing with DeepSeek Chat agentic filter...")
    
    # Configure OpenRouter model from environment
    os.environ["LLM_PROVIDER"] = "openrouter"
    os.environ["OPENROUTER_MODEL"] = os.getenv("OPENROUTER_MODEL_FILTER", "z-ai/glm-5.2")
    
    for idx, (s, raw_seq) in enumerate(quant_passed_seqs, 1):
        date_str = s["date"]
        time_str = s["end_time"]
        pattern = s["seq_pattern"]
        entry_price = s["entry_price"]
        direction = "long" if "long" in pattern else "short"
        
        last_step = raw_seq["steps"][-1]
        session_cvd = last_step.get("session_cvd", 0)
        
        # Value Area Bounds (approximate from ticks or set defaults)
        # Since we don't have exact VA high/low numbers saved in the sequence steps directly,
        # we can pass approximate values. Let's see: price_vs_vah and price_vs_val can help us.
        # If price_vs_val == "above" and price_vs_vah == "above", price is above VAH.
        # We can pass values that match this logic so Fabio/Andrea prompts are structurally correct.
        vah_ticks = last_step.get("vah_ticks", 0)
        val_ticks = last_step.get("val_ticks", 0)
        
        # tick size is 0.25 points
        va_high = entry_price - (vah_ticks * 0.25)
        va_low = entry_price - (val_ticks * 0.25)
        
        # Overnight VA (if not present, default to VA)
        overnight_vah = va_high
        overnight_val = va_low
        
        # contrary trades details
        contrary_max_size = raw_seq.get("contrary_max_size", 0)
        contrary_count = raw_seq.get("contrary_count", 0)
        
        # Localize entry datetime
        entry_dt = pd.to_datetime(date_str + ' ' + time_str, format='%Y%m%d %H:%M')
        entry_dt = ET.localize(entry_dt)
        
        # Simulate trade execution using OHLC bars
        bars = bars_cache.get(date_str)
        if not bars:
            print(f"   ⚠️ Skipping: OHLC bars not found in cache for date {date_str}")
            continue
            
        entry_idx = -1
        for i, b in enumerate(bars):
            # parse time
            t_str = b["timestamp"].split(" ")[1][:5]
            if t_str == time_str:
                entry_idx = i
                break
                
        if entry_idx == -1:
            print(f"   ⚠️ Skipping: Entry time {time_str} not found in OHLC bars for date {date_str}")
            continue
            
        # Compute price_change_10m and dist_sma_30 dynamically from OHLC bars
        price_change_10m = 0.0
        dist_sma_30 = 0.0
        
        if entry_idx >= 9:
            prior_10 = bars[entry_idx - 9 : entry_idx + 1]
            price_change_10m = prior_10[-1]["close"] - prior_10[0]["open"]
            
        if entry_idx >= 29:
            prior_30 = bars[entry_idx - 29 : entry_idx + 1]
            sma_30 = sum(b["close"] for b in prior_30) / 30.0
            dist_sma_30 = entry_price - sma_30

        # Get recent big trades for the trigger bar minute (from the current entry_dt)
        recent_big_trades = []
        entry_ts_start = int(entry_dt.timestamp())
        entry_ts_end = entry_ts_start + 59
        
        day_trades = big_trades_cache.get(date_str, [])
        for bt in day_trades:
            if entry_ts_start <= bt["time"] <= entry_ts_end:
                recent_big_trades.append({
                    "price": bt["price"],
                    "size": bt["size"],
                    "side": bt["side"]
                })
        
        # Get actual volume and delta from footprint JSON
        trigger_bar_volume = 0
        trigger_bar_delta = 0
        trigger_idx = -1
        day_m1 = m1_ny_cache.get(date_str, [])
        for idx_m, m_bar in enumerate(day_m1):
            bar_dt = datetime.fromtimestamp(m_bar["time"], tz=pytz.utc).astimezone(ET)
            if bar_dt.strftime("%H:%M") == time_str:
                trigger_bar_volume = m_bar.get("volume", 0)
                trigger_bar_delta = m_bar.get("delta", 0)
                trigger_idx = idx_m
                break

        # Calculate avg_volume_5m from prior RTH bars
        avg_volume_5m = 0.0
        if trigger_idx != -1:
            prior_rth_bars = []
            for b in day_m1[:trigger_idx]:
                b_dt = datetime.fromtimestamp(b["time"], tz=pytz.utc).astimezone(ET)
                if b_dt.hour > 9 or (b_dt.hour == 9 and b_dt.minute >= 30):
                    prior_rth_bars.append(b)
            prior_rth_bars = prior_rth_bars[-5:]
            if prior_rth_bars:
                avg_volume_5m = sum(b.get("volume", 0) for b in prior_rth_bars) / len(prior_rth_bars)
            else:
                # fallback to pre-market
                prior_pm_bars = day_m1[max(0, trigger_idx - 5):trigger_idx]
                if prior_pm_bars:
                    avg_volume_5m = sum(b.get("volume", 0) for b in prior_pm_bars) / len(prior_pm_bars)

        # Calculate initial balance (developing or final) up to entry_dt
        rth_first_hour_bars = []
        for b in day_m1:
            b_dt = datetime.fromtimestamp(b["time"], tz=pytz.utc).astimezone(ET)
            if (b_dt.hour == 9 and b_dt.minute >= 30) or (b_dt.hour == 10 and b_dt.minute < 30):
                if b_dt <= entry_dt:
                    rth_first_hour_bars.append(b)
        if rth_first_hour_bars:
            ib_high = max(b.get("high", 0.0) for b in rth_first_hour_bars)
            ib_low = min(b.get("low", 0.0) for b in rth_first_hour_bars)
        else:
            ib_high = 0.0
            ib_low = 0.0
        initial_balance = {"high": ib_high, "low": ib_low}

        print(f"\n[{idx}/{len(quant_passed_seqs)}] Trade {date_str} {time_str} {pattern.upper()} at {entry_price} (Vol: {trigger_bar_volume}, Delta: {trigger_bar_delta:+}, IB: {ib_low:.2f}-{ib_high:.2f}, Avg5m: {avg_volume_5m:.1f})")
        
        # Run agentic filter
        approved, report_str = agent_filter.run_agentic_filter(
            setup_name=pattern,
            direction=direction,
            price=entry_price,
            session_cvd=session_cvd,
            va_low=va_low,
            va_high=va_high,
            overnight_val=overnight_val,
            overnight_vah=overnight_vah,
            price_change_10m=price_change_10m,
            dist_sma_30=dist_sma_30,
            recent_big_trades=recent_big_trades,
            contrary_max_size=contrary_max_size,
            contrary_count=contrary_count,
            contrary_big_trades=[], # details not needed for simulation
            trigger_bar_delta=trigger_bar_delta,
            trigger_bar_volume=trigger_bar_volume,
            initial_balance=initial_balance,
            avg_volume_5m=avg_volume_5m
        )
        
        # Determine trade outcome based on historical SL/TP
        # Low vs high vol setups
        atr = compute_5day_atr(date_str, cached_dates, bars_cache)
        if atr < 200.0:
            sl = 39.0 if direction == "long" else 46.0 # trend
            if "absorb" in pattern:
                sl = 49.0
            tp = 120.0 if direction == "long" else 120.0
            if "absorb" in pattern:
                tp = 37.0 if direction == "long" else 114.0
        else:
            sl = 22.0 if direction == "long" else 48.0
            if "absorb" in pattern:
                sl = 50.0 if direction == "long" else 34.0
            tp = 113.0 if direction == "long" else 113.0
            if "absorb" in pattern:
                tp = 115.0 if direction == "long" else 35.0
                
        pnl_pts = 0.0
        outcome = "eod"
        
        # Simulate trade execution using OHLC bars
        for i in range(entry_idx + 1, len(bars)):
            bar = bars[i]
            t_str = bar["timestamp"].split(" ")[1][:5]
            # End of day cutoff at 16:00
            h_b, m_b = map(int, t_str.split(':'))
            if h_b >= 16:
                outcome = "eod"
                pnl_pts = (bar["close"] - entry_price) if direction == "long" else (entry_price - bar["close"])
                break
                
            high = bar["high"]
            low = bar["low"]
            
            if direction == "long":
                if low <= entry_price - sl:
                    pnl_pts = -sl
                    outcome = "loss"
                    break
                elif high >= entry_price + tp + 0.25:
                    pnl_pts = tp
                    outcome = "win"
                    break
            else:
                if high >= entry_price + sl:
                    pnl_pts = -sl
                    outcome = "loss"
                    break
                elif low <= entry_price - tp - 0.25:
                    pnl_pts = tp
                    outcome = "win"
                    break
                        
        pnl_pts = pnl_pts - 1.5 # slippage
        pnl_usd = ((pnl_pts * point_value) - commission) * base_contracts
        
        results.append({
            "date": date_str,
            "time": time_str,
            "pattern": pattern,
            "entry_price": entry_price,
            "direction": direction,
            "quant_pnl_usd": pnl_usd,
            "outcome": outcome,
            "agent_approved": approved,
            "final_pnl_usd": pnl_usd if approved else 0.0
        })

    # Summary analysis
    df = pd.DataFrame(results)
    
    # Quant results (all trades)
    q_trades = len(df)
    q_wins = len(df[(df["quant_pnl_usd"] > 0)])
    q_wr = (q_wins / q_trades) * 100 if q_trades > 0 else 0
    q_pnl = df["quant_pnl_usd"].sum()
    
    # Agent filtered results
    a_df = df[df["agent_approved"]]
    a_trades = len(a_df)
    a_wins = len(a_df[(a_df["final_pnl_usd"] > 0)])
    a_wr = (a_wins / a_trades) * 100 if a_trades > 0 else 0
    a_pnl = a_df["final_pnl_usd"].sum()
    
    print("\n" + "="*60)
    print("OOS FORWARD TEST RESULTS SUMMARY (March - June 2026)")
    print("="*60)
    print(f"QUANT BASELINE (No Agent filter):")
    print(f"  Trades:     {q_trades}")
    print(f"  Win Rate:   {q_wr:.1f}%")
    print(f"  Net P&L:    ${q_pnl:,.2f}")
    print(f"AGENTIC FILTERED (Sonnet filter):")
    print(f"  Trades:     {a_trades} (Filtered out {q_trades - a_trades} trades)")
    print(f"  Win Rate:   {a_wr:.1f}%")
    print(f"  Net P&L:    ${a_pnl:,.2f}")
    print("="*60)
    
    # Save OOS test report
    report_path = Path("output/oos_forward_test_report.md")
    report_content = f"""# 🧪 Out-Of-Sample Forward Test Report (March-June 2026)
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This report evaluates the performance of the **Claude 3.5 Sonnet Agentic Filter** during the out-of-sample forward test period from March 1, 2026 to June 30, 2026.

## 📊 Summary Performance Comparison

| Metric | Quant Baseline (No Agent) | Agentic Filtered (Sonnet) | Change |
|---|---|---|---|
| **Trades (N)** | {q_trades} | {a_trades} | {a_trades - q_trades} ({((a_trades - q_trades)/q_trades)*100:.1f}%) |
| **Win Rate** | {q_wr:.1f}% | {a_wr:.1f}% | {a_wr - q_wr:+.1f}% |
| **Net P&L (USD)** | ${q_pnl:,.2f} | ${a_pnl:,.2f} | ${a_pnl - q_pnl:+,.2f} ({((a_pnl - q_pnl)/q_pnl)*100:+.1f}%) |

## 📝 Trade Log Details
"""
    
    for r in results:
        status_tag = "🟩 APPROVED" if r["agent_approved"] else "🟥 REJECTED"
        win_loss = "WIN" if r["quant_pnl_usd"] > 0 else "LOSS"
        report_content += f"- **{r['date']} {r['time']}** | Setup: `{r['pattern'].upper()}` | price: {r['entry_price']:.2f} | Quant P&L: ${r['quant_pnl_usd']:+,.2f} ({win_loss}) | Agent Status: {status_tag}\n"
        
    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write(report_content)
        
    print(f"OOS Forward-testing report saved to {report_path}")

if __name__ == "__main__":
    main()

