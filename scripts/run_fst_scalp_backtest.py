import os
import glob
import pandas as pd
import numpy as np
import pytz
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from src.data_loader import load_day
from src.range_builder import build_range_bars
from src.footprint_engine import get_bar_poc
from src.volume_profile import build_profile_from_bars
from src.pattern_detector import detect_bullish_setup, detect_bearish_setup
from src.trade_manager import ActiveTrade, evaluate_trade_tick, update_trailing_stop

# Config
DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
NY_TZ = pytz.timezone("America/New_York")

# Strategy Parameters
RANGE_POINTS = 10.0
ABSORPTION_DELTA_LIMIT = 26
BIG_TRADE_THRESHOLD = 10
POC_INSTITUTIONAL_VOL = 179
COMPOSITE_LOOKBACK_MIN = 60
PROXIMITY_PTS = 3.5

# Position sizing config (matching dashboard expectations)
CONTRACTS = 3
POINT_VALUE = 2.0  # MNQ point value
COMMISSION = 0.50

# --- OPTIMIZED RISK CONFIGURATION ---
ENTRY_MODE = 'limit'            # 'market' (C2.close) | 'limit' (C1.close / pullback)
STOP_TYPE = 'swing_low'         # 'c1_low_buffered' | 'swing_low'
STOP_BUFFER = 3.5               # Used if STOP_TYPE is c1_low_buffered
MIN_SL_POINTS = 16.0            # Minimum Stop Loss distance to prevent noise cacciate

