# Optimal Filters Optimization Report
Date: 2026-06-26 22:43:05

This report details the findings from a grid search optimization run on the unified NQ futures strategy backtest script over historical sequences from 2025 and 2026.

## Executive Summary
- **Baseline Scenario Performance:**
  - Net Profit: **$9,291.00**
  - Trades: **545**
  - Win Rate: **40.9%**
  - Profit Factor: **1.12**
  - Max Drawdown: **$4,288.50**

### Best Configuration by Profit Factor (Overall, N >= 80)
- **Setups:** `trend_long+absorb_long+trend_short`
- **CVD Climax:** `Th=2000` (Target: `all`)
- **Contrary Big Trade:** `Th=250`
- **Trading Hours:** Morning End: `11:00` | Afternoon Start: `14:30` | Lunch Excl: `True`
- **Value Area Filters:** Short Inside VA: `True` | Long Inside VA: `True` | Long Below VA: `False`
- **Volume Filter:** `original`
- **Results:**
  - Net Profit: **$12,535.50** (Improvement: **+$3,244.50**)
  - Trades: **88**
  - Win Rate: **51.1%**
  - Profit Factor: **2.12** (Improvement: **+1.00**)
  - Max Drawdown: **$1,575.00**

### Best Configuration with Drawdown Constraint (Max DD < $2,000, N >= 80)
- **Setups:** `trend_long+absorb_long+trend_short`
- **CVD Climax:** `Th=2000` (Target: `all`)
- **Contrary Big Trade:** `Th=250`
- **Trading Hours:** Morning End: `11:00` | Afternoon Start: `14:30` | Lunch Excl: `True`
- **Value Area Filters:** Short Inside VA: `True` | Long Inside VA: `True` | Long Below VA: `False`
- **Volume Filter:** `original`
- **Results:**
  - Net Profit: **$12,535.50**
  - Trades: **88**
  - Win Rate: **51.1%**
  - Profit Factor: **2.12**
  - Max Drawdown: **$1,575.00** (Safe for $50k prop account!)

## Top 20 Configurations Sorted by Profit Factor (Overall, N >= 80)

| Rank | Active Setups | CVD Climax | Contrary BT | Trading Hours | VA Filters | Vol Filter | Trades | Win Rate | Net PnL | Profit Factor | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | trend_long+absorb_long+trend_short | Th=2000 (all) | Th=250 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 88 | 51.1% | $12,535.50 | 2.12 | $1,575.00 |
| 2 | trend_long+absorb_long+trend_short | Th=2000 (all) | Th=300 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 88 | 51.1% | $12,535.50 | 2.12 | $1,575.00 |
| 3 | trend_long+absorb_long+trend_short | Th=2000 (all) | Th=200 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 86 | 50.0% | $11,752.50 | 2.05 | $1,635.00 |
| 4 | trend_long+absorb_long | Th=2000 (only_absorption) | Th=250 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 86 | 46.5% | $10,330.50 | 2.03 | $1,210.50 |
| 5 | trend_long+absorb_long | Th=2000 (only_absorption) | Th=250 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=False,L_In=True,L_Bel=False | original | 86 | 46.5% | $10,330.50 | 2.03 | $1,210.50 |
| 6 | trend_long+absorb_long | Th=2000 (only_absorption) | Th=300 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 86 | 46.5% | $10,330.50 | 2.03 | $1,210.50 |
| 7 | trend_long+absorb_long | Th=2000 (only_absorption) | Th=300 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=False,L_In=True,L_Bel=False | original | 86 | 46.5% | $10,330.50 | 2.03 | $1,210.50 |
| 8 | trend_long+absorb_long+trend_short | Th=2000 (all) | None | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 92 | 50.0% | $12,271.50 | 2.01 | $1,575.00 |
| 9 | absorb_long+trend_short | Th=2000 (only_absorption) | Th=250 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 89 | 52.8% | $12,829.50 | 2.00 | $1,522.50 |
| 10 | absorb_long+trend_short | Th=2000 (only_absorption) | Th=300 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 89 | 52.8% | $12,829.50 | 2.00 | $1,522.50 |
| 11 | trend_long+absorb_long+absorb_short | Th=2000 (all) | Th=150 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 95 | 53.7% | $10,147.50 | 2.00 | $835.50 |
| 12 | trend_long+absorb_long+trend_short | Th=2000 (only_absorption) | Th=150 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 112 | 46.4% | $13,909.50 | 1.97 | $1,354.50 |
| 13 | trend_long+absorb_long+trend_short | Th=2000 (all) | Th=250 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=True | original | 82 | 50.0% | $10,582.50 | 1.97 | $1,575.00 |
| 14 | trend_long+absorb_long+trend_short | Th=2000 (all) | Th=300 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=True | original | 82 | 50.0% | $10,582.50 | 1.97 | $1,575.00 |
| 15 | trend_short+absorb_short | Th=1000 (only_absorption) | None | M_End=11:00 | A_Start=13:30 | LunchExcl=False | S_In=True,L_In=True,L_Bel=True | original | 83 | 55.4% | $9,660.00 | 1.96 | $1,423.50 |
| 16 | trend_short+absorb_short | Th=1000 (only_absorption) | None | M_End=11:00 | A_Start=13:30 | LunchExcl=False | S_In=True,L_In=True,L_Bel=False | original | 83 | 55.4% | $9,660.00 | 1.96 | $1,423.50 |
| 17 | trend_short+absorb_short | Th=1000 (only_absorption) | None | M_End=11:00 | A_Start=13:30 | LunchExcl=False | S_In=True,L_In=False,L_Bel=True | original | 83 | 55.4% | $9,660.00 | 1.96 | $1,423.50 |
| 18 | trend_short+absorb_short | Th=1000 (only_absorption) | None | M_End=11:00 | A_Start=13:30 | LunchExcl=False | S_In=True,L_In=False,L_Bel=False | original | 83 | 55.4% | $9,660.00 | 1.96 | $1,423.50 |
| 19 | trend_long+absorb_long | Th=2000 (only_absorption) | Th=200 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 84 | 45.2% | $9,547.50 | 1.95 | $1,210.50 |
| 20 | trend_long+absorb_long | Th=2000 (only_absorption) | Th=200 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=False,L_In=True,L_Bel=False | original | 84 | 45.2% | $9,547.50 | 1.95 | $1,210.50 |

