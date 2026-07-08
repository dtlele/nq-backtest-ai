"""
Backtest A — Zone Catalog Full Year 2025
Scans all of 2025 and logs every triggered FST setup zone.
Same parameters as run_fst_scalp_backtest.py. No trade management.
"""
import glob
import json
import os
import sys
import time
from datetime import timedelta
from pathlib import Path

import pandas as pd
import pytz

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.data_loader import load_day
from src.range_builder import build_range_bars
from src.volume_profile import build_profile_from_bars
from src.pattern_detector import detect_bullish_setup, detect_bearish_setup

NY_TZ = pytz.timezone("America/New_York")
DATA_DIR = r"C:\Users\Mauro\Documents\databento-data"

# WIDENED FOR OPTIMIZATION (Rete a strascico)
RANGE_POINTS       = 10.0
BIG_TRADE_THRESHOLD = 10
ABSORPTION_DELTA_LIMIT = 15
PROXIMITY_PTS      = 8.0
COMPOSITE_LOOKBACK_MIN = 120
MIN_SL_POINTS      = 16.0
STOP_BUFFER        = 3.5


def scan_day_for_zones(filepath: str) -> list:
    day_name = os.path.basename(filepath)
    parts = day_name.split("-")
    raw_date = parts[2].split(".")[0] if len(parts) >= 3 else "20250101"

    zones = []
    trades_raw = load_day(filepath)
    if not trades_raw:
        return zones

    bars = build_range_bars(trades_raw, range_points=RANGE_POINTS, big_trade_threshold=BIG_TRADE_THRESHOLD)
    if not bars or len(bars) < 2:
        return zones

    closed_bars = []
    for i, bar in enumerate(bars):
        bar_ts_ny = bar.timestamp.astimezone(NY_TZ)
        # RTH Window limitata alla PRIMA ORA E MEZZA (09:30 - 11:00) per massimizzare l'efficienza e prendere la direzionalità netta
        is_rth = (bar_ts_ny.hour == 9 and bar_ts_ny.minute >= 30) or (bar_ts_ny.hour == 10)
        
        # Optimization: if we are past 11:00, we can stop processing this day completely
        if bar_ts_ny.hour >= 11:
            break
            
        closed_bars.append(bar)
        if not is_rth or i < 1:
            continue

        # Composite LVN from last 60 min
        start_comp_ts = bar.timestamp - timedelta(minutes=COMPOSITE_LOOKBACK_MIN)
        comp_bars = [b for b in closed_bars if b.timestamp >= start_comp_ts]
        lvn_zones = []
        if comp_bars:
            vp = build_profile_from_bars(comp_bars)
            if vp:
                lvn_zones = vp.lvn_levels

        # Session Value Area from RTH open
        rth_start_dt = bar.timestamp.replace(hour=14, minute=30, second=0, microsecond=0)
        rth_bars = [b for b in closed_bars if b.timestamp >= rth_start_dt]
        session_val = session_vah = None
        if rth_bars:
            vp = build_profile_from_bars(rth_bars)
            if vp:
                session_val = vp.va_low
                session_vah = vp.va_high

        c1 = closed_bars[-2]
        c2 = closed_bars[-1]
        bar_time = bar_ts_ny.strftime("%H:%M")

        # Check Bullish
        is_bullish, reason_bull = detect_bullish_setup(
            c1, c2, lvn_zones=lvn_zones, session_val=session_val,
            delta_threshold=-ABSORPTION_DELTA_LIMIT,
            range_points=RANGE_POINTS, proximity_pts=PROXIMITY_PTS
        )
        if is_bullish:
            entry_p = c1.close
            local_low = min(b.low for b in closed_bars[-3:]) if len(closed_bars) >= 3 else c1.low
            sl_p = local_low - 1.0
            risk = entry_p - sl_p
            if risk < MIN_SL_POINTS:
                sl_p = entry_p - MIN_SL_POINTS
                risk = MIN_SL_POINTS
            zones.append({
                "date": raw_date,
                "time": bar_time,
                "direction": "LONG",
                "entry": round(entry_p, 2),
                "stop": round(sl_p, 2),
                "risk_pts": round(risk, 2),
                "c1_delta": c1.delta,
                "c2_delta": c2.delta,
                "c1_close": c1.close,
                "c2_close": c2.close,
                "reason": reason_bull
            })

        # Check Bearish
        is_bearish, reason_bear = detect_bearish_setup(
            c1, c2, hvn_zones=lvn_zones, session_vah=session_vah,
            delta_threshold=ABSORPTION_DELTA_LIMIT,
            range_points=RANGE_POINTS, proximity_pts=PROXIMITY_PTS
        )
        if is_bearish:
            entry_p = c1.close
            local_high = max(b.high for b in closed_bars[-3:]) if len(closed_bars) >= 3 else c1.high
            sl_p = local_high + 1.0
            risk = sl_p - entry_p
            if risk < MIN_SL_POINTS:
                sl_p = entry_p + MIN_SL_POINTS
                risk = MIN_SL_POINTS
            zones.append({
                "date": raw_date,
                "time": bar_time,
                "direction": "SHORT",
                "entry": round(entry_p, 2),
                "stop": round(sl_p, 2),
                "risk_pts": round(risk, 2),
                "c1_delta": c1.delta,
                "c2_delta": c2.delta,
                "c1_close": c1.close,
                "c2_close": c2.close,
                "reason": reason_bear
            })

    return zones


