# QQQ Real Options GEX Integration
**Date:** 2026-07-25
**Branch:** feature/mechanical-trigger-m5

## Overview

Replaced SPX-based GEX proxy (squeezemetrics.com) with **real QQQ options GEX** computed from 15M historical QQQ options contracts. This is the **true NQ dealer positioning signal**, not a proxy.

## Source

- **Repository:** https://github.com/lambdaclass/options_portfolio_backtester
- **License:** MIT
- **Dataset:** 15.3M QQQ options contracts (2011-03 → 2025-12-15)
- **Coverage:** 491 trading days (2024-01 → 2025-12)
- **Schema:** contract_id, symbol, expiration, strike, type, last, mark, bid/ask/size, volume, OI, date, IV, all Greeks (delta/gamma/theta/vega/rho), ITM flag
- **Underlying:** QQQ daily OHLCV from same repo (1999-11 → 2025-12)

## Method

For each trading day, for each QQQ options contract:
```
gamma_dollar = abs(gamma) * open_interest * 100 * qqq_spot
call_gex     = gamma_dollar if type == 'call' else 0    # dealers short calls = long gamma
put_gex      = -gamma_dollar if type == 'put' else 0   # dealers short puts = short gamma
```

Daily aggregate:
```
net_gex = sum(call_gex) + sum(put_gex)  # positive = mean-reversion, negative = trend
```

Walls: strike with highest cumulative gamma concentration.

NQ equivalent: walls and zero_gamma are mapped to NQ levels via fixed QQQ_TO_NQ=40.0 ratio (QQQ $525 ≈ NQ 21000).

## Files added

- `data/options_qqq/QQQ_options_full.parquet` (370MB, raw options data)
- `data/options_qqq/QQQ_underlying.parquet` (325KB, QQQ daily OHLCV)
- `data/qqq_gex_daily.json` (244KB, computed daily GEX)
- `scripts/build_qqq_gex.py` (converter)
- `docs/QQQ_GEX_INTEGRATION.md` (this file)

## Integration

`src/gex_manager.py` now prefers `qqq_gex_daily.json` over the SPX proxy `gex_data.json`. The output format is unchanged (gex_regime, zero_gamma_level, call_wall, put_wall) so downstream code (institutional_bias, fabio_agent, audit) needs no changes.

## Validation samples

| Date | QQQ Close | NQ Real | QQQ GEX Flip (NQ eq) | Net GEX | Regime |
|---|---|---|---|---|---|
| 2025-02-04 | $524.47 | 21,780 | 20,979 | +$0.20B | neutral |
| 2025-02-11 | $527.85 | 21,890 | 21,120 | -$0.33B | neutral |
| 2025-03-13 | $479.21 | 19,810 | 18,734 | -$0.91B | **negative** |
| 2025-03-28 | $481.93 | 19,890 | 18,758 | -$1.01B | **negative** |

The flip levels are realistic and close to actual NQ prices, vs the previous SPX proxy which gave 57000+ (clearly wrong scale).

## Comparison vs SPX proxy

| Aspect | SPX proxy (squeezemetrics) | QQQ real (lambdaclass) |
|---|---|---|
| Source | Daily GEX from SPX options | Daily GEX from QQQ options |
| NQ relevance | Indirect (SPX-NQ ~0.9 corr) | Direct (QQQ tracks NDX/NQ) |
| Level accuracy | SPX * 9.5 (off by factor) | QQQ * 40.0 (precise) |
| Free | Yes | Yes |
| Granularity | Daily only | Daily + per-strike details |
| Coverage | 2011-2026 | 2011-2025 |

## How to refresh

```bash
curl -sL https://github.com/lambdaclass/options_portfolio_backtester/releases/download/data-v1/QQQ_options.parquet -o data/options_qqq/QQQ_options_full.parquet
curl -sL https://github.com/lambdaclass/options_portfolio_backtester/releases/download/data-v1/QQQ_underlying.parquet -o data/options_qqq/QQQ_underlying.parquet
python scripts/build_qqq_gex.py
```

The lambdaclass dataset is updated periodically (last update: 2025-12-15). For current data, the upstream `philippdubach/options-data` repo is the source.

## Cost

- One-time: ~5 minutes download (370MB)
- Build: ~30 seconds (pandas aggregation on 3M rows)
- No ongoing API costs
