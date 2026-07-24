"""Pre-filtro A+ basato su Random Forest addestrato su 230 giorni.

Carica il modello RF e fornisce score() per candele M5 nuove.
Score > threshold = candela ha edge statistico.
"""
import os
import joblib
import numpy as np
import pandas as pd

MODEL_PATH = r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml\rf_v1.pkl'

_cached_model = None
_cached_features = None


def load_model():
    """Lazy-load del modello RF."""
    global _cached_model, _cached_features
    if _cached_model is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f'Modello non trovato: {MODEL_PATH}. Esegui train_rf.py prima.')
        bundle = joblib.load(MODEL_PATH)
        _cached_model = bundle['model']
        _cached_features = bundle['feature_cols']
    return _cached_model, _cached_features


def extract_features_for_bar(bar, ctx, vol_avg_12=None):
    """Estrai le stesse features del training per una candela M5 nuova.

    Args:
        bar: oggetto Bar (M5) con timestamp, open/high/low/close, volume, delta, big_trades
        ctx: SessionContext con ib_high, ib_low, vp (poc, va_high, va_low), prev_day_vp
        vol_avg_12: media volume ultime 12 candele (opzionale, calcolato se None)

    Returns:
        dict con tutte le features
    """
    import pytz
    ET = pytz.timezone('America/New_York')

    # Time of day
    et = bar.timestamp.astimezone(ET)
    tod = et.hour + et.minute / 60.0

    # Volume ratio
    if vol_avg_12 is None or vol_avg_12 == 0:
        vol_ratio = 1.0
    else:
        vol_ratio = bar.volume / vol_avg_12

    # Body / range / wick
    body = abs(bar.close - bar.open)
    full_range = bar.high - bar.low
    upper_wick = bar.high - max(bar.open, bar.close)
    lower_wick = min(bar.open, bar.close) - bar.low
    net = bar.close - bar.open
    wick_ratio = (upper_wick + lower_wick) / full_range if full_range > 0 else 0

    # IB
    ib_high = getattr(ctx, 'ib_high', 0) or 0
    ib_low = getattr(ctx, 'ib_low', 0) or 0
    is_outside_ib = 1 if (ib_high > 0 and (bar.close > ib_high or bar.close < ib_low)) else 0
    is_above_ib = 1 if (ib_high > 0 and bar.close > ib_high) else 0
    is_below_ib = 1 if (ib_low > 0 and bar.close < ib_low) else 0
    dist_ib_high = bar.close - ib_high if ib_high > 0 else 0
    dist_ib_low = bar.close - ib_low if ib_low > 0 else 0

    # VWAP
    vwap = getattr(bar, 'vwap', 0) or 0
    if vwap > 0:
        dist_vwap_pct = (bar.close - vwap) / vwap * 100
    else:
        dist_vwap_pct = 0

    # POC
    poc = 0
    vp = getattr(ctx, 'vp', None)
    if vp:
        poc = getattr(vp, 'poc', 0) or 0
    if poc > 0:
        dist_poc_pct = (bar.close - poc) / poc * 100
    else:
        dist_poc_pct = 0

    # Big trades
    big_trades = getattr(bar, 'big_trades', []) or []
    big_trades_count = len(big_trades)
    big_trades_total = sum(t.size for t in big_trades)

    # Cumulativi (placeholder se non disponibili)
    cv_delta_30m = getattr(bar, 'cv_delta_30m', 0) or 0
    cv_vol_30m = getattr(bar, 'cv_vol_30m', bar.volume)

    # Second test (semplificato)
    is_second_test = 0  # da migliorare con history

    return {
        'tod': tod,
        'open': bar.open,
        'high': bar.high,
        'low': bar.low,
        'close': bar.close,
        'volume': bar.volume,
        'vol_ratio': vol_ratio,
        'delta': getattr(bar, 'delta', 0) or 0,
        'body': body,
        'full_range': full_range,
        'wick_ratio': wick_ratio,
        'upper_wick': upper_wick,
        'lower_wick': lower_wick,
        'net': net,
        'cv_delta_30m': cv_delta_30m,
        'cv_vol_30m': cv_vol_30m,
        'dist_vwap_pct': dist_vwap_pct,
        'dist_poc_pct': dist_poc_pct,
        'dist_ib_high': dist_ib_high,
        'dist_ib_low': dist_ib_low,
        'is_outside_ib': is_outside_ib,
        'is_above_ib': is_above_ib,
        'is_below_ib': is_below_ib,
        'is_second_test': is_second_test,
        'big_trades_count': big_trades_count,
        'big_trades_total': big_trades_total,
    }


def score_bar(bar, ctx, vol_avg_12=None):
    """Calcola score RF per una candela M5.

    Returns:
        float in [0, 1] = probabilita' WIN
    """
    model, feature_cols = load_model()
    feats = extract_features_for_bar(bar, ctx, vol_avg_12)
    # Crea DataFrame con ordine corretto
    x = pd.DataFrame([[feats.get(c, 0) for c in feature_cols]], columns=feature_cols).fillna(0).values
    return float(model.predict_proba(x)[0, 1])


if __name__ == '__main__':
    # Test
    model, features = load_model()
    print(f'Modello caricato: {len(features)} features')
    print(f'Feature ordine: {features[:10]}...')
