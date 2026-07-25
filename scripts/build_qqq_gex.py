"""
Build QQQ daily GEX from options parquet.
Calculates net dealer gamma exposure per day from QQQ options (real NQ proxy).

Formula: GEX = sum(gamma * OI * 100 * spot)  for all contracts
        - Calls contribute + (dealers short calls = long gamma)
        - Puts contribute - (dealers short puts = short gamma)

Uses real QQQ underlying close price (not option mark) for spot.

Output: data/qqq_gex_daily.json  (date -> {gex_value, call_gex, put_gex, net_gex, ...})
"""
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

SOURCE = Path('data/options_qqq/QQQ_options_full.parquet')
UNDERLYING = Path('data/options_qqq/QQQ_underlying.parquet')
OUTPUT = Path('data/qqq_gex_daily.json')

# NQ futures multiplier (CME) - $20/point
# QQQ option multiplier - 100 shares
# QQQ/NQ ratio is computed dynamically from underlying vs NQ
QQQ_TO_NQ_DEFAULT = 40.0

def compute_daily_gex(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute daily GEX from options data.
    GEX = sum(call_gamma_contrib) - sum(put_gamma_contrib)
    where each contrib = gamma * OI * 100 * spot
    """
    # Use close-of-day underlying price (we don't have it in options parquet)
    # Approximate with strike mid for ATM contracts
    # Better: use OI * 100 * gamma * strike^2 (dollar gamma)
    # Standard formula: gamma_dollar = gamma * OI * 100 * spot^2 / 100

    # For each row, compute dollar gamma contribution
    df = df.copy()
    # Use real QQQ underlying close price (joined on date) - NOT option mark
    spot = underlying.set_index('date')['close']
    df['spot'] = df['date'].map(spot)
    df = df.dropna(subset=['spot'])
    # Dollar gamma per contract: gamma * OI * 100 (shares) * spot / 100
    df['gamma_dollar'] = (df['gamma'].abs() * df['open_interest'].astype(float) * 100 * df['spot'])

    # Calls: positive contribution (dealers short calls = long gamma)
    is_call = (df['type'] == 'call')
    df['call_gex'] = (df['gamma_dollar'] * is_call.astype(float))
    df['put_gex']  = (df['gamma_dollar'] * (~is_call).astype(float) * -1)
    df['total_gex'] = df['call_gex'] + df['put_gex']

    # Daily aggregate
    daily = df.groupby('date', as_index=False).agg(
        call_gex=('call_gex', 'sum'),
        put_gex=('put_gex', 'sum'),
        total_volume=('volume', 'sum'),
        total_oi=('open_interest', 'sum'),
        contract_count=('contract_id', 'count'),
        avg_iv=('implied_volatility', 'mean'),
        spot_proxy=('spot', 'first'),
    )

    daily['net_gex'] = daily['call_gex'] + daily['put_gex']  # put_gex already negative

    return daily

def classify_regime(gex_dollar: float) -> str:
    """Same classification as SPX GEX (relative scale, since QQQ is smaller)."""
    if gex_dollar > 5e8:    # > $500M (QQQ scale)
        return 'positive'
    if gex_dollar < -5e8:
        return 'negative'
    return 'neutral'

def main():
    print('Loading QQQ options data...')
    df = pd.read_parquet(SOURCE)
    print(f'Loaded {len(df):,} rows')

    # Load QQQ underlying prices
    print('Loading QQQ underlying prices...')
    global underlying
    underlying = pd.read_parquet(UNDERLYING)
    underlying['date'] = pd.to_datetime(underlying['date'])
    print(f'Underlying rows: {len(underlying):,}  ({underlying["date"].min()} to {underlying["date"].max()})')

    # Filter to 2024-2025 (focus on recent)
    df = df[df['date'] >= '2024-01-01'].copy()
    print(f'Filtered to 2024+: {len(df):,} rows')

    # Drop rows with missing critical fields
    df = df.dropna(subset=['gamma', 'open_interest', 'mark'])
    df = df[df['open_interest'] > 0]
    print(f'After dropna: {len(df):,} rows')

    print('Computing daily GEX...')
    daily = compute_daily_gex(df)

    # Classify regime
    daily['gex_regime'] = daily['net_gex'].apply(classify_regime)

    # Estimate walls (largest single gamma concentration strike)
    print('Computing walls...')
    # Recompute per-row columns on main df (needed for wall aggregation)
    spot = underlying.set_index('date')['close']
    df['spot'] = df['date'].map(spot)
    df = df.dropna(subset=['spot'])
    df['gamma_dollar'] = (df['gamma'].abs() * df['open_interest'].astype(float) * 100 * df['spot'])
    is_call = (df['type'] == 'call')
    df['call_gex'] = (df['gamma_dollar'] * is_call.astype(float))
    df['put_gex']  = (df['gamma_dollar'] * (~is_call).astype(float) * -1)
    df['total_gex'] = df['call_gex'] + df['put_gex']

    walls = []
    for date, group in df.groupby('date'):
        # Top 3 strikes by total gamma (call+put)
        by_strike = group.groupby('strike', as_index=False).agg(
            total_gamma=('gamma_dollar', 'sum'),
            total_gex=('total_gex', 'sum'),
        )
        by_strike = by_strike.sort_values('total_gamma', ascending=False)
        if len(by_strike) > 0:
            call_wall = by_strike.iloc[0]['strike']  # highest gamma strike
            put_wall = by_strike.iloc[-1]['strike']   # lowest gamma strike
            walls.append({'date': date, 'call_wall_strike': call_wall, 'put_wall_strike': put_wall})
    walls_df = pd.DataFrame(walls)
    daily = daily.merge(walls_df, on='date', how='left')

    # Convert QQQ strikes to NQ equivalent levels
    daily['call_wall_nq'] = daily['call_wall_strike'] * QQQ_TO_NQ_DEFAULT
    daily['put_wall_nq'] = daily['put_wall_strike'] * QQQ_TO_NQ_DEFAULT
    daily['zero_gamma_nq'] = daily['spot_proxy'] * QQQ_TO_NQ_DEFAULT  # NQ equivalent of QQQ spot

    # Build output dict
    out = {}
    for _, row in daily.iterrows():
        d = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])[:10]
        out[d] = {
            'gex_regime': row['gex_regime'],
            'net_gex_dollar': float(row['net_gex']),
            'call_gex_dollar': float(row['call_gex']),
            'put_gex_dollar': float(row['put_gex']),
            'call_wall_nq': float(row['call_wall_nq']),
            'put_wall_nq': float(row['put_wall_nq']),
            'zero_gamma_nq': float(row['zero_gamma_nq']),
            'qqq_spot': float(row['spot_proxy']),
            'total_volume': int(row['total_volume']),
            'total_oi': int(row['total_oi']),
            'contract_count': int(row['contract_count']),
            'avg_iv': float(row['avg_iv']),
            'source': 'lambdaclass/options_portfolio_backtester (real QQQ options)',
        }

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)

    print(f'Wrote {len(out)} dates to {OUTPUT}')
    # Samples
    for d in ['2025-02-04', '2025-02-11', '2025-03-13', '2025-03-28']:
        if d in out:
            r = out[d]
            print(f'  {d}: regime={r["gex_regime"]:<8} net_gex=${r["net_gex_dollar"]/1e9:+5.2f}B  '
                  f'call_wall_NQ={r["call_wall_nq"]:.0f}  put_wall_NQ={r["put_wall_nq"]:.0f}')

if __name__ == '__main__':
    main()