def run_day_backtest(filepath: str) -> list[dict]:
    day_name = os.path.basename(filepath)
    parts = day_name.split("-")
    raw_date = parts[2].split(".")[0] if len(parts) >= 3 else "20251101"
    
    print(f"\nProcessing {day_name}...")
    
    trades_raw = load_day(filepath)
    if not trades_raw:
        print(f"No trades loaded for {day_name}.")
        return []
        
    # Generate Range 40 bars
    bars = build_range_bars(trades_raw, range_points=RANGE_POINTS, big_trade_threshold=BIG_TRADE_THRESHOLD)
    if not bars:
        return []
        
    closed_bars = []
    active_trade = None
    trades_log = []
    active_trade_bars = []
    daily_trade_count = 0  # Max 2 trades per day
    
    for i, bar in enumerate(bars):
        bar_ts_ny = bar.timestamp.astimezone(NY_TZ)
        is_rth = (bar_ts_ny.hour > 9 or (bar_ts_ny.hour == 9 and bar_ts_ny.minute >= 30)) and (bar_ts_ny.hour < 16)
        
        # --- TRADE MANAGEMENT (No TP — run to SL or EOD to measure TRUE MFE) ---
        if active_trade and active_trade.status == 'active':
            active_trade_bars.append(bar)
            risk = active_trade.risk_pts

            if active_trade.direction == 'long':
                profit = bar.high - active_trade.entry_price
                loss   = active_trade.entry_price - bar.low
                if profit > active_trade.max_profit_pts:
                    active_trade.max_profit_pts = profit
                if not hasattr(active_trade, 'max_adverse_pts'):
                    active_trade.max_adverse_pts = 0.0
                if loss > active_trade.max_adverse_pts:
                    active_trade.max_adverse_pts = loss

                # Only SL closes the trade intraday
                if bar.low <= active_trade.sl:
                    active_trade.status = 'stopped'
                    pnl_pts = active_trade.sl - active_trade.entry_price  # negative
                    pnl_usd = (pnl_pts * POINT_VALUE - COMMISSION) * CONTRACTS
                    trades_log.append({
                        'date': raw_date,
                        'time': active_trade.entry_ts.astimezone(NY_TZ).strftime('%H:%M'),
                        'exit_time': bar.timestamp.astimezone(NY_TZ).strftime('%H:%M'),
                        'setup': active_trade.setup_reason,
                        'direction': 'LONG',
                        'entry': active_trade.entry_price,
                        'sl_pts': risk,
                        'mfe_pts': active_trade.max_profit_pts,
                        'mfe_r': round(active_trade.max_profit_pts / risk, 2) if risk > 0 else 0,
                        'mae_pts': getattr(active_trade, 'max_adverse_pts', 0.0),
                        'mae_r': round(getattr(active_trade, 'max_adverse_pts', 0.0) / risk, 2) if risk > 0 else 0,
                        'outcome': 'loss',
                        'pnl_pts': pnl_pts,
                        'pnl_usd': pnl_usd,
                        'half_size': active_trade.half_size,
                        'steps': [{'time_et': b.timestamp.astimezone(NY_TZ).strftime('%H:%M'), 'price': b.close, 'dominant_side': 'A', 'volume': b.volume, 'cumulative_delta': b.delta} for b in active_trade_bars]
                    })
                    active_trade = None
                    active_trade_bars = []

            elif active_trade.direction == 'short':
                profit = active_trade.entry_price - bar.low
                loss   = bar.high - active_trade.entry_price
                if profit > active_trade.max_profit_pts:
                    active_trade.max_profit_pts = profit
                if not hasattr(active_trade, 'max_adverse_pts'):
                    active_trade.max_adverse_pts = 0.0
                if loss > active_trade.max_adverse_pts:
                    active_trade.max_adverse_pts = loss

                if bar.high >= active_trade.sl:
                    active_trade.status = 'stopped'
                    pnl_pts = active_trade.entry_price - active_trade.sl  # negative
                    pnl_usd = (pnl_pts * POINT_VALUE - COMMISSION) * CONTRACTS
                    trades_log.append({
                        'date': raw_date,
                        'time': active_trade.entry_ts.astimezone(NY_TZ).strftime('%H:%M'),
                        'exit_time': bar.timestamp.astimezone(NY_TZ).strftime('%H:%M'),
                        'setup': active_trade.setup_reason,
                        'direction': 'SHORT',
                        'entry': active_trade.entry_price,
                        'sl_pts': risk,
                        'mfe_pts': active_trade.max_profit_pts,
                        'mfe_r': round(active_trade.max_profit_pts / risk, 2) if risk > 0 else 0,
                        'mae_pts': getattr(active_trade, 'max_adverse_pts', 0.0),
                        'mae_r': round(getattr(active_trade, 'max_adverse_pts', 0.0) / risk, 2) if risk > 0 else 0,
                        'outcome': 'loss',
                        'pnl_pts': pnl_pts,
                        'pnl_usd': pnl_usd,
                        'half_size': active_trade.half_size,
                        'steps': [{'time_et': b.timestamp.astimezone(NY_TZ).strftime('%H:%M'), 'price': b.close, 'dominant_side': 'B', 'volume': b.volume, 'cumulative_delta': b.delta} for b in active_trade_bars]
                    })
                    active_trade = None
                    active_trade_bars = []
        
        closed_bars.append(bar)
        
        if not is_rth:
            continue
            
        # --- DYNAMIC CONTEXT ZONES ---
        # 1. Composite profile of the last 60 minutes to find LVNs
        start_comp_ts = bar.timestamp - timedelta(minutes=COMPOSITE_LOOKBACK_MIN)
        comp_bars = [b for b in closed_bars if b.timestamp >= start_comp_ts]
        
        lvn_zones = []
        if comp_bars:
            session_vp = build_profile_from_bars(comp_bars)
            if session_vp:
                lvn_zones = session_vp.lvn_levels
        
        # 2. Session Profile starting at 09:30 EST (14:30 UTC)
        rth_start_dt = bar.timestamp.replace(hour=14, minute=30, second=0, microsecond=0)
        rth_bars = [b for b in closed_bars if b.timestamp >= rth_start_dt]
        
        session_val = None
        session_vah = None
        if rth_bars:
            session_vp = build_profile_from_bars(rth_bars)
            if session_vp:
                session_val = session_vp.va_low
                session_vah = session_vp.va_high
                
        # --- PATTERN DETECTION ---
        if i >= 1 and active_trade is None:
            c1 = closed_bars[-2]
            c2 = closed_bars[-1]
            
            # Check Bullish (Long) Setup
            is_bullish, reason = detect_bullish_setup(
                c1, c2, 
                lvn_zones=lvn_zones, 
                session_val=session_val, 
                delta_threshold=-ABSORPTION_DELTA_LIMIT, 
                range_points=RANGE_POINTS,
                proximity_pts=PROXIMITY_PTS
            )
            
            if is_bullish and daily_trade_count < 2:
                # 1. Entry price calculation (pulled back to C1 close)
                entry_p = c1.close if ENTRY_MODE == 'limit' else c2.close
                
                # 2. Stop loss price calculation
                if STOP_TYPE == 'swing_low' and len(closed_bars) >= 3:
                    local_low = min(b.low for b in closed_bars[-3:])
                    sl_p = local_low - 1.0
                else:
                    sl_p = c1.low - STOP_BUFFER
                
                risk = entry_p - sl_p
                if risk < MIN_SL_POINTS:
                    sl_p = entry_p - MIN_SL_POINTS
                    risk = MIN_SL_POINTS
                
                is_half_size = (daily_trade_count == 1)  # 2nd trade of the day = half size
                active_trade = ActiveTrade(
                    direction='long',
                    entry_price=entry_p,
                    entry_ts=c2.timestamp,
                    initial_sl=sl_p,
                    sl=sl_p,
                    risk_pts=risk
                )
                active_trade.setup_reason = "FST Long Setup: " + reason.split('(')[0].strip()
                active_trade.half_size = is_half_size
                active_trade.max_adverse_pts = 0.0
                active_trade_bars = [c2]
                daily_trade_count += 1
                size_label = "[HALF SIZE]" if is_half_size else "[FULL SIZE]"
                print(f"  [TRADE TRIGGERED] LONG at {entry_p:.2f} | Stop: {sl_p:.2f} | Reason: {reason} | Risk: {risk:.2f} pts | {size_label}")
                
    # Close any open trade at end of day — log full MFE to EOD
    if active_trade and active_trade.status == 'active':
        risk = active_trade.risk_pts
        pnl_pts = bars[-1].close - active_trade.entry_price if active_trade.direction == 'long' else active_trade.entry_price - bars[-1].close
        pnl_usd = (pnl_pts * POINT_VALUE - COMMISSION) * CONTRACTS
        trades_log.append({
            'date': raw_date,
            'time': active_trade.entry_ts.astimezone(NY_TZ).strftime('%H:%M'),
            'exit_time': '16:00',
            'setup': active_trade.setup_reason,
            'direction': active_trade.direction.upper(),
            'entry': active_trade.entry_price,
            'sl_pts': risk,
            'mfe_pts': active_trade.max_profit_pts,
            'mfe_r': round(active_trade.max_profit_pts / risk, 2) if risk > 0 else 0,
            'mae_pts': getattr(active_trade, 'max_adverse_pts', 0.0),
            'mae_r': round(getattr(active_trade, 'max_adverse_pts', 0.0) / risk, 2) if risk > 0 else 0,
            'outcome': 'eod_win' if pnl_pts > 0 else 'eod_loss',
            'pnl_pts': pnl_pts,
            'pnl_usd': pnl_usd,
            'half_size': active_trade.half_size,
            'steps': [{'time_et': b.timestamp.astimezone(NY_TZ).strftime('%H:%M'), 'price': b.close, 'dominant_side': 'A' if active_trade.direction == 'long' else 'B', 'volume': b.volume, 'cumulative_delta': b.delta} for b in active_trade_bars]
        })
    return trades_log

