"""
Export dati reali per la dashboard React.
Legge i CSV Databento, aggrega M1/M5, calcola VWAP, estrae Big Trades.
Output: dashboard/public/data/<date>.json
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import load_day, list_data_files
from src.bar_aggregator import aggregate_to_bars
from src.session_context import filter_ny_window, filter_overnight_window, filter_full_ny_session, compute_ib
from src.volume_profile import compute_vwap, compute_volume_profile
from src import NQ_BIG_TRADE_THRESHOLD
from pathlib import Path
import pytz

DATA_DIR   = r"C:\Users\Mauro\Documents\databento-data"
OUTPUT_DIR = Path(__file__).parent.parent / "dashboard" / "public" / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ET = pytz.timezone("America/New_York")

# Load unique dates from trades_log.jsonl
MEMORY_FILE = Path(__file__).parent.parent / "agent_memory" / "trades_log.jsonl"
unique_dates = set()
if MEMORY_FILE.exists():
    with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    trade = json.loads(line)
                    if "date" in trade:
                        # format "2025-04-01" -> "20250401"
                        date_str = trade["date"].replace("-", "")
                        unique_dates.add(date_str)
                except:
                    pass

active_date_str = None
SESSION_FILE = Path(__file__).parent.parent / "agent_memory" / "session_state.json"
if SESSION_FILE.exists():
    try:
        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            session_state = json.load(f)
            if "date" in session_state:
                date_str = session_state["date"].replace("-", "")
                unique_dates.add(date_str)
                active_date_str = date_str
    except:
        pass

DATES = sorted(list(unique_dates))

def ts(bar):
    """Timestamp UTC epoch per lightweight-charts."""
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
    """Estrai tutti i big trades dai bar M1."""
    events = []
    for bar in bars:
        for t in getattr(bar, "big_trades", []):
            if t.size >= NQ_BIG_TRADE_THRESHOLD:
                events.append({
                    "time":  int(t.ts_event.timestamp()),
                    "price": t.price,
                    "size":  t.size,
                    "side":  t.side,  # 'A'=buyer, 'B'=seller
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

for date_str in DATES:
    # trova file CSV
    candidates = list(Path(DATA_DIR).glob(f"*{date_str}*.csv"))
    if not candidates:
        print(f"[SKIP] {date_str} — nessun file trovato")
        continue

    csv_path = candidates[0]
    date_label = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
    out_file = OUTPUT_DIR / f"{date_label}.json"
    
    print(f"[PROCESS] {date_label} — {csv_path.name}")

    try:
        trades_raw = load_day(str(csv_path))
        bars_all   = aggregate_to_bars(trades_raw, freq="1min")
        bars_ny    = filter_ny_window(bars_all)
        bars_full  = filter_full_ny_session(bars_all)
        bars_on    = filter_overnight_window(bars_all)
        
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
            print(f"  [WARN] nessuna barra per {date_label}")
            continue

        # VWAP cumulativo (espansivo) su barre M1 RTH
        vwap_data = []
        cum_pv, cum_vol = 0.0, 0.0
        for bar in bars_full:
            hlc3 = (bar.high + bar.low + bar.close) / 3.0
            cum_pv  += hlc3 * bar.volume
            cum_vol += bar.volume
            vwap_val = cum_pv / cum_vol if cum_vol > 0 else bar.close
            vwap_data.append({"time": ts(bar), "value": round(vwap_val, 2)})

        # Volume Profile RTH progressivo (snapshot finale)
        vp_final = compute_volume_profile(bars_full)

        # Volume Profile Overnight (true overnight levels)
        vp_overnight = compute_volume_profile(bars_on)

        # Volume Profile Developing (Candela per Candela)
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

        # Initial Balance
        ib_high, ib_low = compute_ib(bars_full)

        # Big trades
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

        out_file = OUTPUT_DIR / f"{date_label}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)

        print(f"  -> {len(bars_ny)} barre M1 | {len(big_trades)} big trades | VWAP ok | saved: {out_file.name}")

    except Exception as e:
        print(f"  [ERROR] {date_label}: {e}")
        import traceback; traceback.print_exc()

print("\nDone! Dati esportati in dashboard/public/data/")
