# Master Trading Manual (Fabio + Andrea Core Principles)

## Backtested Confidence Calibration (Empirical Heuristics from 549 Trades)

1. **Structure Convergence**: IBL + VAL converging at the same level = strongest setup historically (59% WR).
   VAH or VAL alone WITHOUT IB confirmation = weak signal (22-31% WR). Subtract 10-15 from confidence.
2. **Institutional Footprint**: Big Trade >= 1000 contracts at the breakout point = strong confirmation (+10 confidence).
   High total bar volume (>3000 contracts) BUT small Big Trade = likely retail fakeout.
   The SIZE of the single institutional order matters more than total volume.
3. **Delta Conviction**: |Delta| >= 600 at entry bar = real directional commitment, confirmed.
   |Delta| < 300 = market in chop/equilibrium, subtract 10 from confidence.
4. **Entry Precision**: Is the entry point structurally sound? High scores MUST be given if EITHER: (A) price is actively pulling back to a boundary, OR (B) a pullback (EVEN A SHALLOW ONE) occurred recently and the current bar shows momentum/absorption confirming the resumption of the trend. In a strong trend, pullbacks are often shallow. Do not enter at the very top of a vertical breakout bar (FOMO) because the inevitable pullback will hit your stop loss. Only give high scores to entries that occur DURING or AFTER a pullback.

## Core Setup Classifications (Triple A Setups)

### ivb_model_1_continuation
**Description**: Trend continuation on a pullback to a key level (VAH/VAL, POC, LVN) after a confirmed Initial Volume Breakout (IVB) breakout
**Trigger**: Price breaks outside the IVB range with institutional aggression, then retraces to a key level where sellers/buyers stall.
**Confirmation**: Look for institutional absorption (large Big Trades, delta divergence) on the pullback, followed by a 'Second Drive' resuming the trend in the breakout direction.

### momentum_squeeze
**Description**: Trapped traders squeeze in trend direction
**Trigger**: Aggressive participants hit a level (e.g. IB edge, swing extreme) but are absorbed by passive limits, trapping them.
**Confirmation**: When price breaks past the trapped trader cluster, it triggers a fast liquidation squeeze. Stop is placed tightly behind the defending wall.

## Auction Market Theory (AMT) Mechanics

### PUNCH IN THE WALL MECHANICS (INTEGRATED IN TREND BREAKOUTS)
On directional trend days, counter-trend aggression is absorbed at key levels:
- NEGATIVE DELTA at new HIGHS = sellers 'punching the wall' of institutional buyers (reload zone for longs).
- POSITIVE DELTA at new LOWS = buyers 'punching the wall' of institutional sellers (reload zone for shorts).
This is evaluated strictly within the context of the IVB_BREAKOUT continuation phase (second drive). Enter immediately near the absorption cluster. Do not wait for the candle to close. Lock in a tight entry within 10-20 ticks of the big-trade wall to secure a massive risk-to-reward ratio.

### V3 PREDATORY EXECUTION RULES (M5 CONTEXT + M1 TIMING)
1. UNIFIED REACTION: Do NOT wait for M5 or M1 candlestick closure.
2. INSTANT ENTRY ON ABSORPTION: Enter via MARKET ORDER the exact moment you identify institutional absorption on the M1 Footprint (Big Trades hitting a wall and failing to progress).
3. PREDATOR ENTRY: Your entry must be within 10-20 ticks of the Big Trade cluster. Late entries are strictly prohibited.
4. INVALIDATION STOP: Use tight, structural stops placed 2-3 ticks behind the institutional big-trade wall. If the wall is breached, accept the invalidation immediately.
5. HTF ALIGNMENT: Prioritize setups aligned with the dominant trend. Avoid fading strong one-timeframe-moves unless clear exhaustion is confirmed.

### INITIATIVE BREAKOUTS & ACCEPTANCE (TRANSITION TO IMBALANCE)
During a breakout, do NOT enter on the first break. You must wait for ACCEPTANCE. Acceptance means sustained volume and price action outside the structural level. Look for constant aggression pushing price into the new imbalance zone, and the counter-party failing to push it back.

### IMBALANCE_HUNTING MECHANICS (M1 FAST LOOP)
When the market breaks the Initial Balance (IB) and enters an IMBALANCE state, price discovery occurs rapidly. You will be fed M1 (1-minute) candles to evaluate entries in real-time.
1. TREND ALIGNMENT: Below IB Low = SHORT trend. Above IB High = LONG trend. Do NOT fade an imbalance phase.
2. M1 MOMENTUM SIGNALS: Look for aggressive Big Trades in the direction of the breakout. If Delta is extremely directional (e.g., highly negative for a short), this is an immediate entry signal.
3. TRAPPED VS ABSORPTION: In an explosive imbalance, counter-trend participants are often run over (Limit orders swept). If you see positive Delta during a massive down-candle, it is NOT necessarily 'trapped buyers' reversing the trend, but rather passive buyers getting destroyed by market sellers (Limit Absorption). Do NOT let counter-trend delta stop you from entering if the overall M1 momentum and Big Trades heavily favor the breakout direction.
4. EXECUTE QUICKLY: Do not wait for M5 structural pullbacks. Enter the momentum on the M1 candle that shows aggressive continuation.

## Fabio's Aggressive Framework

### squeeze_definition
A squeeze occurs when traders are trapped against a structural wall, forcing them to cover.

### squeeze_entry_trigger
Enter when the trapped side shows exhaustion (delta divergence).

### simplified_day_type_quick
Trend Day: one-sided. Balance Day: rotates around POC.

### aplus_setup
Trend day + pullback to VWAP/POC + absorption = A+ setup.

### punches_to_wall
Look for 3+ Big Trades hitting the same level and failing to break it.

### punch_in_wall_trend_continuation
CRITICAL: On TREND days (trend_up or trend_down) or IMBALANCE sessions, 'Punches to the Wall' are NOT reversal signals — they are CONTINUATION signals. TREND_UP + strong negative delta at highs = sellers absorbed by institutional buyers. Next 1-3 candles: price stabilizes → LONG continuation entry. TREND_DOWN + strong positive delta at lows = buyers absorbed by institutional sellers. Next 1-3 candles: price stabilizes → SHORT continuation entry. NEVER call a punch at the highs a short signal on a trend_up day. It is a reload zone for longs.

### big_trades_filter
Big trades must be >30 contracts to matter.

### coherence_of_information
Ensure M5 trend, M1 delta, and Bookmap liquidity align.

### counter_trend_rules
Counter trend requires a hard structural stop and clear absorption of the dominant trend.

### entry_mechanics
Market order exactly at the moment of absorption or initiative acceptance.

### initiative_vs_absorption
While Institutional Absorption (passive limit orders stopping price) is a premium A+ setup, you MUST ALSO trade INITIATIVE setups. If you see strong INITIATIVE Big Trades (aggressive market orders pushing price) and the auction rewards them (price accepts the new level), enter in the direction of the initiative. Protect your Stop Loss behind the origin of those initiative Big Trades.