def main():
    # Backtest B — Full Year 2025 MFE Analysis
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, "*2025*.trades.csv")))
    files = [
        f for f in all_files
        if "20250101" <= os.path.basename(f).split("-")[2].split(".")[0] <= "20251231"
    ]
    
    if not files:
        print("No trades.csv files found for 2025.")
        return
        
    all_trades = []
    start_time = time.time()
    
    for f in files:
        all_trades.extend(run_day_backtest(f))
        
    print("\n" + "="*80)
    print("ENTRY QUALITY VALIDATION — Fixed Targets: 2R and 2.5R (No Trailing, No BE)")
    print("="*80)
    
    if not all_trades:
        print("No trades executed.")
        return
        
    df_trades = pd.DataFrame(all_trades)
    n_total = len(df_trades)
    n_loss  = (df_trades['outcome'] == 'loss').sum()
    n_eod_w = (df_trades['outcome'] == 'eod_win').sum()
    n_eod_l = (df_trades['outcome'] == 'eod_loss').sum()
    n_full  = (df_trades.get('half_size', False) == False).sum()
    n_half  = (df_trades.get('half_size', False) == True).sum()
    
    mfe_r   = df_trades['mfe_r']
    mae_r   = df_trades['mae_r']

    # MFE distribution — how far did each trade go in our favor?
    buckets = [2, 3, 4, 5, 6, 7]
    print(f"\n  {'MFE Distribution (True Max Excursion)':}")
    print(f"  {'Soglia':<12} {'Trade >= soglia':>16} {'%':>6}")
    print(f"  {'-'*12} {'-'*16} {'-'*6}")
    for r in buckets:
        n_above = (mfe_r >= r).sum()
        pct = n_above / n_total * 100
        bar = '#' * int(pct / 5)
        print(f"  >= {r}R        {n_above:>8} / {n_total:<5}  {pct:>5.1f}%  {bar}")

    avg_mfe_r_all   = mfe_r.mean()
    avg_mae_r_all   = mae_r.mean()
    avg_mfe_loss    = mfe_r[df_trades['outcome'] == 'loss'].mean()
    avg_mfe_eod_win = mfe_r[df_trades['outcome'] == 'eod_win'].mean() if n_eod_w > 0 else 0

    print(f"\n  Trade Eseguiti:       {n_total} ({n_full} full size | {n_half} half size)")
    print(f"  Loss (stop pieno):    {n_loss}")
    print(f"  Chiusi EOD (win):     {n_eod_w}")
    print(f"  Chiusi EOD (loss):    {n_eod_l}")
    print(f"  Media MFE tutti:      {avg_mfe_r_all:.2f}R")
    print(f"  Media MFE su loss:    {avg_mfe_loss:.2f}R  (quanto andavano su prima di tornare)")
    print(f"  Media MAE tutti:      {avg_mae_r_all:.2f}R")

    print("\nDettaglio Trade:")
    print(f"  {'Data':<10} {'Ora':>5} {'Size':>6} | {'MFE':>6}  {'MAE':>6} | Esito")
    print(f"  {'-'*10} {'-'*5} {'-'*6}   {'-'*6}  {'-'*6}   {'-'*20}")
    for row in df_trades.itertuples():
        mfe_r_v = getattr(row, 'mfe_r', 0)
        mae_r_v = getattr(row, 'mae_r', 0)
        mfe_pts_v = getattr(row, 'mfe_pts', 0)
        mae_pts_v = getattr(row, 'mae_pts', 0)
        outcome_str = str(row.outcome)
        half = getattr(row, 'half_size', False)
        size_tag = "HALF" if half else "FULL"
        icon = "[WIN]" if 'win' in outcome_str or 'eod_win' in outcome_str else "[LOSS]"
        print(f"  {row.date} {row.time} | {size_tag} | MFE:{mfe_pts_v:>6.1f}pt ({mfe_r_v:.1f}R) MAE:{mae_pts_v:>5.1f}pt ({mae_r_v:.1f}R) | {icon} {outcome_str}")
        
    # --- WRITE TRADES TO AGENT_MEMORY FOR DASHBOARD INJECTION ---
    output_dir = Path("C:/Users/Mauro/Documents/nq-backtest-clean/agent_memory")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "optimal_backtest_trades.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_trades, f, indent=2)
    print(f"\nSaved {len(all_trades)} trades to {output_file}")
    
    # --- AUTO RUN INJECTION ---
    print("Running dashboard injector...")
    try:
        # Import directly to call
        import sys
        sys.path.insert(0, r"C:\Users\Mauro\Documents\nq-backtest-clean")
        from scripts.inject_optimal_trades_to_localhost import inject
        inject()
        print("Dashboard data successfully updated!")
    except Exception as e:
        print(f"Error running dashboard injector: {e}")
        
    print("\nCOMPLETATO IN {:.2f}s".format(time.time() - start_time))

if __name__ == "__main__":
    main()


