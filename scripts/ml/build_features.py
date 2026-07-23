"""Build features per ML training su 230 giorni di NQ.

Per ogni candela M5 aggrega 15+ features orderflow:
- delta, wick, range, volume
- distance_from_VWAP, distance_from_POC
- is_second_test, is_outside_IB
- time_of_day, regime

Output: data/ml/features_230d.csv con colonne (date, time, features..., label)
"""
import csv
import os
import sys
import datetime as dt
from collections import defaultdict

sys.path.insert(0, '.')
from src.bar_aggregator import aggregate_to_bars
from src.volume_profile import compute_volume_profile
from src.session_context import build_session_context, compute_ib

DATA_DIR = r'C:\Users\Mauro\Documents\databento-data'
OUT_DIR = r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml'
os.makedirs(OUT_DIR, exist_ok=True)


def load_trades(csv_path):
    """Carica tick trades da CSV Databento come oggetti Trade."""
    from src import Trade
    trades = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts_str = row['ts_event'].replace('Z', '+00:00')
            ts = dt.datetime.fromisoformat(ts_str)
            price = float(row['price'])
            if 20000 < price < 25000:  # filtra outlier
                trades.append(Trade(
                    ts_event=ts,
                    price=price,
                    size=int(row['size']),
                    side=row.get('side', 'A'),
                ))
    return trades


def build_features_for_day(date_str, trades):
    """Costruisce features per tutte le candele M5 di un giorno."""
    if not trades:
        return []

    # Aggrega a M1, poi M5
    bars_m1 = aggregate_to_bars(trades, freq='1min')
    bars_m5 = aggregate_to_bars(trades, freq='5min')

    # Filtra solo RTH (9:30-16:00 ET)
    import pytz
    ET = pytz.timezone('America/New_York')
    rth_bars = []
    for b in bars_m5:
        et = b.timestamp.astimezone(ET)
        if 9 <= et.hour < 16:
            rth_bars.append(b)
    if not rth_bars:
        return []

    # Calcola VWAP cumulativo
    cum_vol = 0
    cum_pv = 0
    vwap_data = []
    for b in bars_m1:
        # typical price
        tp = (b.high + b.low + b.close) / 3
        cum_pv += tp * b.volume
        cum_vol += b.volume
        vwap_data.append((b.timestamp, cum_pv / cum_vol if cum_vol > 0 else tp))

    # Calcola Volume Profile (semplificato) per POC
    try:
        vp = compute_volume_profile(bars_m1)
        poc = vp.poc if vp else None
        vah = vp.va_high if vp else None
        val = vp.va_low if vp else None
    except Exception:
        poc = vah = val = None

    # Features per ogni candela M5 RTH
    features = []
    for i, b in enumerate(rth_bars):
        if b.volume < 100:  # skip candele vuote
            continue
        # VWAP al timestamp della candela
        vwap = None
        for ts, v in vwap_data:
            if ts <= b.timestamp:
                vwap = v
            else:
                break
        if vwap is None:
            vwap = b.close

        # Features
        body = abs(b.close - b.open)
        full_range = b.high - b.low
        upper_wick = b.high - max(b.open, b.close)
        lower_wick = min(b.open, b.close) - b.low
        net = b.close - b.open
        wick_ratio = (upper_wick + lower_wick) / full_range if full_range > 0 else 0

        # Delta cumulato ultime 6 candele M5 (30 min di contesto)
        cv_delta = 0
        cv_vol = 0
        for j in range(max(0, i - 6), i + 1):
            cv_delta += rth_bars[j].delta if hasattr(rth_bars[j], 'delta') else 0
            cv_vol += rth_bars[j].volume
        cv_delta_avg = cv_delta / max(1, i - max(0, i - 6) + 1)

        # Time of day
        et = b.timestamp.astimezone(ET)
        tod = et.hour + et.minute / 60.0

        # Volume relative (vs media ultime 12 candele = 1h)
        recent_vols = [rth_bars[max(0, i - j)].volume for j in range(12)]
        avg_vol = sum(recent_vols) / len(recent_vols) if recent_vols else 1
        vol_ratio = b.volume / avg_vol if avg_vol > 0 else 1

        # IB (prima ora 9:30-10:30)
        ib_bars = [rth_bars[j] for j in range(min(12, len(rth_bars))) if rth_bars[j].timestamp.astimezone(ET).hour < 11]
        if ib_bars:
            ib_high = max(bb.high for bb in ib_bars)
            ib_low = min(bb.low for bb in ib_bars)
            ib_range = ib_high - ib_low
            is_outside_ib = 1 if b.close > ib_high or b.close < ib_low else 0
            is_above_ib = 1 if b.close > ib_high else 0
            is_below_ib = 1 if b.close < ib_low else 0
        else:
            ib_high = ib_low = ib_range = 0
            is_outside_ib = is_above_ib = is_below_ib = 0

        # Distance da livelli strutturali
        dist_vwap = (b.close - vwap) / vwap * 100 if vwap > 0 else 0
        dist_poc = (b.close - poc) / poc * 100 if poc else 0
        dist_ib_high = (b.close - ib_high) if ib_high > 0 else 0
        dist_ib_low = (b.close - ib_low) if ib_low > 0 else 0

        # Big trades count
        big_trades_count = len(b.big_trades) if hasattr(b, 'big_trades') else 0
        big_trades_total = sum(t.size for t in b.big_trades) if hasattr(b, 'big_trades') else 0

        # Second test (precedente candela ha toccato livello simile)
        is_second_test = 0
        if i > 0 and ib_high > 0:
            if (abs(b.high - ib_high) < 5 or abs(b.low - ib_low) < 5):
                is_second_test = 1

        # LABEL: forward-looking 6 candele (30 min) — WIN solo se
        # movimento netto > 20pt in UNA direzione (NON semplicemente
        # movimento > soglia, che include oscillazioni casuali).
        # NET = somma(net[i+1..i+6]) — misura se il mercato si muove in modo
        # direzionale (win) o choppy (loss).
        forward_window = rth_bars[i + 1:i + 7] if i + 7 <= len(rth_bars) else []
        net_forward = 0
        max_up = 0
        max_down = 0
        for fb in forward_window:
            net_forward += (fb.close - fb.open)
            max_up = max(max_up, fb.high - b.close)
            max_down = max(max_down, b.close - fb.low)
        # WIN: net directionale > +15pt E max move > 20pt in stessa direzione
        if net_forward > 15 and max_up > 20:
            label = 1   # LONG win
        elif net_forward < -15 and max_down > 20:
            label = 1   # SHORT win
        else:
            label = 0   # LOSS / choppy

        row = {
            'date': date_str,
            'time_et': et.strftime('%H:%M'),
            'tod': tod,
            'open': b.open,
            'high': b.high,
            'low': b.low,
            'close': b.close,
            'volume': b.volume,
            'vol_ratio': vol_ratio,
            'delta': getattr(b, 'delta', 0),
            'body': body,
            'full_range': full_range,
            'wick_ratio': wick_ratio,
            'upper_wick': upper_wick,
            'lower_wick': lower_wick,
            'net': net,
            'cv_delta_30m': cv_delta,
            'cv_vol_30m': cv_vol,
            'dist_vwap_pct': dist_vwap,
            'dist_poc_pct': dist_poc,
            'dist_ib_high': dist_ib_high,
            'dist_ib_low': dist_ib_low,
            'is_outside_ib': is_outside_ib,
            'is_above_ib': is_above_ib,
            'is_below_ib': is_below_ib,
            'is_second_test': is_second_test,
            'big_trades_count': big_trades_count,
            'big_trades_total': big_trades_total,
            'label': label,
        }
        features.append(row)

    return features


