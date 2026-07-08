# 🧪 Out-Of-Sample Forward Test Report (March-June 2026)
Date: 2026-06-26 14:49:47

This report evaluates the performance of the **Claude 3.5 Sonnet Agentic Filter** during the out-of-sample forward test period from March 1, 2026 to June 30, 2026.

## 📊 Summary Performance Comparison

| Metric | Quant Baseline (No Agent) | Agentic Filtered (Sonnet) | Change |
|---|---|---|---|
| **Trades (N)** | 37 | 1 | -36 (-97.3%) |
| **Win Rate** | 32.4% | 0.0% | -32.4% |
| **Net P&L (USD)** | $1,567.50 | $-298.50 | $-1,866.00 (-119.0%) |

## 📝 Trade Log Details
- **20260302 09:35** | Setup: `ABSORB_LONG` | price: 24843.00 | Quant P&L: $-310.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260302 10:13** | Setup: `ABSORB_LONG` | price: 24938.75 | Quant P&L: $-310.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260309 10:23** | Setup: `TREND_LONG` | price: 24451.50 | Quant P&L: $-142.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260318 10:43** | Setup: `TREND_SHORT` | price: 24828.00 | Quant P&L: $-298.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260319 10:28** | Setup: `TREND_SHORT` | price: 24411.00 | Quant P&L: $-298.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260324 14:39** | Setup: `TREND_LONG` | price: 24345.25 | Quant P&L: $-142.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260326 14:51** | Setup: `TREND_LONG` | price: 23884.75 | Quant P&L: $+667.50 (WIN) | Agent Status: 🟥 REJECTED
- **20260402 09:58** | Setup: `ABSORB_LONG` | price: 23886.75 | Quant P&L: $-310.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260406 10:50** | Setup: `TREND_SHORT` | price: 24276.50 | Quant P&L: $-298.50 (LOSS) | Agent Status: 🟩 APPROVED
- **20260408 09:57** | Setup: `TREND_SHORT` | price: 25082.75 | Quant P&L: $-298.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260409 10:23** | Setup: `ABSORB_LONG` | price: 25002.50 | Quant P&L: $+679.50 (WIN) | Agent Status: 🟥 REJECTED
- **20260410 09:48** | Setup: `ABSORB_LONG` | price: 25341.00 | Quant P&L: $-310.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260416 09:59** | Setup: `ABSORB_LONG` | price: 26321.25 | Quant P&L: $+679.50 (WIN) | Agent Status: 🟥 REJECTED
- **20260417 09:51** | Setup: `ABSORB_LONG` | price: 26733.00 | Quant P&L: $-310.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260421 09:56** | Setup: `TREND_LONG` | price: 26817.50 | Quant P&L: $-142.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260429 09:53** | Setup: `ABSORB_LONG` | price: 27217.00 | Quant P&L: $-310.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260429 10:25** | Setup: `ABSORB_LONG` | price: 27246.75 | Quant P&L: $-310.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260430 10:52** | Setup: `TREND_LONG` | price: 27333.50 | Quant P&L: $+667.50 (WIN) | Agent Status: 🟥 REJECTED
- **20260506 14:49** | Setup: `TREND_SHORT` | price: 28638.50 | Quant P&L: $+667.50 (WIN) | Agent Status: 🟥 REJECTED
- **20260506 14:50** | Setup: `TREND_SHORT` | price: 28637.00 | Quant P&L: $+667.50 (WIN) | Agent Status: 🟥 REJECTED
- **20260507 09:55** | Setup: `TREND_LONG` | price: 28789.25 | Quant P&L: $-142.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260507 10:15** | Setup: `TREND_SHORT` | price: 28829.25 | Quant P&L: $+667.50 (WIN) | Agent Status: 🟥 REJECTED
- **20260512 09:43** | Setup: `ABSORB_LONG` | price: 29274.00 | Quant P&L: $-310.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260515 10:20** | Setup: `TREND_LONG` | price: 29357.00 | Quant P&L: $-142.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260518 10:40** | Setup: `TREND_LONG` | price: 29043.25 | Quant P&L: $+667.50 (WIN) | Agent Status: 🟥 REJECTED
- **20260518 10:46** | Setup: `TREND_LONG` | price: 29058.25 | Quant P&L: $+667.50 (WIN) | Agent Status: 🟥 REJECTED
- **20260520 10:21** | Setup: `TREND_LONG` | price: 29217.75 | Quant P&L: $-142.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260522 10:21** | Setup: `TREND_SHORT` | price: 29542.75 | Quant P&L: $-298.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260603 09:50** | Setup: `TREND_LONG` | price: 30554.25 | Quant P&L: $+667.50 (WIN) | Agent Status: 🟥 REJECTED
- **20260603 09:56** | Setup: `TREND_LONG` | price: 30567.25 | Quant P&L: $+667.50 (WIN) | Agent Status: 🟥 REJECTED
- **20260605 14:31** | Setup: `TREND_SHORT` | price: 29244.50 | Quant P&L: $-298.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260605 14:58** | Setup: `TREND_SHORT` | price: 29172.75 | Quant P&L: $-298.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260605 15:00** | Setup: `TREND_SHORT` | price: 29149.75 | Quant P&L: $-298.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260608 10:35** | Setup: `TREND_LONG` | price: 29573.25 | Quant P&L: $-142.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260608 15:15** | Setup: `TREND_SHORT` | price: 29431.75 | Quant P&L: $-298.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260608 15:18** | Setup: `TREND_SHORT` | price: 29418.25 | Quant P&L: $-298.50 (LOSS) | Agent Status: 🟥 REJECTED
- **20260618 10:11** | Setup: `TREND_SHORT` | price: 30558.00 | Quant P&L: $+667.50 (WIN) | Agent Status: 🟥 REJECTED
