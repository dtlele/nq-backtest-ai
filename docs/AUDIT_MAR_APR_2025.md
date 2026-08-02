# Audit Backtest mar_apr_2025

**Run**: `output/mar_apr_2025.log`  
**Periodo**: 1 Gen 2025 → 30 Apr 2025 (4 mesi)  
**Status**: Interrotto il 31 Lug 2026 (morto processo)  
**Setup**: prod3-yellow + glm-5.2 default

## Performance

| Metrica | Valore |
|---|---|
| Trade totali | 50 |
| Winners / Losers | 30 / 20 |
| **Win rate** | **60.0%** |
| **P&L totale** | **+$1,396.65** |
| Avg winner | $67.71 |
| Avg loser | ~$53.74 |
| R:R effettivo | 1.26:1 |
| Sharpe-like | 1.36 |

## Distribuzione mensile

| Mese | Trade | W/L | PnL |
|---|---|---|---|
| Gennaio | 4 | 2/2 | +$50.83 |
| Marzo | 18 | 11/7 | +$1,008.21 |
| Aprile | 25 | 17/8 | +$338.44 |

## Top 5 winner

1. 26 Mar LONG @ target: **+$269.40**
2. 8 Apr SHORT @ trailing: +$179.96
3. 30 Apr LONG @ target: $141.77
4. 23 Apr SHORT @ target: $134.13
5. 18 Mar LONG @ trailing: $98.74

## Top 5 loser

1. 17 Apr SHORT @ stop: -$53.96
2. 25 Mar LONG @ stop: -$52.70
3. 31 Mar SHORT @ stop: -$52.53
4. 17 Mar LONG @ stop: -$52.11
5. 17 Apr LONG @ stop: -$51.72

## Per exit reason

| Exit | Trade | Win% | PnL |
|---|---|---|---|
| target | 15 | 100% | +$1,344 |
| trailing_stop | 23 | 96% | +$622 |
| stop | 12 | 0% | -$1,023 |

## Confronto baseline

- prod1-yellow (Feb-Mar 2025): 48 trade, +$903, 51.9% WR
- mar_apr_2025 (Gen-Apr 2025): 50 trade, +$1396, **60.0% WR** ⭐
