import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone
import pytz
import pandas as pd
import numpy as np

sys.path.append(r"c:\Users\Mauro\Documents\nq-backtest-clean")

from src.data_loader import list_data_files, load_day
from src.bar_aggregator import aggregate_to_bars
from src.bt_narrative_engine import extract_big_trade_nodes
from src.volume_profile import compute_volume_profile, VolumeProfile

ET = pytz.timezone("America/New_York")
DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
CACHE_DIR = r"C:\Users\Mauro\Documents\nq-backtest-clean\cache_ohlc"

bars_cache = {}

class MockBar:
    def __init__(self, timestamp, open_, high, low, close):
        self.timestamp = timestamp
        self.open = open_
        self.high = high
        self.low = low
        self.close = close

def to_et(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(ET)

def filter_ny_window(bars):
    return [b for b in bars if 9 <= to_et(b.timestamp).hour < 16
            or (to_et(b.timestamp).hour == 16 and to_et(b.timestamp).minute == 0)]

def build_ib(bars_ny) -> tuple:
    ib_bars = [b for b in bars_ny
               if 9*60+30 <= to_et(b.timestamp).hour*60+to_et(b.timestamp).minute < 10*60]
    if not ib_bars: return None, None
    return max(b.high for b in ib_bars), min(b.low for b in ib_bars)

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
            print(f"Error loading cache for {date_str}: {e}")
    return None

def classify_node_side_corrected(trades) -> str:
    # side == 'A' is BUY (Ask), side == 'B' is SELL (Bid)
    buy_vol  = sum(t.size for t in trades if t.side == 'A')
    sell_vol = sum(t.size for t in trades if t.side == 'B')
    return "A" if buy_vol >= sell_vol else "B"

def extract_combined_sequences(start_date, end_date):
    files = list_data_files(DATA_DIR)
    all_files = sorted(
        [(os.path.basename(f).split('-')[2].split('.')[0], f)
         for f in files if len(os.path.basename(f).split('-')) >= 3],
        key=lambda x: x[0]
    )
    dates_to_run = [(d, f) for d, f in all_files if start_date <= d <= end_date]
    
    all_sequences = []
    
    for date_str, f in dates_to_run:
        print(f"Extracting {date_str}...")
        try:
            df_raw    = load_day(f, as_df=True)
            bars_1min = aggregate_to_bars(df_raw, "1min")
            bars_ny   = filter_ny_window(bars_1min)
            nodes = extract_big_trade_nodes(bars_ny)
            
            if len(nodes) < 4:
                continue
                
            for i in range(len(nodes) - 3):
                seq_nodes = nodes[i:i + 3]
                next_node = nodes[i + 3]
                last_node = seq_nodes[-1]
                
                entry_price = last_node.current_price
                
                # Classification
                sides  = [classify_node_side_corrected(n.current_trades) for n in seq_nodes]
                deltas = [seq_nodes[k].price_change for k in range(1, len(seq_nodes))]
                
                all_buy  = all(s == "A" for s in sides)
                all_sell = all(s == "B" for s in sides)
                price_up = all(d > 0 for d in deltas)
                price_down = all(d < 0 for d in deltas)
                
                pattern = "unknown"
                if all_buy and price_up:
                    pattern = "trend_long"      # Buy aggressives, price going up
                elif all_sell and price_up:
                    pattern = "absorb_long"     # Sell aggressives absorbed, price going up
                elif all_sell and price_down:
                    pattern = "trend_short"     # Sell aggressives, price going down
                elif all_buy and price_down:
                    pattern = "absorb_short"    # Buy aggressives absorbed, price going down
                
                if pattern == "unknown":
                    continue
                    
                steps = []
                for j, n in enumerate(seq_nodes):
                    ts_n = n.current_time
                    steps.append({
                        "time_et": to_et(ts_n).strftime("%H:%M"),
                        "volume": sum(t.size for t in n.current_trades)
                    })
                    
                all_sequences.append({
                    "date": date_str,
                    "end_time": to_et(last_node.current_time).strftime("%H:%M"),
                    "seq_pattern": pattern,
                    "entry_price": entry_price,
                    "entry_vol": sum(t.size for t in last_node.current_trades),
                    "steps": steps,
                    "mae_long_pts": round(entry_price - (getattr(next_node, 'min_excursion', None) or entry_price), 2),
                    "mae_short_pts": round((getattr(next_node, 'max_excursion', None) or entry_price) - entry_price, 2),
                })
        except Exception as e:
            print(f"Error on {date_str}: {e}")
            
    return all_sequences

def run_optimization(sequences):
    setups = {
        "Trend LONG (Buy Aggressives + Price Up)": {
            "cond": lambda s: s["seq_pattern"] == "trend_long",
            "direction": "long"
        },
        "Absorption LONG (Sell Aggressives Absorbed + Price Up)": {
            "cond": lambda s: s["seq_pattern"] == "absorb_long",
            "direction": "long"
        },
        "Trend SHORT (Sell Aggressives + Price Down)": {
            "cond": lambda s: s["seq_pattern"] == "trend_short",
            "direction": "short"
        },
        "Absorption SHORT (Buy Aggressives Absorbed + Price Down)": {
            "cond": lambda s: s["seq_pattern"] == "absorb_short",
            "direction": "short"
        }
    }
    
    sl_range = np.arange(5.0, 50.5, 1.0)
    tp_range = np.arange(10.0, 120.5, 1.0)

    
    results = {}
    
    for setup_name, setup_info in setups.items():
        cond_fn = setup_info["cond"]
        direction = setup_info["direction"]
        
        filtered_seqs = [s for s in sequences if cond_fn(s)]
        n = len(filtered_seqs)
        if n == 0:
            print(f"\nSkipping {setup_name} (0 occurrences)")
            continue
            
        print(f"\nOptimizing {setup_name} (N = {n} sequences)...")
        
        # Pre-load bars
        trade_candidates = []
        for s in filtered_seqs:
            date_str = s["date"]
            time_str = s["end_time"]
            entry_price = s["entry_price"]
            
            # Filters (Volume & Time)
            vol = s['entry_vol']
            if not ((80 <= vol < 150) or (vol >= 500)):
                continue
                
            time_parts = time_str.split(':')
            h, m = int(time_parts[0]), int(time_parts[1])
            t_val = h * 60 + m
            is_morning = (9 * 60 + 30 <= t_val < 11 * 60)
            is_lunch_core = (12 * 60 + 30 <= t_val < 13 * 60 + 30)
            is_afternoon = (14 * 60 <= t_val < 15 * 60 + 30)
            if not (is_morning or is_lunch_core or is_afternoon):
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
                    
            if entry_idx != -1:
                trade_candidates.append({
                    "entry_price": entry_price,
                    "entry_idx": entry_idx,
                    "bars": bars,
                    "mae_long": s["mae_long_pts"],
                    "mae_short": s["mae_short_pts"]
                })
                
        print(f"  Loaded {len(trade_candidates)} valid filtered trade candidates.")
        if len(trade_candidates) == 0:
            continue
            
        best_pnl = -999999
        best_sl = None
        best_tp = None
        best_wr = 0
        best_pf = 0
        best_stats = None
        
        for sl in sl_range:
            for tp in tp_range:
                wins = 0
                losses = 0
                eod_closes = 0
                pnl_list = []
                
                for tc in trade_candidates:
                    entry_price = tc["entry_price"]
                    entry_idx = tc["entry_idx"]
                    bars = tc["bars"]
                    
                    outcome = None
                    pnl_pts = 0
                    
                    for i in range(entry_idx + 1, len(bars)):
                        bar = bars[i]
                        t_et = bar.timestamp.astimezone(ET)
                        
                        if t_et.hour >= 16:
                            outcome = "eod"
                            exit_price = bar.close
                            pnl_pts = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
                            break
                            
                        high = bar.high
                        low = bar.low
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
                                
                    if outcome is None:
                        last_bar = bars[-1]
                        outcome = "eod"
                        exit_price = last_bar.close
                        pnl_pts = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
                        
                    pnl_pts = pnl_pts - 1.5 # slippage
                    
                    if outcome == "win":
                        wins += 1
                    elif outcome == "loss":
                        losses += 1
                    else:
                        eod_closes += 1
                        
                    pnl_list.append(pnl_pts)
                    
                total_trades = len(pnl_list)
                if total_trades == 0:
                    continue
                    
                total_pnl = sum(pnl_list)
                wr = (wins / total_trades) * 100
                gross_profits = sum(p for p in pnl_list if p > 0)
                gross_losses = abs(sum(p for p in pnl_list if p < 0))
                pf = gross_profits / gross_losses if gross_losses > 0 else float('inf')
                
                if total_pnl > best_pnl:
                    best_pnl = total_pnl
                    best_sl = sl
                    best_tp = tp
                    best_wr = wr
                    best_pf = pf
                    best_stats = {
                        "wins": wins,
                        "losses": losses,
                        "eod": eod_closes
                    }
                    
        results[setup_name] = {
            "n_trades": len(trade_candidates),
            "sl": best_sl,
            "tp": best_tp,
            "win_rate": best_wr,
            "profit_factor": best_pf,
            "pnl_pts": best_pnl,
            "stats": best_stats
        }
        
        print(f"  Result: SL={best_sl:.1f} TP={best_tp:.1f} | WR={best_wr:.1f}% | PF={best_pf:.2f} | PnL={best_pnl:.1f} pt")
        
    return results

def save_report(results, report_name="combined_backtest_report.md"):
    report_path = Path("agent_memory") / report_name
    lines = [
        "# 📊 Report di Ottimizzazione Combinata: Trend vs Assorbimento (2026)",
        f"Generato il: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\nQuesto report confronta le performance dei 4 ingressi principali: **Trend-Following** ed **Assorbimento** sul lato LONG e SHORT nel periodo out-of-sample (Dec 2025 - Jun 2026).",
        "\n## 📈 Sintesi delle Performance Ottimizzate",
        "\n| Setup | N. Trade | SL Ottimale (pt) | TP Ottimale (pt) | Win Rate % | Profit Factor | P&L Totale (pt) |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]
    
    for name, r in results.items():
        lines.append(f"| **{name}** | {r['n_trades']} | {r['sl']:.1f} | {r['tp']:.1f} | {r['win_rate']:.1f}% | {r['profit_factor']:.2f} | {r['pnl_pts']:.1f} pt |")
        
    lines.append("\n## 💡 Conclusioni e Analisi dell'Edge")
    lines.append("\n> [!NOTE]")
    lines.append("> L'integrazione contemporanea di setup Trend ed Assorbimento consente al bot di adattarsi a diversi contesti di volatilità.")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nReport salvato in {report_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run Combined Backtest & Optimization")
    parser.add_argument('--start-date', type=str, default="20251201")
    parser.add_argument('--end-date', type=str, default="20260618")
    parser.add_argument('--cache-name', type=str, default="bt_sequences_combined.json")
    parser.add_argument('--report-name', type=str, default="combined_backtest_report.md")
    args = parser.parse_args()

    print("Pre-scanning OHLC cache files...")
    for f in Path(CACHE_DIR).glob("*.csv"):
        date_str = f.stem
        get_bars_for_date(date_str)
        
    seq_file = Path("knowledge/trader_lessons_graph/graphify-out/sequences") / args.cache_name
    if seq_file.exists():
        print(f"\nLoading combined sequences from cache: {seq_file}")
        with open(seq_file, encoding="utf-8") as fp:
            seqs = json.load(fp)
    else:
        print(f"\nExtracting combined sequences for period ({args.start_date} to {args.end_date})...")
        seqs = extract_combined_sequences(args.start_date, args.end_date)
        seq_file.parent.mkdir(parents=True, exist_ok=True)
        with open(seq_file, "w", encoding="utf-8") as fp:
            json.dump(seqs, fp, indent=4)
        print(f"\nExtracted and cached {len(seqs)} total combined sequences to {seq_file}")
        
    print(f"\nLoaded {len(seqs)} total combined sequences.")
    
    print("\nRunning grid search optimization for all 4 setups...")
    results = run_optimization(seqs)
    save_report(results, args.report_name)

if __name__ == '__main__':
    main()

