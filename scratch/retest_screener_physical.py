"""
HONEST Physical Stop Floor Simulation v2

For each trade stopped out (exit_reason == 'stop'), we load the ACTUAL tick data
for that day and check:
  - What was the REAL low (for longs) or REAL high (for shorts) reached
    DURING the trade's lifetime (entry_time to exit_time and beyond, max 2 hours)?
  - Would the wider 40-tick stop have been hit by the actual price action?
  - If NOT, we check if price reached the TARGET in the subsequent bars.

This uses real OHLCV bars — no assumptions.
"""
import json, csv, math
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytz

MEMORY_DIR  = Path("agent_memory")
TRADES_FILE = MEMORY_DIR / "trades_log.jsonl"
DATA_DIR    = Path(r"C:\Users\Mauro\Documents\databento-data")
TICK_SIZE   = 0.25
TICK_VAL    = 0.50
MIN_STOP_TICKS = 40.0
ET = pytz.timezone("America/New_York")

def load_bars_for_date(date_str: str) -> list[dict]:
    """Load 1-min aggregated bars from raw CSV for a given date (YYYY-MM-DD)."""
    yyyymmdd = date_str.replace("-", "")
    pattern = f"glbx-mdp3-{yyyymmdd}.trades.csv"
    path = DATA_DIR / pattern
    if not path.exists():
        return []
    
    # Read raw trades and build 1-min bars
    bars_by_min = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = datetime.fromisoformat(row["ts_event"].replace("Z", "+00:00"))
                price = float(row["price"]) / 1e9  # databento stores in nanoseconds fixed point
                size = int(row["size"])
            except Exception:
                continue
            # Round to 1-minute bucket
            bucket = ts.replace(second=0, microsecond=0)
            if bucket not in bars_by_min:
                bars_by_min[bucket] = {"ts": bucket, "high": price, "low": price, "close": price}
            else:
                bars_by_min[bucket]["high"] = max(bars_by_min[bucket]["high"], price)
                bars_by_min[bucket]["low"]  = min(bars_by_min[bucket]["low"],  price)
                bars_by_min[bucket]["close"] = price
    
    return sorted(bars_by_min.values(), key=lambda b: b["ts"])


def widened_stop(entry: float, original_stop: float, direction: str):
    orig_dist = abs(entry - original_stop) / TICK_SIZE
    if orig_dist >= MIN_STOP_TICKS:
        return original_stop, orig_dist
    if direction == "long":
        new_stop = entry - MIN_STOP_TICKS * TICK_SIZE
    else:
        new_stop = entry + MIN_STOP_TICKS * TICK_SIZE
    return new_stop, MIN_STOP_TICKS


def simulate_trade(entry, new_stop, target, direction, entry_time, bars, max_hours=2):
    """
    Walk forward through actual 1-min bars from entry_time.
    Return ('stop', exit_price) or ('target', exit_price) or ('open', last_price).
    """
    window_end = entry_time + timedelta(hours=max_hours)
    relevant = [b for b in bars
                if entry_time <= b["ts"] < window_end]
    
    for b in relevant:
        if direction == "long":
            if b["low"] <= new_stop:
                return "stop", new_stop
            if b["high"] >= target:
                return "target", target
        else:
            if b["high"] >= new_stop:
                return "stop", new_stop
            if b["low"] <= target:
                return "target", target
    return "open", relevant[-1]["close"] if relevant else entry


