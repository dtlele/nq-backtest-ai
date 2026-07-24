# V1 Baseline Weekly Tracker

**Status:** Tracking V1 (default audit, 100% confirm) on each week of NQ data.
**Cost per week:** ~$0.50 (varies with management calls)
**Config:** `AUDIT_PROMPT_VERSION=v1` (default)

## 📊 Weekly Results

| Week | Period | Trades | WR | P&L | Rejects | Cost | Notes |
|---|---|---|---|---|---|---|---|
| V8b | 2025-02-04 to 02-11 | 3 | 33% | **+$666** | 0 | $0 | Best run, +$766 LONG 11 Feb 10:50 |
| V19 | 2025-02-18 to 02-22 | 4 | 75% | **+$474** | 0 | $0.50 | 3 wins, 1 stop |
| V21 | 2025-02-24 to 02-28 | 17 | 35.3% | **+$80** | 0 | $0.78 | 6 wins, 11 stops (whipsaw week) |
| **TOTAL** | 13 days | 24 | 39% | **+$1,220** | 0 | $1.28 | |

## 🔍 Observations

### W08 (V8b, 04-11 Feb): BEST +$666
- 3 trades, 33% WR but with 2.0 R:R → profitable
- Key win: LONG 11 Feb 10:50 +$766 (pullback absorption, drive_up +83)
- 2 stops: -$50 each
- Net: +$666

### W08 (V19, 18-22 Feb): GOOD +$474
- 4 trades, 75% WR
- Key: SHORT 22018 won big (drive_down -83, 201-lot SELL)
- 1 stop: -$50
- Net: +$474

### W09 (V21, 24-28 Feb): MARGINAL +$80
- 17 trades, 35.3% WR (above breakeven)
- 6 wins, 11 stops
- 6 SHORTs, 11 LONGs (mostly wrong direction)
- High trade count = high management call cost (~$0.78)
- The market was in a strong downtrend (NQ dropped from 21600 to 20500)
- LLM kept shorting but getting stopped on bounces
- Net: barely +$80

## 💡 Key Insights

1. **V1 baseline IS profitable** but with high variance (+$80 to +$666 per week)
2. **High WR weeks (75%) are rare** — most weeks 30-40% WR with 2:1 R:R
3. **W09 shows the failure mode**: high trade count, lots of management calls, marginal profitability
4. **Management calls are expensive** (~$0.50-0.80 per week) — they eat into profitability
5. **The Feb 24-28 downtrend was difficult** — the LLM kept fighting the trend

## 📅 Remaining weeks to test (with $5.50 budget)

- W10 (Mar 3-7)
- W19 (May 5-9)
- W20 (May 12-16)
- W23 (Jun 2-6)
- W24 (Jun 9-13)

Each week: ~$0.50-0.80 → can run ~6-10 more weeks

## 🎯 Goal

Establish a robust V1 baseline across 10+ weeks. If average P&L/week is positive, V1 is the strategy to keep. If negative, we need to find a different approach.