def main():
    files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith('glbx-mdp3-2025') and f.endswith('.trades.csv')])
    print(f'Trovati {len(files)} file CSV Databento 2025')

    all_features = []
    for i, fname in enumerate(files):
        date_str = fname.replace('glbx-mdp3-', '').replace('.trades.csv', '')
        csv_path = os.path.join(DATA_DIR, fname)
        try:
            trades = load_trades(csv_path)
            if len(trades) < 1000:
                continue
            feats = build_features_for_day(date_str, trades)
            all_features.extend(feats)
            if (i + 1) % 20 == 0:
                print(f'Processed {i + 1}/{len(files)} days, {len(all_features)} rows total')
        except Exception as e:
            print(f'  Skip {date_str}: {e}')

    # Salva CSV
    if all_features:
        out_path = os.path.join(OUT_DIR, 'features_230d.csv')
        keys = list(all_features[0].keys())
        with open(out_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_features)
        print(f'\nScritto {len(all_features)} righe in {out_path}')

        # Distribuzione label
        labels = [r['label'] for r in all_features]
        n_win = sum(labels)
        n_loss = len(labels) - n_win
        print(f'Label distribution: WIN={n_win} ({100 * n_win / len(labels):.1f}%), LOSS={n_loss} ({100 * n_loss / len(labels):.1f}%)')


if __name__ == '__main__':
    main()
