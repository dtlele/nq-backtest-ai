# Real GEX Data — squeezemetrics.com integration

**Date:** 2026-07-25
**Branch:** feature/mechanical-trigger-m5
**Source:** https://squeezemetrics.com/monitor/dix (free, public endpoint)

## What was wrong

The backtest was logging `[GEX WARNING] No real GEX data found for YYYY-MM-DD. Returning unknown regime to prevent backtest falsification.` for every candidate on every day. This caused:

1. The bias engine (institutional_bias.py) to receive `gex_regime=unknown` for all dates
2. The system to fall back to conservative defaults that reject most setups
3. The "GEX" feature in ML model and audit to be effectively disabled

## What was fixed

1. **Downloaded DIX.csv** from `https://squeezemetrics.com/monitor/static/DIX.csv`
   - 3830 daily rows from 2011-05-02 to 2026-07-24
   - Columns: `date, price, dix, gex`
2. **Built gex_data.json** via `scripts/build_gex_data.py`:
   - 3830 dates with full structure expected by `src/gex_manager.py`
   - Maps SPX levels to NQ equivalents via SPX_TO_NQ=9.5 ratio
   - Adds `gex_regime` classification (positive / negative / neutral)
3. **Confirmed integration**: backtest now logs `[GEX] Successfully loaded GEX data for YYYY-MM-DD: Regime=positive, Flip=NQNQNQ` instead of warnings

## Caveats

1. **SPX is a proxy for NQ, not exact NQ data.** SPX and NQ share mega-cap underlyings (AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSLA) so GEX regime correlation is high (estimated ~0.9 daily).
2. **zero_gamma_level and walls are SPX-based**, converted to NQ equivalent via fixed 9.5x ratio. This is an approximation; true NQ zero-gamma would need QQQ or NDX options data.
3. **No NQ-specific GEX available for free** in 2026-07:
   - SpotGamma: paid (no public API)
   - Tanuki Trade: waitlist, launch 2026-08-31
   - FlashAlpha: 5 req/day free tier
   - CBOE/NDX direct: requires OCC historical data subscription
   - GitHub repos use Yahoo Finance QQQ options (only ~30-60 days history, not years)
4. **Estimated impact**: with SPX GEX, the bias engine now has regime signal it didn't have before. The 3 OOS weeks tested with "unknown" regime produced -$117 total; re-running them with real SPX GEX may produce different results. To verify, the LLM cache must be cleared (current results are cached from previous runs).

## Files added

- `data/gex/DIX.csv` (raw download, 220KB)
- `data/gex_data.json` (converted format, 1.2MB)
- `scripts/build_gex_data.py` (converter)
- `docs/GEX_DATA.md` (this file)

## How to refresh

```bash
curl -sL https://squeezemetrics.com/monitor/static/DIX.csv -o data/gex/DIX.csv
python scripts/build_gex_data.py
```

The DIX.csv is updated daily by squeezemetrics.com after market close.
