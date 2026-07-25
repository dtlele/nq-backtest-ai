"""
Build gex_data.json from squeezemetrics.com DIX.csv.

Source: https://squeezemetrics.com/monitor/static/DIX.csv
Format: date,price,dix,gex (SPX-based, but highly correlated with NQ since both track mega-caps)

GEX regime classification:
  - gex > 0: positive (dealers dampen vol, mean reversion favored)
  - gex < 0: negative (dealers amplify vol, trends favored)
  - |gex| < 1B: neutral

NQ/SPX conversion factor (~9.5x for NQ futures vs SPX, varies with VIX).
For backtest purposes, we use SPX levels as a proxy regime indicator,
NOT exact NQ price levels (since NQ/SPX correlation is ~0.9 daily).
"""
import csv
import json
from pathlib import Path
from datetime import datetime

SOURCE = Path('data/gex/DIX.csv')
OUTPUT = Path('data/gex_data.json')

# SPX-to-NQ conversion (futures ratio, ~9.5x for NQ vs SPX in 2025-26)
# Used to translate zero_gamma_level and walls from SPX to NQ equivalent
SPX_TO_NQ = 9.5

def classify_regime(gex: float) -> str:
    """Classify GEX regime from dollar value (in $)."""
    if gex > 1e9:    # > $1B
        return 'positive'
    if gex < -1e9:   # < -$1B
        return 'negative'
    return 'neutral'

def estimate_walls(gex: float, spx_price: float) -> tuple:
    """
    Estimate call_wall and put_wall from GEX magnitude and price.

    These are rough proxies — true values require per-strike OI data.
    Higher |GEX| = stronger walls further from current price.
    """
    # Wall distance scales with |GEX| and inversely with price
    gex_billions = abs(gex) / 1e9
    if gex_billions < 0.5:
        # Low GEX, walls are tight
        wall_distance_pct = 0.005  # 0.5% from current
    elif gex_billions < 2.0:
        wall_distance_pct = 0.015  # 1.5%
    elif gex_billions < 5.0:
        wall_distance_pct = 0.025  # 2.5%
    else:
        wall_distance_pct = 0.04   # 4%

    wall_distance = spx_price * wall_distance_pct

    # Call wall above, put wall below (for positive GEX — inverse for negative)
    if gex > 0:
        call_wall = spx_price + wall_distance
        put_wall = spx_price - wall_distance
    else:
        # Negative GEX: walls invert (dealers long calls, short puts)
        call_wall = spx_price - wall_distance * 0.5  # closer
        put_wall = spx_price + wall_distance * 0.5

    return call_wall, put_wall

def main():
    if not SOURCE.exists():
        print(f"ERROR: {SOURCE} not found. Download from:")
        print("  curl -sL https://squeezemetrics.com/monitor/static/DIX.csv -o data/gex/DIX.csv")
        return 1

    out = {}
    with open(SOURCE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row['date']
            try:
                spx_price = float(row['price'])
                dix = float(row['dix'])
                gex = float(row['gex'])
            except (ValueError, KeyError):
                continue

            regime = classify_regime(gex)
            call_wall_sp, put_wall_sp = estimate_walls(gex, spx_price)

            # Convert SPX levels to NQ equivalent (futures ratio)
            out[date] = {
                'gex_regime': regime,
                'gex_value': gex,                        # raw dollars
                'dix_value': dix,                        # 0-1, dark pool sentiment
                'zero_gamma_level': spx_price * SPX_TO_NQ,  # NQ-equivalent zero gamma
                'call_wall': call_wall_sp * SPX_TO_NQ,      # NQ-equivalent call wall
                'put_wall': put_wall_sp * SPX_TO_NQ,        # NQ-equivalent put wall
                'spx_close': spx_price,                     # for reference
                'source': 'squeezemetrics.com (SPX proxy)',
            }

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)

    print(f"Wrote {len(out)} dates to {OUTPUT}")
    print(f"Date range: {min(out)} to {max(out)}")
    # Show some samples
    for d in ['2025-02-04', '2025-02-11', '2025-03-13', '2025-03-28']:
        if d in out:
            r = out[d]
            print(f"  {d}: regime={r['gex_regime']:<8} gex=${r['gex_value']/1e9:+5.2f}B  "
                  f"dix={r['dix_value']:.3f}  zero_gamma_NQ={r['zero_gamma_level']:.0f}")

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
