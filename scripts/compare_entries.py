import json
import sys
from pathlib import Path
import pytz
import datetime
import pandas as pd
import numpy as np

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest-clean")
from scripts.time_session_optimizer_v2 import CACHE_DIR, get_bars_for_date, compute_5day_atr, get_session_label

ET = pytz.timezone("America/New_York")

def simulate_trade_wick(bars, entry_idx, direction, sl, tp, base_contracts=2.5):
    """Mode A: Wick Entry (Lookahead/Unrealistic)"""
    start_idx = entry_idx
    if direction == "long":
        entry_price = bars[start_idx].low + 1.0
    else:
        entry_price = bars[start_idx].high - 1.0
        
    outcome = None
    pnl_pts = 0.0
    
    for i in range(start_idx + 1, len(bars)):
        bar = bars[i]
        t_et = bar.timestamp.astimezone(ET)
        
        if t_et.hour == 16 and t_et.minute >= 55:
            outcome = "eod"
            pnl_pts = (bar.close - entry_price) if direction == "long" else (entry_price - bar.close)
            break
            
        if direction == "long":
            if bar.low <= entry_price - sl:
                pnl_pts = -sl; outcome = "loss"; break
            elif bar.high >= entry_price + tp + 0.25:
                pnl_pts = tp; outcome = "win"; break
        else:
            if bar.high >= entry_price + sl:
                pnl_pts = -sl; outcome = "loss"; break
            elif bar.low <= entry_price - tp - 0.25:
                pnl_pts = tp; outcome = "win"; break
                
    if outcome is None:
        pnl_pts = (bars[-1].close - entry_price) if direction == "long" else (entry_price - bars[-1].close)
        
    pnl_usd = ((pnl_pts - 1.5) * 2.0 - 0.50) * base_contracts
    return pnl_usd, outcome

def simulate_trade_instant(bars, entry_idx, direction, sl, tp, raw_entry_price, base_contracts=2.5):
    """Mode B: Setup Price Entry (Realistic Instant)
    Checks the entry candle itself for stop out / target hits.
    If both could be hit on the entry candle, assumes stop out (conservative).
    """
    entry_price = raw_entry_price
    outcome = None
    pnl_pts = 0.0
    
    # Check entry candle (intra-candle simulation)
    entry_bar = bars[entry_idx]
    if direction == "long":
        # Conservative: did it hit SL on the entry bar?
        hit_sl = entry_bar.low <= entry_price - sl
        hit_tp = entry_bar.high >= entry_price + tp + 0.25
        if hit_sl and hit_tp:
            pnl_pts = -sl; outcome = "loss"
        elif hit_sl:
            pnl_pts = -sl; outcome = "loss"
        elif hit_tp:
            pnl_pts = tp; outcome = "win"
    else:
        hit_sl = entry_bar.high >= entry_price + sl
        hit_tp = entry_bar.low <= entry_price - tp - 0.25
        if hit_sl and hit_tp:
            pnl_pts = -sl; outcome = "loss"
        elif hit_sl:
            pnl_pts = -sl; outcome = "loss"
        elif hit_tp:
            pnl_pts = tp; outcome = "win"
            
    if outcome is None:
        # Check subsequent candles
        for i in range(entry_idx + 1, len(bars)):
            bar = bars[i]
            t_et = bar.timestamp.astimezone(ET)
            
            if t_et.hour == 16 and t_et.minute >= 55:
                outcome = "eod"
                pnl_pts = (bar.close - entry_price) if direction == "long" else (entry_price - bar.close)
                break
                
            if direction == "long":
                if bar.low <= entry_price - sl:
                    pnl_pts = -sl; outcome = "loss"; break
                elif bar.high >= entry_price + tp + 0.25:
                    pnl_pts = tp; outcome = "win"; break
            else:
                if bar.high >= entry_price + sl:
                    pnl_pts = -sl; outcome = "loss"; break
                elif bar.low <= entry_price - tp - 0.25:
                    pnl_pts = tp; outcome = "win"; break
                    
    if outcome is None:
        pnl_pts = (bars[-1].close - entry_price) if direction == "long" else (entry_price - bars[-1].close)
        
    pnl_usd = ((pnl_pts - 1.5) * 2.0 - 0.50) * base_contracts
    return pnl_usd, outcome

def simulate_trade_close(bars, entry_idx, direction, sl, tp, base_contracts=2.5):
    """Mode C: M1 Close Entry (Realistic Delayed)
    Entry at the close of the M1 candle, checking SL/TP from the next candle.
    """
    start_idx = entry_idx
    entry_price = bars[start_idx].close
    outcome = None
    pnl_pts = 0.0
    
    for i in range(start_idx + 1, len(bars)):
        bar = bars[i]
        t_et = bar.timestamp.astimezone(ET)
        
        if t_et.hour == 16 and t_et.minute >= 55:
            outcome = "eod"
            pnl_pts = (bar.close - entry_price) if direction == "long" else (entry_price - bar.close)
            break
            
        if direction == "long":
            if bar.low <= entry_price - sl:
                pnl_pts = -sl; outcome = "loss"; break
            elif bar.high >= entry_price + tp + 0.25:
                pnl_pts = tp; outcome = "win"; break
        else:
            if bar.high >= entry_price + sl:
                pnl_pts = -sl; outcome = "loss"; break
            elif bar.low <= entry_price - tp - 0.25:
                pnl_pts = tp; outcome = "win"; break
                
    if outcome is None:
        pnl_pts = (bars[-1].close - entry_price) if direction == "long" else (entry_price - bars[-1].close)
        
    pnl_usd = ((pnl_pts - 1.5) * 2.0 - 0.50) * base_contracts
    return pnl_usd, outcome