def main():
    print("=" * 60)
    print("BACKTEST A — Zone Catalog Full Year 2025")
    print("=" * 60)

    all_files = sorted(glob.glob(os.path.join(DATA_DIR, "*2025*.trades.csv")))
    files = [
        f for f in all_files
        if "20250101" <= os.path.basename(f).split("-")[2].split(".")[0] <= "20251231"
    ]
    print(f"Found {len(files)} trading days in 2025.\n")

    all_zones = []
    start_time = time.time()

    for f in files:
        date_str = os.path.basename(f).split("-")[2].split(".")[0]
        day_zones = scan_day_for_zones(f)
        if day_zones:
            for z in day_zones:
                print(f"  {z['date']} {z['time']} | {z['direction']:<5} | Entry:{z['entry']:>9.2f} | Risk:{z['risk_pts']:>5.1f}pts")
            all_zones.extend(day_zones)

    print(f"\n{'=' * 60}")
    print(f"ZONE CATALOG SUMMARY — 2025")
    print(f"{'=' * 60}")

    if not all_zones:
        print("  Nessuna zona trovata. Verificare i parametri di rilevamento.")
        return

    df = pd.DataFrame(all_zones)
    n_long  = (df['direction'] == 'LONG').sum()
    n_short = (df['direction'] == 'SHORT').sum()

    print(f"  Giorni analizzati:   {len(files)}")
    print(f"  Zone totali:         {len(all_zones)}")
    print(f"  Long setup:          {n_long}  ({n_long/len(all_zones)*100:.1f}%)")
    print(f"  Short setup:         {n_short}  ({n_short/len(all_zones)*100:.1f}%)")
    print(f"  Risk medio (pts):    {df['risk_pts'].mean():.1f}")
    print(f"  Risk mediano (pts):  {df['risk_pts'].median():.1f}")
    print(f"  Zone / giorno:       {len(all_zones)/len(files):.2f} in media")

    # Monthly breakdown
    df['month'] = df['date'].str[:6]
    print(f"\n  Distribuzione Mensile:")
    for m, grp in df.groupby('month'):
        print(f"    {m}: {len(grp):>3} zone  ({(grp['direction']=='LONG').sum()} L / {(grp['direction']=='SHORT').sum()} S)")

    # Save JSON
    out_path = Path("C:/Users/Mauro/Documents/nq-backtest/output/zone_catalog_2025.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_zones, f, indent=2)
    print(f"\n  Salvato JSON: {out_path}")

    # Save CSV
    csv_path = out_path.with_suffix(".csv")
    df.to_csv(csv_path, index=False)
    print(f"  Salvato CSV:  {csv_path}")

    elapsed = time.time() - start_time
    print(f"\nCompletato in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
