import json
import os
from pathlib import Path
from typing import Tuple, Dict, Any

GEX_DATA_FILE = Path(__file__).parent.parent / 'data' / 'gex_data.json'

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
    if GEX_DATA_FILE.exists():
        try:
            with open(GEX_DATA_FILE, 'r', encoding='utf-8') as f:
                all_gex = json.load(f)
                gex_data = all_gex.get(norm_date, {})
        except Exception as e:
            print(f"  [GEX WARNING] Failed to read {GEX_DATA_FILE}: {e}")

    if gex_data:
        print(f"  [GEX] Successfully loaded GEX data for {norm_date}: Regime={gex_data.get('gex_regime')}, Flip={gex_data.get('zero_gamma_level')}")
        return {
            "gex_regime": gex_data.get("gex_regime", "positive"),
            "zero_gamma_level": float(gex_data.get("zero_gamma_level", 0.0)),
            "call_wall": float(gex_data.get("call_wall", 0.0)),
            "put_wall": float(gex_data.get("put_wall", 0.0))
        }

    # Fallback Logic:
    # 1. Use overnight Volume Profile POC as the Zero Gamma level
    # 2. Estimate regime: positive if open >= Zero Gamma, else negative
    # 3. Estimate Call Wall at POC + 150 points (600 ticks) and Put Wall at POC - 150 points (600 ticks)
    zero_gamma = 0.0
    if overnight_vp and hasattr(overnight_vp, 'poc') and overnight_vp.poc:
        zero_gamma = overnight_vp.poc
    elif opening_price:
        zero_gamma = opening_price

    regime = "positive"
    if opening_price and zero_gamma > 0:
        regime = "positive" if opening_price >= zero_gamma else "negative"

    call_wall = zero_gamma + 150.0 if zero_gamma > 0 else 0.0
    put_wall = zero_gamma - 150.0 if zero_gamma > 0 else 0.0

    print(f"  [GEX INFO] No GEX data found for {norm_date}. Using fallback estimation: Regime={regime}, Flip={zero_gamma:.2f}")
    return {
        "gex_regime": regime,
        "zero_gamma_level": zero_gamma,
        "call_wall": call_wall,
        "put_wall": put_wall
    }
