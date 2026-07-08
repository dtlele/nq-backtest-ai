import sys, os, json
from pathlib import Path
import pytz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import load_day
from src.bar_aggregator import aggregate_to_bars
from src.session_context import filter_ny_window, filter_overnight_window, filter_full_ny_session, compute_ib
from src.volume_profile import compute_volume_profile
from src import NQ_BIG_TRADE_THRESHOLD

DATA_DIR   = r"C:\Users\Mauro\Documents\databento-data"
OUTPUT_DIR = Path(__file__).parent.parent / "dashboard" / "public" / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ET = pytz.timezone("America/New_York")

def ts(bar):
    return int(bar.timestamp.timestamp())

def bar_to_ohlcv(bar):
    return {
        "time":   ts(bar),
        "open":   bar.open,
        "high":   bar.high,
        "low":    bar.low,
        "close":  bar.close,
        "volume": bar.volume,
        "delta":  bar.delta,
        "buy_vol": bar.buy_volume,
        "sell_vol": bar.sell_volume,
        "footprint": getattr(bar, "footprint", {}),
    }

def extract_big_trades(bars):
    events = []
    for bar in bars:
        for t in getattr(bar, "big_trades", []):
            if t.size >= NQ_BIG_TRADE_THRESHOLD:
                events.append({
                    "time":  int(t.ts_event.timestamp()),
                    "price": t.price,
                    "size":  t.size,
                    "side":  t.side,
                })
    return events