def analyze():
    trades = [json.loads(l) for l in open(TRADES_FILE) if l.strip()]
    risk_per_trade = 100_000 * 0.005  # $500 per trade

    print("=" * 115)
    print("HONEST PHYSICAL STOP SIMULATION — Using REAL tick data")
    print("=" * 115)
    print(f"{'Date':<12} {'Dir':<5} {'Setup':<22} {'OrigDist':>8} {'NewDist':>8} "
          f"{'OldResult':>12} {'NewResult':>12} {'Delta USD':>11}")
    print("-" * 115)

    total_old_usd = 0.0
    total_new_usd = 0.0
    saved = []
    still_stopped = []

    bars_cache = {}

    for t in trades:
        entry      = t["entry"]
        stop       = t["stop"]
        target     = t["target"]
        direction  = t["direction"]
        reason     = t["exit_reason"]
        old_pnl    = t["pnl_usd"]
        date_str   = t["date"]
        entry_time = datetime.fromisoformat(t["entry_time"])

        orig_dist = abs(entry - stop) / TICK_SIZE
        new_stop, new_dist = widened_stop(entry, stop, direction)
        
        # Calculate new contracts with 40-tick floor sizing
        new_contracts = max(1, math.floor(risk_per_trade / (max(MIN_STOP_TICKS, orig_dist) * TICK_VAL)))

        if reason == "target":
            # Winner — no change to outcome, just sizing diff
            new_pnl = old_pnl * (new_contracts / t["contracts"]) if t["contracts"] > 0 else old_pnl
            old_outcome = f"+{t['pnl_ticks']:.0f}t"
            new_outcome = f"+{t['pnl_ticks']:.0f}t"
        else:
            # Stopped out trade — simulate with real bars
            if date_str not in bars_cache:
                bars_cache[date_str] = load_bars_for_date(date_str)
            bars = bars_cache[date_str]

            if orig_dist >= MIN_STOP_TICKS:
                # Stop already >= 40 ticks — no change
                new_pnl = old_pnl
                old_outcome = f"-{orig_dist:.0f}t"
                new_outcome = f"-{orig_dist:.0f}t"
            elif not bars:
                # No data available — mark as unknown
                new_pnl = old_pnl
                old_outcome = f"-{orig_dist:.0f}t"
                new_outcome = "NO DATA"
            else:
                exit_reason_new, exit_price_new = simulate_trade(
                    entry, new_stop, target, direction, entry_time, bars
                )
                if exit_reason_new == "target":
                    ticks_new = abs(target - entry) / TICK_SIZE
                    new_pnl = ticks_new * new_contracts * TICK_VAL
                    old_outcome = f"-{orig_dist:.0f}t (${old_pnl:.0f})"
                    new_outcome = f"+{ticks_new:.0f}t (${new_pnl:.0f})"
                    saved.append((date_str, t["setup_type"], orig_dist, old_pnl, new_pnl))
                elif exit_reason_new == "stop":
                    ticks_new = new_dist
                    new_pnl = -ticks_new * new_contracts * TICK_VAL
                    old_outcome = f"-{orig_dist:.0f}t (${old_pnl:.0f})"
                    new_outcome = f"-{ticks_new:.0f}t (${new_pnl:.0f})"
                    still_stopped.append(date_str)
                else:
                    new_pnl = old_pnl
                    old_outcome = f"-{orig_dist:.0f}t"
                    new_outcome = "OPEN/UNKNOWN"

        total_old_usd += old_pnl
        total_new_usd += new_pnl
        delta = new_pnl - old_pnl

        print(f"{date_str:<12} {direction:<5} {t['setup_type']:<22} {orig_dist:>8.1f} {new_dist:>8.1f} "
              f"{old_outcome:>12} {new_outcome:>12} {delta:>+11.0f}")

    print("=" * 115)
    print(f"\nSUMMARY (based on REAL price data):")
    print(f"  OLD Total USD PnL : ${total_old_usd:,.2f}")
    print(f"  NEW Total USD PnL : ${total_new_usd:,.2f}")
    print(f"  Net Delta         : ${(total_new_usd - total_old_usd):+,.2f}")
    print()

    wins_old = len([t for t in trades if t["exit_reason"] == "target"])
    wins_new = wins_old + len(saved)
    print(f"  Win Rate OLD : {wins_old}/{len(trades)} = {wins_old/len(trades)*100:.1f}%")
    print(f"  Win Rate NEW : {wins_new}/{len(trades)} = {wins_new/len(trades)*100:.1f}%")
    print()
    if saved:
        print(f"  Trades GENUINELY SAVED by wider stop ({len(saved)}):")
        for date, setup, dist, old_u, new_u in saved:
            print(f"    {date} [{setup}] orig={dist:.0f}t  was ${old_u:.0f} LOSS => ${new_u:.0f} PROFIT  (swing: ${new_u-old_u:+,.0f})")
    if still_stopped:
        print(f"\n  Trades still stopped even with wider stop ({len(still_stopped)}):")
        for d in still_stopped:
            print(f"    {d}")


if __name__ == "__main__":
    analyze()
