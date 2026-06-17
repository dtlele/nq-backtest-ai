import sys, os, json, re
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import load_day
from src.bar_aggregator import aggregate_to_bars
from src.session_context import filter_ny_window, filter_overnight_window, filter_full_ny_session, compute_ib
from src.volume_profile import compute_volume_profile
from src import NQ_BIG_TRADE_THRESHOLD
import pytz

DATA_DIR   = r"C:\Users\Mauro\Documents\databento-data"
OUTPUT_DIR = Path(__file__).parent.parent / "dashboard" / "public" / "data"

# Find all dates that have JSON files in OUTPUT_DIR
dates_to_process = []
for f in sorted(list(OUTPUT_DIR.glob("*.json"))):
    # format "2025-04-30.json" -> "20250430"
    match = re.match(r'(\d{4})-(\d{2})-(\d{2})', f.stem)
    if match:
        dates_to_process.append(f.stem.replace("-", ""))

print(f"Found {len(dates_to_process)} dates to process.")

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

# Import the helper from export_dashboard_data or define it here
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

for date_str in dates_to_process:
    candidates = list(Path(DATA_DIR).glob(f"*{date_str}*.csv"))
    if not candidates:
        print(f"[SKIP] {date_str} — csv not found")
        continue

    csv_path = candidates[0]
    date_label = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    out_file = OUTPUT_DIR / f"{date_label}.json"

    # We overwrite always to ensure prev_day_vp is included
    print(f"[PROCESS] {date_label} — {csv_path.name}")

    try:
        trades_raw = load_day(str(csv_path))
        bars_all   = aggregate_to_bars(trades_raw, freq="1min")
        bars_ny    = filter_ny_window(bars_all)
        bars_full  = filter_full_ny_session(bars_all)
        
        # Keep bars from overnight (Sunday/evening) to end of RTH session (16:15 ET) for visualization
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
            print(f"  [WARN] no bars for {date_label}")
            continue

        vwap_data = []
        cum_pv, cum_vol = 0.0, 0.0
        for bar in bars_full:
            hlc3 = (bar.high + bar.low + bar.close) / 3.0
            cum_pv  += hlc3 * bar.volume
            cum_vol += bar.volume
            vwap_val = cum_pv / cum_vol if cum_vol > 0 else bar.close
            vwap_data.append({"time": ts(bar), "value": round(vwap_val, 2)})

        bars_on    = filter_overnight_window(bars_all)
        vp_overnight = compute_volume_profile(bars_on)

        dev_va = []
        prog_bars = []
        for bar in bars_full:
            prog_bars.append(bar)
            vp_prog = compute_volume_profile(prog_bars)
            dev_va.append({
                "time": ts(bar),
                "vah": vp_prog.va_high if vp_prog else bar.high,
                "val": vp_prog.va_low if vp_prog else bar.low,
                "poc": vp_prog.poc if vp_prog else bar.close
            })

        ib_high, ib_low = compute_ib(bars_full)
        big_trades = extract_big_trades(bars_full)

        # Get yesterday's VP
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

        print(f"  -> saved: {out_file.name} with prev_day_vp={prev_vp is not None}")

    except Exception as e:
        print(f"  [ERROR] {date_label}: {e}")

print("All dates processed successfully!")
