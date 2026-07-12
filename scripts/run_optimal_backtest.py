import sys, os
import json
import pandas as pd
import numpy as np
from pathlib import Path
import pytz
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
CACHE_DIR = r"C:\Users\Mauro\Documents\nq-backtest-clean\cache_ohlc"
ET = pytz.timezone("America/New_York")
bars_cache = {}

class MockBar:
    def __init__(self, timestamp, open_, high, low, close):
        self.timestamp = timestamp
        self.open = open_
        self.high = high
        self.low = low
        self.close = close

def get_bars_for_date(date_str):
    if date_str in bars_cache:
        return bars_cache[date_str]
        
    cache_file = Path(CACHE_DIR) / f"{date_str}.csv"
    if cache_file.exists():
        try:
            df = pd.read_csv(cache_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            bars = []
            for _, row in df.iterrows():
                bars.append(MockBar(row['timestamp'].to_pydatetime(), row['open'], row['high'], row['low'], row['close']))
            bars_cache[date_str] = bars
            return bars
        except Exception as e:
            print(f"Error reading cache for {date_str}: {e}")
            
    candidates = list(Path(DATA_DIR).glob(f"*{date_str}*.csv"))
    if not candidates:
        return None
    try:
        # Load CSV using pandas and filter to action == 'T'
        df = pd.read_csv(candidates[0], usecols=['ts_event', 'action', 'price', 'size', 'symbol'])
        df = df[df['action'] == 'T'].copy()
        
        # Filter to front month outright futures
        outright = df[~df['symbol'].str.contains('-', na=False)]
        if not outright.empty:
            front_month = outright['symbol'].value_counts().idxmax()
            df = outright[outright['symbol'] == front_month].copy()
            
        df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
        
        # Resample to 1-minute bars in pandas (incredibly fast!)
        df = df.set_index('ts_event')
        bars_df = df['price'].resample('1Min').ohlc()
        
        # Save to cache file
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
        bars_df_clean = bars_df.dropna().reset_index()
        bars_df_clean.columns = ['timestamp', 'open', 'high', 'low', 'close']
        bars_df_clean.to_csv(cache_file, index=False)
        
        bars = []
        for ts, row in bars_df.iterrows():
            if pd.isna(row['open']):
                continue
            bars.append(MockBar(ts.to_pydatetime(), row['open'], row['high'], row['low'], row['close']))
            
        bars_cache[date_str] = bars
        return bars
    except Exception as e:
        print(f"Error loading bars for {date_str}: {e}")
        return None

def run_backtest():
    seq_file = Path('knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences.json')
    if not seq_file.exists():
        print(f"Error: {seq_file} not found.")
        return

    with open(seq_file, encoding='utf-8') as f:
        sequences = json.load(f)

    big_trades_cache = {}
    data_dir = Path('dashboard/public/data')

    # Convert to DataFrame and sort by date/time
    df = pd.DataFrame(sequences)
    df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['start_time'], format='%Y%m%d %H:%M')
    df = df.sort_values('datetime').reset_index(drop=True)
    df['entry_vol'] = df['steps'].apply(lambda x: x[-1]['volume'] if x else 0)

    print(f"Loaded and sorted {len(df)} sequences chronologically.")

    # Only Setup 1 and Setup 3 are active (structural setups)
    setups = {
        "Setup 1: trending_up (LONG)": {
            "cond": lambda r: r["seq_pattern"] == "trending_up",
            "direction": "long",
            "sl": 40.0,
            "tp": 55.0
        },
        "Setup 3: trending_down (SHORT)": {
            "cond": lambda r: r["seq_pattern"] == "trending_down",
            "direction": "short",
            "sl": 18.0,
            "tp": 65.0
        }
    }

    # Prop Firm Settings (MNQ: 2 contracts)
    initial_equity = 50000.0
    equity = initial_equity
    
    use_micro = True   # Set to True for Micro NQ (MNQ), False for Mini NQ (NQ)
    contracts = 3      # Number of contracts to trade
    
    point_value = 2.0 if use_micro else 20.0
    commission = 0.50 if use_micro else 2.50  # Commission per contract round turn

    print(f"Position Sizing: {contracts} contracts of {'MNQ' if use_micro else 'NQ'} (${point_value}/point, commission ${commission:.2f}/contract)")

    trades_executed = []
    daily_pnl = {}
    last_exit_datetime = None

    for idx, row in df.iterrows():
        # Check which setup triggers (if any)
        triggered_setup = None
        for name, setup in setups.items():
            if setup["cond"](row):
                triggered_setup = name
                setup_info = setup
                break

        if triggered_setup is None:
            continue

        # Volume Filter (Rule B: 80 - 150 or >= 500 contracts)
        vol = row['entry_vol']
        if not ((80 <= vol < 150) or (vol >= 500)):
            continue

        # Time Filter (Filter B): 09:30-11:00 and 12:30-13:30 NY Time
        time_parts = row["end_time"].split(':')
        h, m = int(time_parts[0]), int(time_parts[1])
        t_val = h * 60 + m
        is_morning = (9 * 60 + 30 <= t_val < 11 * 60)
        is_lunch_core = (12 * 60 + 30 <= t_val < 13 * 60 + 30)
        if not (is_morning or is_lunch_core):
            continue

        # Cumulative Delta Climax Filter: skip trade if absolute delta >= 1200
        last_step = row["steps"][-1] if row["steps"] else {}
        cum_delta = last_step.get("cumulative_delta", 0)
        if abs(cum_delta) >= 1200:
            continue

        # Contrary Big Trade Filter: skip trade if there is a contrary big trade >= 150 contracts
        # between the start of the sequence (Step 1) and the entry (Step 3/end_time)
        date_str = row["date"]
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        if date_str not in big_trades_cache:
            day_file = data_dir / f"{formatted_date}.json"
            if day_file.exists():
                try:
                    with open(day_file, encoding='utf-8') as f:
                        day_data = json.load(f)
                    big_trades_cache[date_str] = day_data.get("big_trades", [])
                except:
                    big_trades_cache[date_str] = []
            else:
                big_trades_cache[date_str] = []

        big_trades = big_trades_cache[date_str]
        steps = row["steps"]
        if steps:
            # Step 1 time
            step1_time_str = steps[0]["time_et"]
            dt_start = datetime.strptime(f"{date_str} {step1_time_str}", "%Y%m%d %H:%M")
            dt_start = ET.localize(dt_start)
            start_ts = int(dt_start.timestamp())
            
            # Entry/end_time
            entry_time_str = row["end_time"]
            dt_end = datetime.strptime(f"{date_str} {entry_time_str}", "%Y%m%d %H:%M")
            dt_end = ET.localize(dt_end)
            end_ts = int(dt_end.timestamp())
            
            direction = setup_info["direction"]
            contrary_side = 'B' if direction == "long" else 'A'
            
            has_contrary = False
            for bt in big_trades:
                if start_ts <= bt["time"] <= end_ts:
                    if bt["side"] == contrary_side and bt["size"] >= 150:
                        has_contrary = True
                        break
            if has_contrary:
                continue

        # Concurrency check: skip trade if we are already in a position
        entry_dt = pd.to_datetime(row["date"] + ' ' + row["end_time"], format='%Y%m%d %H:%M')
        entry_dt = ET.localize(entry_dt)
        if last_exit_datetime is not None and entry_dt < last_exit_datetime:
            continue

        direction = setup_info["direction"]
        sl = setup_info["sl"]
        tp = setup_info["tp"]

        # Realistic path-based evaluation using 1-minute bars
        date_str = row["date"]
        time_str = row["end_time"]
        entry_price = row["entry_price"]

        bars = get_bars_for_date(date_str)
        if not bars:
            continue

        # Find entry bar index
        entry_idx = -1
        for i, b in enumerate(bars):
            t_et = b.timestamp.astimezone(ET)
            if t_et.strftime("%H:%M") == time_str:
                entry_idx = i
                break

        if entry_idx == -1:
            continue

        pnl_pts = None
        outcome = None
        exit_time_str = None
        max_adverse_pts = 0.0

        # Scan subsequent bars (start from entry_idx + 1 to avoid lookback bias)
        for i in range(entry_idx + 1, len(bars)):
            bar = bars[i]
            t_et = bar.timestamp.astimezone(ET)

            # Close trade at EOD (16:00 New York time)
            if t_et.hour >= 16:
                outcome = "eod"
                exit_price = bar.close
                pnl_pts = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
                exit_time_str = t_et.strftime("%H:%M")
                
                # Update MAE
                if direction == "long":
                    max_adverse_pts = max(max_adverse_pts, entry_price - bar.low)
                else:
                    max_adverse_pts = max(max_adverse_pts, bar.high - entry_price)
                break

            high = bar.high
            low = bar.low

            if direction == "long":
                # Check Stop Loss first (conservative)
                if low <= entry_price - sl:
                    pnl_pts = -sl
                    outcome = "loss"
                    exit_time_str = t_et.strftime("%H:%M")
                    max_adverse_pts = sl
                    break
                elif high >= entry_price + tp + 0.25: # Require at least 1 tick (0.25pt) penetration
                    pnl_pts = tp
                    outcome = "win"
                    exit_time_str = t_et.strftime("%H:%M")
                    max_adverse_pts = max(max_adverse_pts, entry_price - low)
                    break
                else:
                    max_adverse_pts = max(max_adverse_pts, entry_price - low)
            else: # short
                # Check Stop Loss first (conservative)
                if high >= entry_price + sl:
                    pnl_pts = -sl
                    outcome = "loss"
                    exit_time_str = t_et.strftime("%H:%M")
                    max_adverse_pts = sl
                    break
                elif low <= entry_price - tp - 0.25: # Require at least 1 tick (0.25pt) penetration
                    pnl_pts = tp
                    outcome = "win"
                    exit_time_str = t_et.strftime("%H:%M")
                    max_adverse_pts = max(max_adverse_pts, high - entry_price)
                    break
                else:
                    max_adverse_pts = max(max_adverse_pts, high - entry_price)

        if outcome is None:
            last_bar = bars[-1]
            t_et = last_bar.timestamp.astimezone(ET)
            outcome = "eod"
            exit_price = last_bar.close
            pnl_pts = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
            exit_time_str = t_et.strftime("%H:%M")
            if direction == "long":
                max_adverse_pts = max(max_adverse_pts, entry_price - last_bar.low)
            else:
                max_adverse_pts = max(max_adverse_pts, last_bar.high - entry_price)

        # Apply slippage: 1.5 points NQ per trade
        slippage_pts = 1.5
        pnl_pts = pnl_pts - slippage_pts
        
        # Actual MAE in points includes slippage if stopped out
        max_adverse_pts = min(max_adverse_pts + slippage_pts, sl + slippage_pts)

        # Compute PnL with contract multiplier
        pnl_usd = ((pnl_pts * point_value) - commission) * contracts
        equity += pnl_usd

        trade_info = {
            "date": row["date"],
            "time": row["end_time"],
            "exit_time": exit_time_str,
            "setup": triggered_setup,
            "direction": direction.upper(),
            "entry": entry_price,
            "sl_pts": sl,
            "tp_pts": tp,
            "mae": row["mae_long_pts"] if direction == "long" else row["mae_short_pts"],
            "mfe": row["mfe_long_pts"] if direction == "long" else row["mfe_short_pts"],
            "mae_actual_pts": round(max_adverse_pts, 2),
            "outcome": outcome,
            "pnl_pts": round(pnl_pts, 2),
            "pnl_usd": round(pnl_usd, 2),
            "equity": round(equity, 2),
            "steps": row["steps"]
        }
        trades_executed.append(trade_info)

        # Update last exit datetime for concurrency lock
        exit_dt = pd.to_datetime(row["date"] + ' ' + exit_time_str, format='%Y%m%d %H:%M')
        exit_dt = ET.localize(exit_dt)
        if exit_dt < entry_dt:
            exit_dt = exit_dt + pd.Timedelta(days=1)
        last_exit_datetime = exit_dt

        daily_pnl[date_str] = daily_pnl.get(date_str, 0.0) + pnl_usd

    # Compute metrics
    total_trades = len(trades_executed)
    if total_trades == 0:
        print("No trades executed based on setup triggers.")
        return

    wins = sum(1 for t in trades_executed if t["pnl_usd"] > 0)
    losses = sum(1 for t in trades_executed if t["pnl_usd"] < 0)
    win_rate = (wins / total_trades) * 100

    total_pnl = sum(t["pnl_usd"] for t in trades_executed)
    gross_profit = sum(t["pnl_usd"] for t in trades_executed if t["pnl_usd"] > 0)
    gross_loss = abs(sum(t["pnl_usd"] for t in trades_executed if t["pnl_usd"] < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    # True Intraday Drawdown calculation with contracts multiplier
    peak = initial_equity
    current = initial_equity
    max_dd = 0.0
    
    equity_curve = [initial_equity]
    for t in trades_executed:
        # Intraday low during this trade
        mae_usd = ((t["mae_actual_pts"] * point_value) + commission) * contracts
        intraday_low = current - mae_usd
        
        # Check drawdown at intraday low
        dd_intraday = peak - intraday_low
        if dd_intraday > max_dd:
            max_dd = dd_intraday
            
        # Update current equity after trade closes
        current = t["equity"]
        equity_curve.append(current)
        if current > peak:
            peak = current
            
        # Check drawdown at trade close
        dd_closed = peak - current
        if dd_closed > max_dd:
            max_dd = dd_closed

    max_dd_pct = (max_dd / peak) * 100 if peak > 0 else 0.0

    print(f"\n=== BACKTEST COMPLETE (11 MONTHS - STRESSED PATH BASED) ===")
    print(f"Total Trades:     {total_trades}")
    print(f"Wins:             {wins}")
    print(f"Losses:           {losses}")
    print(f"Win Rate:         {win_rate:.2f}%")
    print(f"Total Profit/Loss: ${total_pnl:,.2f}")
    print(f"Profit Factor:    {profit_factor:.2f}")
    print(f"Max Intraday DD:  ${max_dd:,.2f} ({max_dd_pct:.2f}%)")
    print(f"Final Equity:     ${equity:,.2f}")

    # Save detailed trade logs
    output_dir = Path('agent_memory')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / 'optimal_backtest_trades.json', 'w', encoding='utf-8') as f:
        json.dump(trades_executed, f, indent=2)

    # Save markdown walkthrough
    walkthrough_content = f"""# Walkthrough Backtest Ottimizzato Bot di Esecuzione (Path Based)
Generato il: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

Questo documento descrive i risultati realistici del backtest del Bot di Esecuzione con simulazione barra-per-barra per NQ Futures su un periodo di **11 mesi**.

## Performance Report Globale (MNQ - {contracts} contratti)

*   **Capitale Iniziale**: $50,000.00
*   **Capitale Finale**: ${equity:,.2f}
*   **Profitto Netto**: **${total_pnl:,.2f}**
*   **Ritorno sul Capitale (RoC)**: {((equity - initial_equity) / initial_equity) * 100:.1f}%
*   **Max Drawdown**: ${max_dd:,.2f} ({max_dd_pct:.2f}%)
*   **Profit Factor**: {profit_factor:.2f}
*   **Trade Totali Eseguiti**: {total_trades}
*   **Win Rate**: {win_rate:.2f}% (Wins: {wins} | Losses: {losses})

## Performance per Setup Singolo

| Setup | N. Trade | Wins | Losses | P&L (USD) |
| :--- | :---: | :---: | :---: | :---: |
"""
    # Count stats per setup
    setup_stats = {}
    for t in trades_executed:
        s_name = t["setup"]
        if s_name not in setup_stats:
            setup_stats[s_name] = {"n": 0, "wins": 0, "losses": 0, "pnl": 0.0}
        setup_stats[s_name]["n"] += 1
        if t["pnl_usd"] > 0:
            setup_stats[s_name]["wins"] += 1
        else:
            setup_stats[s_name]["losses"] += 1
        setup_stats[s_name]["pnl"] += t["pnl_usd"]

    for s_name, stats in setup_stats.items():
        walkthrough_content += f"| {s_name} | {stats['n']} | {stats['wins']} | {stats['losses']} | ${stats['pnl']:,.2f} |\n"

    walkthrough_content += """
## Conclusione
Il backtest simulato barra-per-barra (path-based) riflette l'esatta esecuzione del bot, filtrata per volumi e adattata per il superamento controllato di sfide Pro Firm.
"""
    
    with open(output_dir / 'optimal_backtest_walkthrough.md', 'w', encoding='utf-8') as f:
        f.write(walkthrough_content)
        
    print("Optimal backtest walkthrough saved to agent_memory/optimal_backtest_walkthrough.md")

if __name__ == '__main__':
    run_backtest()

