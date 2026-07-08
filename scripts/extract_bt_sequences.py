"""
extract_bt_sequences.py  –  Enriched Big Trade Sequence Extractor v2
======================================================================
Changes from v1:
  - Volume Profile (POC/VAL/VAH) computed INCREMENTALLY (only bars before current node)
  - Added SEQUENCE-LEVEL pattern features:
      * node_proximity: "close" (<5 min), "medium" (5-15 min), "far" (>15 min)
      * direction_consistent: price moved in dominant_side direction
      * seq_all_same_side: tutti e 3 i nodi hanno stesso lato
      * seq_pattern: forma della serie ("accumulation", "breakout_up", etc.)
      * time_gap_trend: i gap temporali si allargano o restringono
      * price_gap_trend: i gap di prezzo si allargano o restringono
"""
import argparse
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone
import pytz

sys.path.append(str(Path(__file__).parent.parent))

from src.data_loader import list_data_files, load_day
from src.bar_aggregator import aggregate_to_bars
from src.bt_narrative_engine import extract_big_trade_nodes
from src.volume_profile import compute_volume_profile

ET = pytz.timezone("America/New_York")

# ── Helpers ───────────────────────────────────────────────────────────────────

def to_et(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(ET)

def filter_ny_window(bars):
    return [b for b in bars if 9 <= to_et(b.timestamp).hour < 16
            or (to_et(b.timestamp).hour == 16 and to_et(b.timestamp).minute == 0)]

def session_phase(ts_utc: datetime) -> str:
    et = to_et(ts_utc)
    mins = et.hour * 60 + et.minute
    if mins < 9 * 60 + 30: return "pre_market"
    if mins < 10 * 60:      return "ib_forming"
    if mins < 11 * 60:      return "morning"
    if mins < 14 * 60:      return "midday"
    if mins < 15 * 60:      return "afternoon"
    return "close"

def ticks_from(price: float, level: float) -> float:
    return round((price - level) / 0.25, 1)

def position_label(price: float, level: float, band: float = 2.0) -> str:
    diff = price - level
    if diff > band:  return "above"
    if diff < -band: return "below"
    return "at"

def ib_position(price: float, ib_high: float, ib_low: float) -> str:
    if price > ib_high: return "above_ib"
    if price < ib_low:  return "below_ib"
    mid = (ib_high + ib_low) / 2
    return "ib_upper_half" if price >= mid else "ib_lower_half"

def build_ib(bars_ny) -> tuple:
    ib_bars = [b for b in bars_ny
               if 9*60+30 <= to_et(b.timestamp).hour*60+to_et(b.timestamp).minute < 10*60]
    if not ib_bars: return None, None
    return max(b.high for b in ib_bars), min(b.low for b in ib_bars)

def bars_before(bars_ny, ts_utc: datetime):
    """Return only bars strictly before this timestamp (real-time VP)."""
    return [b for b in bars_ny if b.timestamp < ts_utc]

def node_proximity(elapsed_mins: int) -> str:
    if elapsed_mins <= 5:  return "close"
    if elapsed_mins <= 15: return "medium"
    return "far"

def classify_node_side(trades) -> str:
    buy_vol  = sum(t.size for t in trades if t.side == 'B')
    sell_vol = sum(t.size for t in trades if t.side == 'A')
    return "B" if buy_vol >= sell_vol else "A"

# ── Sequence-level pattern detection ─────────────────────────────────────────

def seq_pattern_label(seq_nodes) -> str:
    """
    Classifica la forma spazio-temporale dei 3 nodi.
    Esempi:
      - "accumulation_breakup"  : 2 Buy vicini + terzo Buy lontano in su
      - "distribution_breakdown": 2 Sell vicini + terzo Sell lontano in giu
      - "reversal_buy"          : 2 Sell vicini + terzo Buy
      - "reversal_sell"         : 2 Buy vicini + terzo Sell
      - "chop"                  : tutto misto
    """
    if len(seq_nodes) < 3:
        return "unknown"

    sides  = [classify_node_side(n.current_trades) for n in seq_nodes]
    deltas = [seq_nodes[i].price_change for i in range(1, len(seq_nodes))]
    gaps   = [seq_nodes[i].elapsed_mins for i in range(1, len(seq_nodes))]

    first_two_same  = sides[0] == sides[1]
    last_side       = sides[-1]
    first_side      = sides[0]

    # Proximity of first pair
    first_gap_close = gaps[0] <= 5 if gaps else False
    second_gap_far  = gaps[1] > 15 if len(gaps) > 1 else False

    all_buy  = all(s == "B" for s in sides)
    all_sell = all(s == "A" for s in sides)

    # Price acceleration: is last delta bigger than first?
    price_accel = abs(deltas[-1]) > abs(deltas[0]) if len(deltas) >= 2 else False

    if all_buy and first_gap_close and second_gap_far and deltas[-1] > 0 and price_accel:
        return "accumulation_breakup"
    if all_sell and first_gap_close and second_gap_far and deltas[-1] < 0 and price_accel:
        return "distribution_breakdown"
    if all_buy and all(d > 0 for d in deltas):
        return "trending_up"
    if all_sell and all(d < 0 for d in deltas):
        return "trending_down"
    if first_two_same and last_side != first_side:
        return "reversal_buy" if last_side == "B" else "reversal_sell"
    if sides[0] != sides[1] and sides[1] == sides[2]:
        return "failed_reversal"
    return "chop"

# ── Node enrichment ───────────────────────────────────────────────────────────

def precompute_running_volume_profiles(bars_ny, node_timestamps):
    from src.volume_profile import TICK_BUCKET_SIZE, VA_PERCENTAGE, VolumeProfile
    import numpy as np
    from collections import defaultdict
    
    profiles = {}
    price_vol = defaultdict(float)
    node_set = set(node_timestamps)
    
    for idx, bar in enumerate(bars_ny):
        if idx >= 5 and price_vol and bar.timestamp in node_set:
            sorted_prices = sorted(price_vol.keys())
            volumes       = [price_vol[p] for p in sorted_prices]
            total_vol     = sum(volumes)
            
            if total_vol > 0:
                poc_idx       = int(np.argmax(volumes))
                poc           = sorted_prices[poc_idx]
                
                # Value Area
                va_vol = volumes[poc_idx]
                lo_idx = hi_idx = poc_idx
                while va_vol / total_vol < VA_PERCENTAGE:
                    add_lo = volumes[lo_idx - 1] if lo_idx > 0 else 0
                    add_hi = volumes[hi_idx + 1] if hi_idx < len(volumes) - 1 else 0
                    if add_hi >= add_lo and hi_idx < len(volumes) - 1:
                        hi_idx += 1; va_vol += add_hi
                    elif lo_idx > 0:
                        lo_idx -= 1; va_vol += add_lo
                    else:
                        break
                
                profiles[bar.timestamp] = VolumeProfile(
                    poc=poc,
                    va_high=sorted_prices[hi_idx],
                    va_low=sorted_prices[lo_idx],
                    hvn_levels=[],
                    lvn_levels=[]
                )
        
        # Accumulate this bar's volume (optimized running sum)
        p_low  = round(bar.low  / TICK_BUCKET_SIZE) * TICK_BUCKET_SIZE
        p_high = round(bar.high / TICK_BUCKET_SIZE) * TICK_BUCKET_SIZE
        ticks  = max(1, round((p_high - p_low) / TICK_BUCKET_SIZE) + 1)
        vol_per_tick = bar.volume / ticks
        
        for p in np.arange(p_low, p_high + 1e-9, TICK_BUCKET_SIZE):
            price_vol[round(p, 2)] += vol_per_tick
            
    return profiles

def enrich_node(node, bars_ny, ib_high, ib_low, prev_vp, all_nodes, node_idx, running_profiles) -> dict:
    ts    = node.current_time
    et    = to_et(ts)
    price = node.current_price

    # ── VWAP real-time: use bar's own vwap field ──────────────────────────────
    bar_at = next((b for b in bars_ny if b.timestamp == ts), None)
    vwap   = getattr(bar_at, 'vwap', None) if bar_at else None
    cvd    = getattr(bar_at, 'cvd', 0)    if bar_at else 0

    # ── VP real-time: lookup precomputed profile ─────────────────────────────
    rt_vp = running_profiles.get(ts, None)

    poc = rt_vp.poc      if rt_vp else None
    val = rt_vp.va_low   if rt_vp else None
    vah = rt_vp.va_high  if rt_vp else None

    # ── Prev day VP ───────────────────────────────────────────────────────────
    prev_close = prev_vp['close'] if prev_vp else None
    prev_poc   = prev_vp['poc']   if prev_vp else None

    # ── Consecutive same-side ─────────────────────────────────────────────────
    side   = classify_node_side(node.current_trades)
    consec = 1
    for j in range(node_idx - 1, -1, -1):
        if classify_node_side(all_nodes[j].current_trades) == side:
            consec += 1
        else:
            break

    # ── Delta divergence ──────────────────────────────────────────────────────
    price_up  = node.price_change > 0 if node.previous_price else None
    delta_pos = node.cumulative_delta > 0
    divergence = False
    if price_up is not None:
        divergence = (price_up and not delta_pos) or (not price_up and delta_pos)

    # ── Direction consistency: did price move in dominant_side direction? ─────
    if node.previous_price is not None:
        direction_consistent = (side == "B" and node.price_change > 0) or \
                               (side == "A" and node.price_change < 0)
    else:
        direction_consistent = None

    # ── Node proximity ────────────────────────────────────────────────────────
    proximity = node_proximity(node.elapsed_mins) if node.previous_price else None

    mins_since_open = int((et - et.replace(hour=9, minute=30, second=0, microsecond=0)).total_seconds() / 60)

    return {
        # Temporal
        "time_et":           et.strftime("%H:%M"),
        "session_phase":     session_phase(ts),
        "mins_since_open":   mins_since_open,
        "node_proximity":    proximity,
        # Price levels (real-time VP)
        "price":             price,
        "price_vs_vwap":     position_label(price, vwap) if vwap else None,
        "vwap_ticks":        ticks_from(price, vwap)     if vwap else None,
        "price_vs_poc":      position_label(price, poc)  if poc  else None,
        "poc_ticks":         ticks_from(price, poc)      if poc  else None,
        "price_vs_val":      position_label(price, val)  if val  else None,
        "val_ticks":         ticks_from(price, val)      if val  else None,
        "price_vs_vah":      position_label(price, vah)  if vah  else None,
        "vah_ticks":         ticks_from(price, vah)      if vah  else None,
        "ib_position":       ib_position(price, ib_high, ib_low) if ib_high else None,
        "ib_ext_side":       ("above" if price > ib_high else "below" if price < ib_low else "inside") if ib_high else None,
        # Prev day
        "price_vs_prev_close": position_label(price, prev_close) if prev_close else None,
        "price_vs_prev_poc":   position_label(price, prev_poc)   if prev_poc  else None,
        # Trade structure
        "dominant_side":          side,
        "volume":                 sum(t.size for t in node.current_trades),
        "consecutive_same_side":  consec,
        "direction_consistent":   direction_consistent,
        # Inter-node metrics
        "elapsed_mins":      node.elapsed_mins,
        "price_change":      node.price_change,
        "cumulative_delta":  node.cumulative_delta,
        "max_excursion":     node.max_excursion,
        "min_excursion":     node.min_excursion,
        # Session state
        "session_cvd":       cvd,
        "delta_divergence":  divergence,
    }

# ── Sequence builder ──────────────────────────────────────────────────────────

def build_sequences(nodes, bars_ny, ib_high, ib_low, prev_vp, seq_len=3) -> list:
    sequences = []
    
    running_profiles = precompute_running_volume_profiles(bars_ny, [n.current_time for n in nodes])

    for i in range(len(nodes) - seq_len):
        seq_nodes = nodes[i:i + seq_len]
        next_node = nodes[i + seq_len]
        last_node = seq_nodes[-1]

        entry_price        = last_node.current_price
        target_price_delta = next_node.current_price - entry_price
        target_time_delta  = (next_node.current_time - last_node.current_time).total_seconds() / 60.0

        steps = [enrich_node(n, bars_ny, ib_high, ib_low, prev_vp, seq_nodes, j, running_profiles)
                 for j, n in enumerate(seq_nodes)]

        # ── MFE / MAE usando max/min excursion del next_node ─────────────────
        # next_node.max_excursion = massimo HIGH dei bar tra last_node e next_node
        # next_node.min_excursion = minimo LOW dei bar tra last_node e next_node
        window_high = getattr(next_node, 'max_excursion', None) or entry_price
        window_low  = getattr(next_node, 'min_excursion', None) or entry_price

        mfe_long_pts  = round(window_high - entry_price, 2)   # quanto sale prima di arrivare al target
        mae_long_pts  = round(entry_price - window_low,  2)   # quanto scende contro di noi (drawdown long)
        mfe_short_pts = round(entry_price - window_low,  2)   # quanto scende (favorevole se short)
        mae_short_pts = round(window_high - entry_price, 2)   # quanto sale contro (drawdown short)

        # R/R reale: quanto guadagni vs quanto rischi nella finestra
        rr_long  = round(mfe_long_pts  / mae_long_pts,  2) if mae_long_pts  > 0 else None
        rr_short = round(mfe_short_pts / mae_short_pts, 2) if mae_short_pts > 0 else None

        # SL naturale = il punto estremo toccato contro di noi (in punti da entry)
        sl_long_pts  = mae_long_pts   # quanto avremmo perso con SL al minimo della finestra
        sl_short_pts = mae_short_pts  # quanto avremmo perso con SL al massimo della finestra

        # Trade quality: "clean" = non ha toccato > 10 punti contro prima di andare
        clean_long  = mae_long_pts  <= 10
        clean_short = mae_short_pts <= 10

        # Categoria R/R
        def rr_category(rr):
            if rr is None:     return "undefined"
            if rr >= 3.0:      return "excellent"
            if rr >= 2.0:      return "good"
            if rr >= 1.0:      return "acceptable"
            return "poor"

        # ── Sequence-level pattern features ──────────────────────────────────
        sides  = [classify_node_side(n.current_trades) for n in seq_nodes]
        gaps   = [seq_nodes[k].elapsed_mins for k in range(1, len(seq_nodes))]
        pchgs  = [seq_nodes[k].price_change  for k in range(1, len(seq_nodes))]
        vols   = [sum(t.size for t in n.current_trades) for n in seq_nodes]

        pattern = seq_pattern_label(seq_nodes)
        all_same_side = len(set(sides)) == 1
        gap_trend = "widening" if (len(gaps) >= 2 and gaps[-1] > gaps[0]) else \
                    "narrowing" if (len(gaps) >= 2 and gaps[-1] < gaps[0]) else "stable"
        price_accel = round(abs(pchgs[-1]) - abs(pchgs[0]), 2) if len(pchgs) >= 2 else 0
        vol_trend = "increasing" if (len(vols) >= 2 and vols[-1] > vols[0]) else \
                    "decreasing" if (len(vols) >= 2 and vols[-1] < vols[0]) else "stable"

        # Determine setup direction to identify contrary big trades
        if pattern in ["trending_up", "accumulation_breakup", "reversal_buy"]:
            direction = "long"
        elif pattern in ["trending_down", "distribution_breakdown", "reversal_sell"]:
            direction = "short"
        else:
            direction = "unknown"

        contrary_trades = []
        if direction != "unknown":
            start_t = seq_nodes[0].current_time
            end_t = last_node.current_time
            contrary_side = 'B' if direction == "long" else 'A'
            for b in bars_ny:
                if start_t <= b.timestamp <= end_t:
                    for t in b.big_trades:
                        if t.side == contrary_side:
                            contrary_trades.append(t)

        contrary_max_size = max([t.size for t in contrary_trades]) if contrary_trades else 0
        contrary_count = len(contrary_trades)

        sequences.append({
            "sequence_id":            f"{to_et(seq_nodes[0].current_time).strftime('%Y%m%d')}_{i}",
            "date":                   to_et(seq_nodes[0].current_time).strftime('%Y%m%d'),
            "start_time":             to_et(seq_nodes[0].current_time).strftime('%H:%M'),
            "end_time":               to_et(last_node.current_time).strftime('%H:%M'),
            "target_node_time":       to_et(next_node.current_time).strftime('%H:%M'),
            # ── Prezzi ──
            "entry_price":            round(entry_price, 2),
            "window_high":            round(window_high, 2),
            "window_low":             round(window_low, 2),
            "target_price":           round(next_node.current_price, 2),
            "target_price_delta":     round(target_price_delta, 2),
            "target_time_delta_mins": round(target_time_delta, 2),
            # ── Outcome base ──
            "is_profitable_long":     target_price_delta > 0,
            "is_profitable_short":    target_price_delta < 0,
            # ── MFE / MAE / SL ──
            "mfe_long_pts":           mfe_long_pts,
            "mae_long_pts":           mae_long_pts,
            "mfe_short_pts":          mfe_short_pts,
            "mae_short_pts":          mae_short_pts,
            "sl_long_pts":            sl_long_pts,
            "sl_short_pts":           sl_short_pts,
            "rr_long":                rr_long,
            "rr_short":               rr_short,
            "rr_long_category":       rr_category(rr_long),
            "rr_short_category":      rr_category(rr_short),
            "clean_long":             clean_long,
            "clean_short":            clean_short,
            # ── Contrary Trades ──
            "contrary_max_size":      contrary_max_size,
            "contrary_count":         contrary_count,
            "has_contrary_100":       contrary_max_size >= 100,
            "has_contrary_150":       contrary_max_size >= 150,
            "has_contrary_250":       contrary_max_size >= 250,
            # ── Pattern ──
            "seq_pattern":            pattern,
            "seq_all_same_side":      all_same_side,
            "seq_gap_trend":          gap_trend,
            "seq_price_accel":        price_accel,
            "seq_vol_trend":          vol_trend,
            "seq_sides":              "->".join(sides),
            "steps":                  steps,
        })

    return sequences

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Extract enriched Big Trade Sequences v2")
    parser.add_argument('--start-date', type=str, required=True)
    parser.add_argument('--end-date',   type=str, required=True)
    parser.add_argument('--data-dir',   type=str, required=True)
    parser.add_argument('--seq-len',    type=int, default=3)
    args = parser.parse_args()

    files = list_data_files(args.data_dir)
    all_files = sorted(
        [(os.path.basename(f).split('-')[2].split('.')[0], f)
         for f in files if len(os.path.basename(f).split('-')) >= 3],
        key=lambda x: x[0]
    )
    dates_to_run = [(d, f) for d, f in all_files if args.start_date <= d <= args.end_date]

    out_dir = Path(__file__).parent.parent / "knowledge" / "trader_lessons_graph" / "graphify-out" / "sequences"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_sequences = []
    prev_vp = None  # carried forward day by day

    for date_str, f in dates_to_run:
        print(f"Processing {date_str}...")
        try:
            df_raw    = load_day(f, as_df=True)
            bars_1min = aggregate_to_bars(df_raw, "1min")
            bars_ny   = filter_ny_window(bars_1min)
            ib_high, ib_low = build_ib(bars_ny)
            nodes = extract_big_trade_nodes(bars_ny)
            print(f"  Found {len(nodes)} Big Trade Nodes (>=80 contracts).")

            if len(nodes) < args.seq_len + 1:
                print("  Not enough nodes for sequences.")
                # Still carry forward prev_vp
                full_vp = compute_volume_profile(bars_ny) if bars_ny else None
                if full_vp:
                    prev_vp = {"poc": full_vp.poc, "val": full_vp.va_low,
                               "vah": full_vp.va_high, "close": bars_ny[-1].close}
                continue

            seqs = build_sequences(nodes, bars_ny, ib_high, ib_low, prev_vp, args.seq_len)
            print(f"  Extracted {len(seqs)} enriched sequences.")
            all_sequences.extend(seqs)

            # Build today's VP for tomorrow's prev_vp (full day = OK here, it's yesterday)
            full_vp = compute_volume_profile(bars_ny)
            prev_vp = {"poc": full_vp.poc, "val": full_vp.va_low,
                       "vah": full_vp.va_high, "close": bars_ny[-1].close}

        except Exception as e:
            import traceback
            print(f"  ERROR on {date_str}: {e}")
            traceback.print_exc()

    out_file = out_dir / "bt_sequences.json"
    with open(out_file, "w", encoding="utf-8") as fp:
        json.dump(all_sequences, fp, indent=4)

    print(f"\nSaved {len(all_sequences)} enriched sequences to {out_file}")

if __name__ == "__main__":
    main()