def get_prev_day_vp(current_date_label, output_dir):
    json_files = sorted(list(output_dir.glob("*.json")))
    prev_file = None
    for f in json_files:
        if f.stem < current_date_label:
            prev_file = f
        else:
            break
    if prev_file:
        try:
            with open(prev_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("vp")
        except:
            return None
    return None

def main():
    unique_dates = []
    trades_path = Path("agent_memory/optimal_backtest_trades.json")
    if trades_path.exists():
        try:
            with open(trades_path, encoding='utf-8') as f:
                trades = json.load(f)
            unique_dates = sorted(list(set(t["date"] for t in trades)))
        except Exception as e:
            print(f"Warning reading trades file: {e}")

    # Scansiona anche i file CSV raw per trovare date non presenti in optimal_backtest_trades.json
    for f in Path(DATA_DIR).glob("glbx-mdp3-*.trades.csv"):
        parts = f.name.split("-")
        if len(parts) >= 3:
            d_str = parts[2].split(".")[0]
            if d_str not in unique_dates:
                unique_dates.append(d_str)

    unique_dates = sorted(list(set(unique_dates)))
    print(f"Regenerating dashboard JSON files for {len(unique_dates)} dates...")

    # Pre-scan DATA_DIR to build lookup dictionary
    csv_lookup = {}
    for f in Path(DATA_DIR).glob("*.csv"):
        parts = f.name.split("-")
        if len(parts) >= 3:
            d_str = parts[2].split(".")[0]
            csv_lookup[d_str] = f

    for date_str in unique_dates:
        csv_path = csv_lookup.get(date_str)
        if not csv_path:
            print(f"[SKIP] {date_str} — no CSV file found")
            continue
        date_label = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        out_file = OUTPUT_DIR / f"{date_label}.json"
        
        if out_file.exists():
            print(f"[SKIP] {date_label} — already exists")
            continue
            
        print(f"[PROCESS] {date_label} — {csv_path.name}")

        try:
            trades_raw = load_day(str(csv_path))
            bars_all   = aggregate_to_bars(trades_raw, freq="1min")
            bars_ny    = filter_ny_window(bars_all)
            bars_full  = filter_full_ny_session(bars_all)
            bars_on    = filter_overnight_window(bars_all)
            
            bars_visual = []
            for b in bars_all:
                t = b.timestamp.astimezone(ET)
                if t.hour < 16 or (t.hour == 16 and t.minute < 15):
                    bars_visual.append(b)
                    
            bars_m5_all = aggregate_to_bars(trades_raw, freq="5min")
            bars_m5_visual = []
            for b in bars_m5_all:
                t = b.timestamp.astimezone(ET)
                if t.hour < 16 or (t.hour == 16 and t.minute < 15):
                    bars_m5_visual.append(b)

            if not bars_full:
                print(f"  [WARN] no RTH bars for {date_label}")
                continue

            # VWAP
            vwap_data = []
            cum_pv, cum_vol = 0.0, 0.0
            for bar in bars_full:
                hlc3 = (bar.high + bar.low + bar.close) / 3.0
                cum_pv  += hlc3 * bar.volume
                cum_vol += bar.volume
                vwap_val = cum_pv / cum_vol if cum_vol > 0 else bar.close
                vwap_data.append({"time": ts(bar), "value": round(vwap_val, 2)})

            vp_final = compute_volume_profile(bars_full)
            vp_overnight = compute_volume_profile(bars_on)

            dev_va = []
            price_vol = {}
            from src import TICK_BUCKET_SIZE, VA_PERCENTAGE
            import numpy as np

            for bar in bars_full:
                # Add current bar to price_vol incrementally
                p_low  = round(bar.low  / TICK_BUCKET_SIZE) * TICK_BUCKET_SIZE
                p_high = round(bar.high / TICK_BUCKET_SIZE) * TICK_BUCKET_SIZE
                ticks  = max(1, round((p_high - p_low) / TICK_BUCKET_SIZE) + 1)
                vol_per_tick = bar.volume / ticks
                price = p_low
                while price <= p_high + 1e-9:
                    key = round(price / TICK_BUCKET_SIZE) * TICK_BUCKET_SIZE
                    price_vol[key] = price_vol.get(key, 0) + vol_per_tick
                    price += TICK_BUCKET_SIZE

                # Extract POC and Value Area
                sorted_prices = sorted(price_vol.keys())
                volumes       = [price_vol[p] for p in sorted_prices]
                total_vol     = sum(volumes)
                poc_idx       = int(np.argmax(volumes))
                poc           = sorted_prices[poc_idx]

                va_vol = volumes[poc_idx]
                lo_idx = hi_idx = poc_idx
                while va_vol / total_vol < VA_PERCENTAGE:
                    add_lo = volumes[lo_idx - 1] if lo_idx > 0 else 0
                    add_hi = volumes[hi_idx + 1] if hi_idx < len(volumes) - 1 else 0
                    if add_hi >= add_lo and hi_idx < len(volumes) - 1:
                        hi_idx += 1
                        va_vol += add_hi
                    elif lo_idx > 0:
                        lo_idx -= 1
                        va_vol += add_lo
                    else:
                        break

                dev_va.append({
                    "time": ts(bar),
                    "vah": sorted_prices[hi_idx],
                    "val": sorted_prices[lo_idx],
                    "poc": poc
                })

            ib_high, ib_low = compute_ib(bars_full)
            big_trades = extract_big_trades(bars_full)
            prev_vp = get_prev_day_vp(date_label, OUTPUT_DIR)
            
            payload = {
                "date":       date_label,
                "m1_ny":      [bar_to_ohlcv(b) for b in bars_visual],
                "m5_ny":      [bar_to_ohlcv(b) for b in bars_m5_visual],
                "vwap":       vwap_data,
                "big_trades": big_trades,
                "vp": {
                    "poc": vp_overnight.poc if vp_overnight else 0,
                    "va_high": vp_overnight.va_high if vp_overnight else 0,
                    "va_low": vp_overnight.va_low if vp_overnight else 0
                },
                "prev_day_vp": prev_vp,
                "dev_va": dev_va,
                "ib": {
                    "high": ib_high,
                    "low": ib_low
                }
            }

            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(payload, f)

            print(f"  -> {len(bars_ny)} RTH bars | saved: {out_file.name}")

        except Exception as e:
            print(f"  [ERROR] {date_label}: {e}")

if __name__ == "__main__":
    main()