def run_backtest_with_mode(seqs_combined, v2_rules_a, low_vol_setups, high_vol_setups, mode):
    results = []
    for s in seqs_combined:
        pattern = s["seq_pattern"]
        if pattern not in ["absorb_long", "absorb_short"]: continue
        
        vol = s['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)): continue
            
        date_str = s["date"]
        time_str = s["end_time"]
        
        rule = v2_rules_a.get(pattern)
        if not rule: continue
        
        dt_obj = datetime.datetime.strptime(date_str, "%Y%m%d")
        if dt_obj.strftime("%A") not in rule["days"]: continue
        
        h, m = int(time_str.split(':')[0]), int(time_str.split(':')[1])
        t_val = h * 60 + m
        
        if not (9*60+30 <= t_val < 16*60): continue
        if get_session_label(t_val) not in rule["sessions"]: continue
        if rule.get("exclude_10am", False) and (9*60+55 <= t_val <= 10*60+5): continue
            
        atr = compute_5day_atr(date_str)
        setup_info = low_vol_setups.get(pattern) if atr < 200.0 else high_vol_setups.get(pattern)
        if not setup_info: continue
            
        direction = setup_info["direction"]
        bars = get_bars_for_date(date_str)
        if not bars: continue
            
        idx_T = -1
        for i, b in enumerate(bars):
            if b.timestamp.astimezone(ET).strftime("%H:%M") == time_str:
                idx_T = i; break
        if idx_T < 30: continue
            
        # Level 3 Filters
        prior_10 = bars[idx_T-10 : idx_T]
        price_change_10 = prior_10[-1].close - prior_10[0].open
        if pattern == "absorb_long" and price_change_10 < -10: continue
        if pattern == "absorb_short" and price_change_10 > 10: continue
            
        prior_30 = bars[idx_T-30 : idx_T]
        sma_30 = sum(b.close for b in prior_30) / 30.0
        dist_sma = bars[idx_T].close - sma_30
        if pattern == "absorb_short" and dist_sma > -45: continue
        
        if mode == "wick":
            pnl, out = simulate_trade_wick(bars, idx_T, direction, setup_info["sl"], setup_info["tp"])
        elif mode == "instant":
            pnl, out = simulate_trade_instant(bars, idx_T, direction, setup_info["sl"], setup_info["tp"], s["entry_price"])
        elif mode == "close":
            pnl, out = simulate_trade_close(bars, idx_T, direction, setup_info["sl"], setup_info["tp"])
            
        results.append({"pattern": pattern, "pnl": pnl, "out": out})
        
    df = pd.DataFrame(results)
    if df.empty:
        return 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    
    total_trades = len(df)
    win_rate = (df['out'] == 'win').mean() * 100
    net_pnl = df['pnl'].sum()
    
    gw = sum(p for p in df["pnl"] if p > 0)
    gl = abs(sum(p for p in df["pnl"] if p < 0))
    pf = gw/gl if gl > 0 else float('inf')
    
    # Calculate drawdown
    df['cum_pnl'] = df['pnl'].cumsum()
    df['peak'] = df['cum_pnl'].cummax()
    df['drawdown'] = df['peak'] - df['cum_pnl']
    max_dd = df['drawdown'].max()
    
    # Breakdown by pattern
    short_df = df[df['pattern'] == 'absorb_short']
    short_wr = (short_df['out'] == 'win').mean() * 100 if not short_df.empty else 0.0
    long_df = df[df['pattern'] == 'absorb_long']
    long_wr = (long_df['out'] == 'win').mean() * 100 if not long_df.empty else 0.0
    
    return total_trades, win_rate, pf, net_pnl, max_dd, long_wr, short_wr

def main():
    import scripts.time_session_optimizer_v2 as tso
    tso.cached_dates = sorted([f.stem for f in Path(CACHE_DIR).glob("*.csv")])
    for d in tso.cached_dates: get_bars_for_date(d)

    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined_2025.json", encoding="utf-8") as f:
        seqs_combined_2025 = json.load(f)
    with open("knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences_combined.json", encoding="utf-8") as f:
        seqs_combined_2026 = json.load(f)
        
    seqs_combined = seqs_combined_2025 + seqs_combined_2026

    with open("scripts/time_session_rules_v2.json", "r", encoding="utf-8") as f:
        v2_rules_a = json.load(f)["v2_case_a_coarse_sessions"]["rules"]

    low_vol_setups = {
        "absorb_long": {"direction": "long", "sl": 49.0, "tp": 37.0},
        "absorb_short": {"direction": "short", "sl": 49.0, "tp": 114.0}
    }
    high_vol_setups = {
        "absorb_long": {"direction": "long", "sl": 50.0, "tp": 115.0},
        "absorb_short": {"direction": "short", "sl": 34.0, "tp": 35.0}
    }

    print("\n=======================================================")
    print("CONFRONTO MODALITA DI INGRESSO PER GLI ABSORB SETUPS")
    print("=======================================================")
    
    for mode in ["wick", "instant", "close"]:
        n, wr, pf, pnl, dd, l_wr, s_wr = run_backtest_with_mode(seqs_combined, v2_rules_a, low_vol_setups, high_vol_setups, mode)
        print(f"\nMODALITA: {mode.upper()}")
        print(f"  Trade totali:        {n}")
        print(f"  Net PnL (USD):       ${pnl:,.2f}")
        print(f"  Profit Factor:       {pf:.2f}")
        print(f"  Win Rate Globale:    {wr:.1f}%")
        print(f"  Max Drawdown:        ${dd:,.2f}")
        print(f"  Win Rate Long:       {l_wr:.1f}%")
        print(f"  Win Rate Short:      {s_wr:.1f}%")

if __name__ == "__main__":
    main()