## Top 20 Configurations with Drawdown Constraint (Max DD < $2,000, N >= 80)

| Rank | Active Setups | CVD Climax | Contrary BT | Trading Hours | VA Filters | Vol Filter | Trades | Win Rate | Net PnL | Profit Factor | Max DD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | trend_long+absorb_long+trend_short | Th=2000 (all) | Th=250 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 88 | 51.1% | $12,535.50 | 2.12 | $1,575.00 |
| 2 | trend_long+absorb_long+trend_short | Th=2000 (all) | Th=300 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 88 | 51.1% | $12,535.50 | 2.12 | $1,575.00 |
| 3 | trend_long+absorb_long+trend_short | Th=2000 (all) | Th=200 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 86 | 50.0% | $11,752.50 | 2.05 | $1,635.00 |
| 4 | trend_long+absorb_long | Th=2000 (only_absorption) | Th=250 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 86 | 46.5% | $10,330.50 | 2.03 | $1,210.50 |
| 5 | trend_long+absorb_long | Th=2000 (only_absorption) | Th=250 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=False,L_In=True,L_Bel=False | original | 86 | 46.5% | $10,330.50 | 2.03 | $1,210.50 |
| 6 | trend_long+absorb_long | Th=2000 (only_absorption) | Th=300 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 86 | 46.5% | $10,330.50 | 2.03 | $1,210.50 |
| 7 | trend_long+absorb_long | Th=2000 (only_absorption) | Th=300 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=False,L_In=True,L_Bel=False | original | 86 | 46.5% | $10,330.50 | 2.03 | $1,210.50 |
| 8 | trend_long+absorb_long+trend_short | Th=2000 (all) | None | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 92 | 50.0% | $12,271.50 | 2.01 | $1,575.00 |
| 9 | absorb_long+trend_short | Th=2000 (only_absorption) | Th=250 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 89 | 52.8% | $12,829.50 | 2.00 | $1,522.50 |
| 10 | absorb_long+trend_short | Th=2000 (only_absorption) | Th=300 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 89 | 52.8% | $12,829.50 | 2.00 | $1,522.50 |
| 11 | trend_long+absorb_long+absorb_short | Th=2000 (all) | Th=150 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 95 | 53.7% | $10,147.50 | 2.00 | $835.50 |
| 12 | trend_long+absorb_long+trend_short | Th=2000 (only_absorption) | Th=150 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 112 | 46.4% | $13,909.50 | 1.97 | $1,354.50 |
| 13 | trend_long+absorb_long+trend_short | Th=2000 (all) | Th=250 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=True | original | 82 | 50.0% | $10,582.50 | 1.97 | $1,575.00 |
| 14 | trend_long+absorb_long+trend_short | Th=2000 (all) | Th=300 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=True | original | 82 | 50.0% | $10,582.50 | 1.97 | $1,575.00 |
| 15 | trend_short+absorb_short | Th=1000 (only_absorption) | None | M_End=11:00 | A_Start=13:30 | LunchExcl=False | S_In=True,L_In=True,L_Bel=True | original | 83 | 55.4% | $9,660.00 | 1.96 | $1,423.50 |
| 16 | trend_short+absorb_short | Th=1000 (only_absorption) | None | M_End=11:00 | A_Start=13:30 | LunchExcl=False | S_In=True,L_In=True,L_Bel=False | original | 83 | 55.4% | $9,660.00 | 1.96 | $1,423.50 |
| 17 | trend_short+absorb_short | Th=1000 (only_absorption) | None | M_End=11:00 | A_Start=13:30 | LunchExcl=False | S_In=True,L_In=False,L_Bel=True | original | 83 | 55.4% | $9,660.00 | 1.96 | $1,423.50 |
| 18 | trend_short+absorb_short | Th=1000 (only_absorption) | None | M_End=11:00 | A_Start=13:30 | LunchExcl=False | S_In=True,L_In=False,L_Bel=False | original | 83 | 55.4% | $9,660.00 | 1.96 | $1,423.50 |
| 19 | trend_long+absorb_long | Th=2000 (only_absorption) | Th=200 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=True,L_In=True,L_Bel=False | original | 84 | 45.2% | $9,547.50 | 1.95 | $1,210.50 |
| 20 | trend_long+absorb_long | Th=2000 (only_absorption) | Th=200 | M_End=11:00 | A_Start=14:30 | LunchExcl=True | S_In=False,L_In=True,L_Bel=False | original | 84 | 45.2% | $9,547.50 | 1.95 | $1,210.50 |

## Key Findings & Recommendations
1. **Trading Hours:** Setting structured trading windows and excluding the high-variance lunch period shows a significant improvement in reducing maximum drawdowns.
2. **CVD Climax & Contrary Trades:** Using Contrary Big Trade filters helps filter out trades that are going directly against heavy block trade pressure.
3. **Value Area Filters:** Restricting short trades inside the Value Area and long trades below the Value Area prevents entering trend-following trades in low-probability locations.
