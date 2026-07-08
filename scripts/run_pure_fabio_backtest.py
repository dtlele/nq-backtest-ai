import os
import json
import glob
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Project directories
ROOT = Path("C:/Users/Mauro/Documents/nq-backtest")
DATA_DIR = ROOT / "dashboard" / "public" / "data"

class PureFabioBacktester:
    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = data_dir
        self.trades = []

    def get_session_files(self):
        """Get all session JSON files matching YYYY-MM-DD.json format."""
        files = glob.glob(os.path.join(self.data_dir, "202*-*-*.json"))
        return sorted([Path(f) for f in files])

    def parse_session(self, filepath):
        """Parse a single session JSON file and return its data."""
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_backtest(self):
        session_files = self.get_session_files()
        print(f"Found {len(session_files)} session files to backtest.")

        for fpath in session_files:
            try:
                session_data = self.parse_session(fpath)
                self.backtest_session(session_data)
            except Exception as e:
                print(f"Error backtesting session {fpath.name}: {e}")
                
        self.generate_report()

    def backtest_session(self, data):
        date_str = data["date"]
        m1_bars = data.get("m1_ny", [])
        big_trades = data.get("big_trades", [])
        ib = data.get("ib")
        vwap_list = data.get("vwap", [])
        dev_va_list = data.get("dev_va", [])

        if not m1_bars or not ib:
            return

        ib_high = ib["high"]
        ib_low = ib["low"]

        # Build lookup tables
        vwap_dict = {item["time"]: item["value"] for item in vwap_list if "time" in item and "value" in item}
        dev_va_dict = {item["time"]: item for item in dev_va_list if "time" in item}

        # Convert big trades to a pandas DataFrame
        bt_df = pd.DataFrame(big_trades)
        if not bt_df.empty:
            bt_df['datetime'] = pd.to_datetime(bt_df['time'], unit='s', utc=True)
            bt_df.set_index('time', inplace=True, drop=False)
        
        active_trade = None
        recent_volumes = []
        recent_bars = []

        for bar in m1_bars:
            t_epoch = bar["time"]
            dt_utc = datetime.fromtimestamp(t_epoch, tz=timezone.utc)
            
            try:
                import pytz
                dt_ny = dt_utc.astimezone(pytz.timezone("America/New_York"))
            except Exception:
                dt_ny = dt_utc - timedelta(hours=5)

            bar_hour = dt_ny.hour
            bar_minute = dt_ny.minute
            bar_time_str = f"{bar_hour:02d}:{bar_minute:02d}"

            # Only trade during RTH session (10:30 to 15:30)
            is_rth_trade_window = (
                (bar_hour == 10 and bar_minute >= 30) or
                (11 <= bar_hour < 12) or
                (13 <= bar_hour < 15) or
                (bar_hour == 15 and bar_minute < 30)
            )

            # Manage volume history
            vol = bar.get("volume", 0)
            recent_volumes.append(vol)
            if len(recent_volumes) > 10:
                recent_volumes.pop(0)

            recent_bars.append(bar)
            if len(recent_bars) > 5:
                recent_bars.pop(0)

            # Fetch VAH, VAL, POC and VWAP
            dev_va = dev_va_dict.get(t_epoch)
            vah = dev_va["vah"] if dev_va else None
            val = dev_va["val"] if dev_va else None
            poc = dev_va["poc"] if dev_va else None
            vwap = vwap_dict.get(t_epoch)

            # -----------------------------------------------------------------
            # 1. EVALUATE ACTIVE TRADE EXITS & TRAILING STOP UPDATES
            # -----------------------------------------------------------------
            if active_trade:
                high_price = bar["high"]
                low_price = bar["low"]

                if active_trade["direction"] == "long":
                    # Check Stop Loss
                    if low_price <= active_trade["stop_loss"]:
                        exit_price = active_trade["stop_loss"]
                        pnl = (exit_price - active_trade["entry_price"]) * active_trade["contracts"] * 2.0
                        self.trades.append({
                            "date": date_str,
                            "entry_time": active_trade["entry_time_str"],
                            "exit_time": bar_time_str,
                            "direction": "long",
                            "entry": active_trade["entry_price"],
                            "exit": exit_price,
                            "pnl": pnl,
                            "type": "stopped"
                        })
                        active_trade = None
                        continue

                    # End of Day Cutoff (15:55 EST)
                    if bar_hour == 15 and bar_minute >= 55:
                        exit_price = bar["close"]
                        pnl = (exit_price - active_trade["entry_price"]) * active_trade["contracts"] * 2.0
                        self.trades.append({
                            "date": date_str,
                            "entry_time": active_trade["entry_time_str"],
                            "exit_time": bar_time_str,
                            "direction": "long",
                            "entry": active_trade["entry_price"],
                            "exit": exit_price,
                            "pnl": pnl,
                            "type": "cutoff"
                        })
                        active_trade = None
                        continue

                    # --- STRUCTURAL TRAILING STOP LOGIC FOR LONG ---
                    # Trail stop 15.0 points behind newly appearing Big Buy Trades
                    if not bt_df.empty:
                        bt_now = bt_df[(bt_df['time'] >= t_epoch) & (bt_df['time'] < t_epoch + 60)]
                        buy_trades = bt_now[(bt_now['side'] == 'B') & (bt_now['size'] >= 200)]
                        if not buy_trades.empty:
                            max_buy_price = buy_trades['price'].max()
                            new_sl = max_buy_price - 15.0
                            if new_sl > active_trade["stop_loss"] and new_sl < bar["close"]:
                                active_trade["stop_loss"] = new_sl

                    # Trail stop 15.0 points behind rising dynamic VAL
                    if val is not None:
                        new_sl_val = val - 15.0
                        if new_sl_val > active_trade["stop_loss"] and new_sl_val < bar["close"]:
                            active_trade["stop_loss"] = new_sl_val

                elif active_trade["direction"] == "short":
                    # Check Stop Loss
                    if high_price >= active_trade["stop_loss"]:
                        exit_price = active_trade["stop_loss"]
                        pnl = (active_trade["entry_price"] - exit_price) * active_trade["contracts"] * 2.0
                        self.trades.append({
                            "date": date_str,
                            "entry_time": active_trade["entry_time_str"],
                            "exit_time": bar_time_str,
                            "direction": "short",
                            "entry": active_trade["entry_price"],
                            "exit": exit_price,
                            "pnl": pnl,
                            "type": "stopped"
                        })
                        active_trade = None
                        continue

                    # End of Day Cutoff (15:55 EST)
                    if bar_hour == 15 and bar_minute >= 55:
                        exit_price = bar["close"]
                        pnl = (active_trade["entry_price"] - exit_price) * active_trade["contracts"] * 2.0
                        self.trades.append({
                            "date": date_str,
                            "entry_time": active_trade["entry_time_str"],
                            "exit_time": bar_time_str,
                            "direction": "short",
                            "entry": active_trade["entry_price"],
                            "exit": exit_price,
                            "pnl": pnl,
                            "type": "cutoff"
                        })
                        active_trade = None
                        continue

                    # --- STRUCTURAL TRAILING STOP LOGIC FOR SHORT ---
                    # Trail stop 15.0 points above newly appearing Big Sell Trades
                    if not bt_df.empty:
                        bt_now = bt_df[(bt_df['time'] >= t_epoch) & (bt_df['time'] < t_epoch + 60)]
                        sell_trades = bt_now[(bt_now['side'] == 'A') & (bt_now['size'] >= 200)]
                        if not sell_trades.empty:
                            min_sell_price = sell_trades['price'].min()
                            new_sl = min_sell_price + 15.0
                            if new_sl < active_trade["stop_loss"] and new_sl > bar["close"]:
                                active_trade["stop_loss"] = new_sl

                    # Trail stop 15.0 points above falling dynamic VAH
                    if vah is not None:
                        new_sl_vah = vah + 15.0
                        if new_sl_vah < active_trade["stop_loss"] and new_sl_vah > bar["close"]:
                            active_trade["stop_loss"] = new_sl_vah

            # -----------------------------------------------------------------
            # 2. SCAN FOR NEW SETUPS (IF NOT IN A TRADE)
            # -----------------------------------------------------------------
            if not active_trade and is_rth_trade_window and len(recent_volumes) >= 10 and len(recent_bars) >= 5 and val is not None and vah is not None and vwap is not None:
                
                # Check for a Big Buy/Sell Wall in the last 15 minutes
                big_buy_wall = None
                big_sell_wall = None
                
                if not bt_df.empty:
                    window_start = t_epoch - 15 * 60
                    bt_recent = bt_df[(bt_df['time'] >= window_start) & (bt_df['time'] <= t_epoch)]
                    if not bt_recent.empty:
                        walls = bt_recent.groupby(['price', 'side'])['size'].sum().reset_index()
                        
                        buy_walls = walls[(walls['side'] == 'B') & (walls['size'] >= 300)]
                        if not buy_walls.empty:
                            big_buy_wall = buy_walls.loc[buy_walls['size'].idxmax()]['price']

                        sell_walls = walls[(walls['side'] == 'A') & (walls['size'] >= 300)]
                        if not sell_walls.empty:
                            big_sell_wall = sell_walls.loc[sell_walls['size'].idxmax()]['price']

                # Average volume of last 10 bars
                avg_vol_10 = np.mean(recent_volumes[:-1])
                close_price = bar["close"]

                # -------------------------------------------------------------
                # SETUP 1: LONG (TREND IS BULLISH: price > vwap)
                # -------------------------------------------------------------
                if close_price > vwap:
                    # Test of support (VAL, POC, ib_low, ib_high, or Big Buy Wall)
                    is_near_support = (
                        abs(bar["low"] - val) <= 4.0 or
                        abs(bar["low"] - ib_low) <= 4.0 or
                        abs(bar["low"] - ib_high) <= 4.0 or
                        (poc is not None and abs(bar["low"] - poc) <= 4.0) or
                        (big_buy_wall is not None and abs(bar["low"] - big_buy_wall) <= 4.0)
                    )

                    if is_near_support:
                        # Scan last 3 bars for Absorption (Effort vs No Result)
                        absorption_found = False
                        abs_bar_low = 999999.0
                        for prev_bar in recent_bars[-3:]:
                            prev_vol = prev_bar.get("volume", 0)
                            prev_delta = prev_bar.get("delta", 0)
                            prev_range = prev_bar["high"] - prev_bar["low"]
                            if prev_range > 0:
                                lower_wick_ratio = (prev_bar["close"] - prev_bar["low"]) / prev_range
                                
                                if (prev_vol > 400 or prev_vol > 1.3 * avg_vol_10) and prev_delta <= -120 and lower_wick_ratio >= 0.35:
                                    absorption_found = True
                                    abs_bar_low = min(abs_bar_low, prev_bar["low"])
                                    break
                        
                        if absorption_found:
                            # Confirm with Ignition Bar (positive delta >= 150, close near high, above-avg volume)
                            curr_delta = bar.get("delta", 0)
                            curr_range = bar["high"] - bar["low"]
                            if curr_range > 0:
                                body_ratio = (bar["close"] - bar["low"]) / curr_range
                                avg_vol_5 = np.mean([b["volume"] for b in recent_bars[-5:-1]])
                                
                                # Increased ignition bar delta threshold to 150 contracts (real commitment)
                                if curr_delta >= 150 and body_ratio >= 0.55 and bar["volume"] > avg_vol_5:
                                    entry_price = bar["close"]
                                    sl_price = min(abs_bar_low, bar["low"]) - 1.5
                                    
                                    # Constrain SL distance
                                    sl_dist = entry_price - sl_price
                                    if sl_dist < 15.0:
                                        sl_price = entry_price - 15.0
                                    elif sl_dist > 50.0:
                                        sl_price = entry_price - 50.0

                                    active_trade = {
                                        "direction": "long",
                                        "entry_time": t_epoch,
                                        "entry_time_str": bar_time_str,
                                        "entry_price": entry_price,
                                        "stop_loss": sl_price,
                                        "contracts": 2,
                                        "initial_sl": sl_price
                                    }
                                    continue

                # -------------------------------------------------------------
                # SETUP 2: SHORT (TREND IS BEARISH: price < vwap)
                # -------------------------------------------------------------
                elif close_price < vwap:
                    # Test of resistance (VAH, POC, ib_high, ib_low, or Big Sell Wall)
                    is_near_resistance = (
                        abs(bar["high"] - vah) <= 4.0 or
                        abs(bar["high"] - ib_high) <= 4.0 or
                        abs(bar["high"] - ib_low) <= 4.0 or
                        (poc is not None and abs(bar["high"] - poc) <= 4.0) or
                        (big_sell_wall is not None and abs(bar["high"] - big_sell_wall) <= 4.0)
                    )

                    if is_near_resistance:
                        # Scan last 3 bars for Absorption (Effort vs No Result)
                        absorption_found = False
                        abs_bar_high = -1.0
                        for prev_bar in recent_bars[-3:]:
                            prev_vol = prev_bar.get("volume", 0)
                            prev_delta = prev_bar.get("delta", 0)
                            prev_range = prev_bar["high"] - prev_bar["low"]
                            if prev_range > 0:
                                upper_wick_ratio = (prev_bar["high"] - prev_bar["close"]) / prev_range
                                
                                if (prev_vol > 400 or prev_vol > 1.3 * avg_vol_10) and prev_delta >= 120 and upper_wick_ratio >= 0.35:
                                    absorption_found = True
                                    abs_bar_high = max(abs_bar_high, prev_bar["high"])
                                    break
                        
                        if absorption_found:
                            # Confirm with Ignition Bar (negative delta <= -150)
                            curr_delta = bar.get("delta", 0)
                            curr_range = bar["high"] - bar["low"]
                            if curr_range > 0:
                                body_ratio = (bar["high"] - bar["close"]) / curr_range
                                avg_vol_5 = np.mean([b["volume"] for b in recent_bars[-5:-1]])
                                
                                if curr_delta <= -150 and body_ratio >= 0.55 and bar["volume"] > avg_vol_5:
                                    entry_price = bar["close"]
                                    sl_price = max(abs_bar_high, bar["high"]) + 1.5
                                    
                                    sl_dist = sl_price - entry_price
                                    if sl_dist < 15.0:
                                        sl_price = entry_price + 15.0
                                    elif sl_dist > 50.0:
                                        sl_price = entry_price + 50.0

                                    active_trade = {
                                        "direction": "short",
                                        "entry_time": t_epoch,
                                        "entry_time_str": bar_time_str,
                                        "entry_price": entry_price,
                                        "stop_loss": sl_price,
                                        "contracts": 2,
                                        "initial_sl": sl_price
                                    }
                                    continue

    def generate_report(self):
        """Generate a summary report of the backtest results."""
        if not self.trades:
            print("No trades executed during the backtest.")
            # Write empty report to avoid errors
            out_file = ROOT / "output" / "pure_fabio_backtest_report.md"
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_text("# 📈 PURE FABIO STRATEGY BACKTEST REPORT\nNo trades executed.", encoding="utf-8")
            return

        df = pd.DataFrame(self.trades)
        total_trades = len(df)
        wins = df[df["pnl"] > 0]
        losses = df[df["pnl"] <= 0]
        win_rate = len(wins) / total_trades if total_trades > 0 else 0
        total_pnl = df["pnl"].sum()
        
        profit_factor = 0.0
        gross_profit = wins["pnl"].sum()
        gross_loss = abs(losses["pnl"].sum())
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = float('inf') if gross_profit > 0 else 0.0

        # Calculate max drawdown
        df['cum_pnl'] = df['pnl'].cumsum()
        cum_pnl = df['cum_pnl'].values
        running_max = np.maximum.accumulate(cum_pnl)
        drawdowns = running_max - cum_pnl
        max_dd = drawdowns.max()

        report_md = f"""# 📈 PURE FABIO STRATEGY BACKTEST REPORT
Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Strategy: Orderflow & AMT Scalping on NQ Futures (E-mini)
Risk Management: Trailing stop behind dynamic VAL/VAH and Big Trades (15.0 pts buffer). Trend Filter: VWAP.
Data Source: 1-minute footprint files (360+ sessions)

## 📊 Performance Summary
* **Total Trades**: {total_trades}
* **Win Rate**: {win_rate:.2%} ({len(wins)} Win / {len(losses)} Loss)
* **Total P&L**: ${total_pnl:,.2f} (base size: 2 MNQ contracts)
* **Profit Factor**: {profit_factor:.2f}
* **Max Drawdown**: ${max_dd:,.2f}
* **Average P&L per Trade**: ${df["pnl"].mean():,.2f}

## 📋 Trade Statistics
* **Average Win**: ${wins["pnl"].mean():,.2f}
* **Average Loss**: ${losses["pnl"].mean():,.2f}
* **Largest Win**: ${df["pnl"].max():,.2f}
* **Largest Loss**: ${df["pnl"].min():,.2f}

## 📂 Trade Log Snippet (Last 20 Trades)
"""
        report_md += df.tail(20)[["date", "entry_time", "exit_time", "direction", "entry", "exit", "pnl", "type"]].to_markdown(index=False)

        # Write to output file
        out_file = ROOT / "output" / "pure_fabio_backtest_report.md"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(report_md, encoding="utf-8")
        
        print("\n" + "="*50)
        print("BACKTEST RESULTS SUMMARY (STRUCTURAL TRAILING RISK):")
        print("="*50)
        print(f"Total Trades: {total_trades}")
        print(f"Win Rate:     {win_rate:.2%}")
        print(f"Total P&L:    ${total_pnl:,.2f}")
        print(f"Profit Factor: {profit_factor:.2f}")
        print(f"Max Drawdown:  ${max_dd:,.2f}")
        print(f"Report saved to: {out_file.absolute()}")
        print("="*50)

if __name__ == "__main__":
    backtester = PureFabioBacktester()
    backtester.run_backtest()
