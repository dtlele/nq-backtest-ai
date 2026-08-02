import json
import os
from pathlib import Path
from typing import Tuple, Dict, Any

# Try real QQQ GEX first, fall back to SPX proxy
GEX_DATA_FILE_QQQ = Path(__file__).parent.parent / 'data' / 'qqq_gex_daily.json'
GEX_DATA_FILE = Path(__file__).parent.parent / 'data' / 'gex_data.json'

# Cache JSON load (evita di rileggere il file a ogni barra M5)
_gex_json_cache = None
_gex_spx_json_cache = None

def _load_qqq_json():
    global _gex_json_cache
    if _gex_json_cache is None and GEX_DATA_FILE_QQQ.exists():
        try:
            with open(GEX_DATA_FILE_QQQ, 'r', encoding='utf-8') as f:
                _gex_json_cache = json.load(f)
        except Exception:
            _gex_json_cache = {}
    return _gex_json_cache or {}

def _load_spx_json():
    global _gex_spx_json_cache
    if _gex_spx_json_cache is None and GEX_DATA_FILE.exists():
        try:
            with open(GEX_DATA_FILE, 'r', encoding='utf-8') as f:
                _gex_spx_json_cache = json.load(f)
        except Exception:
            _gex_spx_json_cache = {}
    return _gex_spx_json_cache or {}

def load_gex_for_date(date_str: str, overnight_vp=None, opening_price: float = None) -> Dict[str, Any]:
    """
    Load GEX metrics for a given date (format: YYYY-MM-DD or YYYYMMDD).
    If no GEX data is available, computes robust fallback values based on the
    overnight Volume Profile and opening price.
    """
    # Normalize date_str to YYYY-MM-DD
    norm_date = date_str
    if len(date_str) == 8 and date_str.isdigit():
        norm_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    gex_data = {}
    # Try real QQQ GEX first (cache JSON)
    all_gex = _load_qqq_json()
    if all_gex:
        gex_data = all_gex.get(norm_date, {})

    if not gex_data:
        # Fall back to SPX proxy (cache JSON)
        all_gex = _load_spx_json()
        if all_gex:
            gex_data = all_gex.get(norm_date, {})

    if gex_data:
        # QQQ file uses zero_gamma_nq, call_wall_nq, put_wall_nq; SPX proxy uses zero_gamma_level, call_wall, put_wall
        zg = gex_data.get('zero_gamma_nq') or gex_data.get('zero_gamma_level', 0.0)
        cw = gex_data.get('call_wall_nq') or gex_data.get('call_wall', 0.0)
        pw = gex_data.get('put_wall_nq') or gex_data.get('put_wall', 0.0)
        source = gex_data.get('source', 'unknown')
        print(f"  [GEX] Loaded {source} for {norm_date}: Regime={gex_data.get('gex_regime')}, Flip={zg:.0f}")
        return {
            "gex_regime": gex_data.get("gex_regime", "positive"),
            "zero_gamma_level": float(zg),
            "call_wall": float(cw),
            "put_wall": float(pw),
            "net_gex_dollar": float(gex_data.get("net_gex_dollar", 0.0)),
            "qqq_spot": float(gex_data.get("qqq_spot", 0.0)),
        }

    print(f"  [GEX WARNING] No real GEX data found for {norm_date}. Returning unknown regime to prevent backtest falsification.")
    return {
        "gex_regime": "unknown",
        "zero_gamma_level": 0.0,
        "call_wall": 0.0,
        "put_wall": 0.0
    }
