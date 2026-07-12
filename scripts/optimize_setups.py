import json
import numpy as np
import pandas as pd
from pathlib import Path
import pytz

DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"
ET = pytz.timezone("America/New_York")
bars_cache = {}

class MockBar:
    def __init__(self, timestamp, open_, high, low, close):
        self.timestamp = timestamp
        self.open = open_
        self.high = high
        self.low = low
        self.close = close

CACHE_DIR = r"C:\Users\Mauro\Documents\nq-backtest-clean\cache_ohlc"
csv_lookup = None

def pre_scan_csvs():
    global csv_lookup
    if csv_lookup is not None:
        return
    csv_lookup = {}
    for f in Path(DATA_DIR).glob("*.csv"):
        parts = f.name.split("-")
        if len(parts) >= 3:
            d_str = parts[2].split(".")[0]
            csv_lookup[d_str] = f

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

    pre_scan_csvs()
    csv_path = csv_lookup.get(date_str)
    if not csv_path:
        return None
    try:
        df = pd.read_csv(csv_path, usecols=['ts_event', 'action', 'price', 'size', 'symbol'])
        df = df[df['action'] == 'T'].copy()
        
        outright = df[~df['symbol'].str.contains('-', na=False)]
        if not outright.empty:
            front_month = outright['symbol'].value_counts().idxmax()
            df = outright[outright['symbol'] == front_month].copy()
            
        df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
        df = df.set_index('ts_event')
        bars_df = df['price'].resample('1Min').ohlc().dropna().reset_index()
        bars_df.columns = ['timestamp', 'open', 'high', 'low', 'close']
        
        records = bars_df.to_dict(orient='records')
        bars = [MockBar(row['timestamp'].to_pydatetime(), row['open'], row['high'], row['low'], row['close']) for row in records]
        bars_cache[date_str] = bars
        return bars
    except Exception as e:
        print(f"Error loading bars for {date_str}: {e}")
        return None

def optimize():
    seq_file = Path('knowledge/trader_lessons_graph/graphify-out/sequences/bt_sequences.json')
    if not seq_file.exists():
        print(f"Error: {seq_file} not found.")
        return

    with open(seq_file, encoding='utf-8') as f:
        sequences = json.load(f)

    print(f"Loaded {len(sequences)} sequences from {seq_file}")

    # Define the 5 core profitable setups
    setups = {
        "Setup 1: trending_up (LONG)": {
            "cond": lambda s: s.get("seq_pattern") == "trending_up",
            "direction": "long"
        },
        "Setup 2: 3x BUY (LONG)": {
            "cond": lambda s: s.get("seq_sides") == "B->B->B",
            "direction": "long"
        },
        "Setup 3: trending_down (SHORT)": {
            "cond": lambda s: s.get("seq_pattern") == "trending_down",
            "direction": "short"
        },
        "Setup 4: 3x SELL (SHORT)": {
            "cond": lambda s: s.get("seq_sides") == "A->A->A",
            "direction": "short"
        },
        "Setup 5: accumulation_breakup (LONG)": {
            "cond": lambda s: s.get("seq_pattern") == "accumulation_breakup",
            "direction": "long"
        }
    }

    # Grid search parameters
    sl_range = np.arange(5.0, 30.5, 1.0)
    tp_range = np.arange(10.0, 100.5, 1.0)



    results = {}

    for setup_name, setup_info in setups.items():
        cond_fn = setup_info["cond"]
        direction = setup_info["direction"]
        
        filtered_seqs = [s for s in sequences if cond_fn(s)]
        n = len(filtered_seqs)
        if n == 0:
            print(f"Skipping {setup_name} (0 occurrences)")
            continue

        print(f"Optimizing {setup_name} (N = {n} sequences)...")

        # Pre-load bars for dates to make grid search extremely fast
        print("  Pre-loading bars...")
        trade_candidates = []
        for s in filtered_seqs:
            date_str = s["date"]
            time_str = s["end_time"]
            entry_price = s["entry_price"]
            
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
                    "date": date_str,
                    "target_price_delta": s["target_price_delta"]
                })

        print(f"  Loaded {len(trade_candidates)} valid trade periods out of {n}.")

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
                    
                    # Simulating path from entry_idx + 1 (Lookback bias fixed)
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
                            elif high >= entry_price + tp + 0.25: # Target penetration check
                                pnl_pts = tp
                                outcome = "win"
                                break
                        else: # short
                            if high >= entry_price + sl:
                                pnl_pts = -sl
                                outcome = "loss"
                                break
                            elif low <= entry_price - tp - 0.25: # Target penetration check
                                pnl_pts = tp
                                outcome = "win"
                                break
                                
                    if outcome is None:
                        last_bar = bars[-1]
                        outcome = "eod"
                        exit_price = last_bar.close
                        pnl_pts = (exit_price - entry_price) if direction == "long" else (entry_price - exit_price)
                        
                    # Apply slippage (1.5 points NQ per trade)
                    pnl_pts = pnl_pts - 1.5
                        
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
                        "eod": eod_closes,
                        "avg_pnl": total_pnl / total_trades,
                        "total_trades": total_trades
                    }

        results[setup_name] = {
            "sl": best_sl,
            "tp": best_tp,
            "pnl": round(best_pnl, 1),
            "wr": round(best_wr, 1),
            "pf": round(best_pf, 2) if best_pf != float('inf') else "∞",
            "stats": best_stats
        }

    # Generate Markdown Report
    report_path = Path('agent_memory/optimal_setups_report.md')
    md_content = f"""# Report Ottimizzazione Setups (11 Mesi)
Generato il: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}

Questo report mostra i parametri ottimali di **Stop Loss (SL)** e **Take Profit (TP)** in punti NQ per ciascuno dei setup ad alta probabilità, ottimizzati su base percorso (senza bias di lookback) con tenuta fino a fine giornata (EOD).

## Sintesi dei Risultati Ottimizzati

| Setup | N. Trade | SL Ottimale (pt) | TP Ottimale (pt) | Win Rate % | Profit Factor | P&L Totale (pt) | Avg P&L (pt) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""

    for name, res in results.items():
        st = res["stats"]
        md_content += f"| **{name}** | {st['total_trades']} | {res['sl']:.1f} | {res['tp']:.1f} | {res['wr']}% | {res['pf']} | {res['pnl']}{'+' if res['pnl']>0 else ''} | {st['avg_pnl']:.2f} |\n"

    md_content += """
## Dettagli Esecuzione per Setup

"""
    for name, res in results.items():
        st = res["stats"]
        md_content += f"""### {name}
*   **Stop Loss consigliato**: {res['sl']:.1f} punti NQ
*   **Take Profit consigliato**: {res['tp']:.1f} punti NQ
*   **Win Rate**: {res['wr']}% (Wins: {st['wins']} | Losses: {st['losses']} | EOD Closes: {st['eod']})
*   **Profit Factor**: {res['pf']}
*   **PnL Totale**: {res['pnl']:.1f} punti (equivalenti a **${res['pnl'] * 20:,.2f}** per contratto NQ standard, o **${res['pnl'] * 2:,.2f}** per MNQ)
*   **Media per trade**: {st['avg_pnl']:.2f} punti NQ

---
"""

    report_path.write_text(md_content, encoding='utf-8')
    print(f"Report saved to {report_path}")

    print("\n=== OPTIMIZATION SUMMARY ===")
    for name, res in results.items():
        print(f"{name}: SL={res['sl']} TP={res['tp']} | WR={res['wr']}% | PnL={res['pnl']} pt | PF={res['pf']}")

if __name__ == '__main__':
    optimize()

