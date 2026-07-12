# Acceptance Definition Exact

**Trader**: Fabio
**Knowledge Node**: acceptance_definition_exact

## Dettagli e Regole Operative
In Fabio Valentini’s model, **acceptance** is a mechanical requirement used to 
distinguish a true expansion from a "fake out" or failed auction. Based on the 
sources, here is how he defines this condition:

### **(a) Body Position vs. Close Price**
A valid breakout requires a **full-body candle close** outside the established 
range [1, 2]. 
*   **Body over Wick:** Acceptance is defined when the **candle body** (the 
rectangular portion) crosses the level [3]. If a wick pierces the high or low 
but the candle closes back inside the range, it is classified as a **failed 
auction** or a "look above and fail" rather than acceptance [1, 4].
*   **Body Content:** For high-confidence acceptance, "Big Trade" bubbles 
(filtered for 30+ contracts on NQ) should appear within the **body of the 
candle** during the breakout, signaling that aggressive participants are 
winning the battle and accepting new prices [5, 6].

### **(b) Timeframe**
The timeframe used for acceptance depends on the trader’s specific objective 
for the session:
*   **M1 (1-Minute):** Frequently used for **momentum entries** and scalping 
triggers. Fabio notes that he often waits for a "one-minute candle" to close 
with a full body above/below a sensitive level to validate an immediate move 
[7].
*   **M5 (5-Minute):** Used for **broader framing** and identifying 
session-level acceptance [8]. In his simplified model, the **Initial Volume 
Breakout (IVB)** is built from the high and low of the first 15 to 30 minutes 
of the session, and a 5-minute close outside this range is a standard signal 
for the algorithm to plot targets like the **Protection Level** [9, 10].

### **(c) Ticks Outside the Range**
The sources **do not specify a fixed numerical tick threshold** (e.g., "5 ticks
past"). Instead, acceptance is determined **qualitatively by the candle’s 
structure**:
*   **Clean Closure:** The candle must close decisively outside the boundary 
"box" [11]. 
*   **Price Discovery:** Acceptance is proven when the market stops retreating 
to the old range and begins **building new value** (Point of Control) outside 
the previous distribution [12].

### **(d) Single Candle vs. Consecutive Closes**
*   **Single Candle for Breakout:** A **single full-body close** is sufficient 
for the market to be considered "out of balance" and for algorithmic targets to
be projected [1, 9].
*   **The "Second Drive" Protocol:** Although one candle defines acceptance, 
Fabio explicitly warns **"don't take the first drive"** [13]. For a valid Trend
Following trade, he requires a breakout, a **retracement** to test the broken 
edge (or a Low Volume Node), and then a **"Second Drive"** resuming the 
original direction [13, 14]. This prevents the trader from entering a move that
is immediately riassorbito (reabsorbed) back into the range [15].