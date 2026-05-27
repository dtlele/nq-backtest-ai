import json

file_path = 'knowledge/fabio_knowledge.json'

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Update entry_mechanics (or add a clearer timing_entry_precision)
data['knowledge_by_topic']['timing_entry_precision'] = """
Fabio Valentini's entry timing is a two-step process that combines the structural framing of the 5-minute (M5) chart with the tactical precision of the 1-minute (M1) Footprint [1, 2].

### The M5 Setup vs. M1 Trigger
*   **Identification (M5):** He uses the M5 timeframe to identify the broad setup, such as an institutional absorption or a Failed Auction at an extreme (VAH, VAL, IB) [2].
*   **The M1 Confirmation Rule:** He does **NOT** wait for the M5 candle to close to validate the rejection. Instead, once the M5 rejection is visible, he drops to the M1 chart and waits for a **full-body M1 candle close** outside the rejection level [2, 5].
*   **Filtering "Fake Outs":** Waiting for the M1 close is mandatory. If price pierces the level but the 1-minute candle closes back inside the rejected "box," the setup is a "fake out" and no trade is taken [2, 6].

### Optimization of Risk/Reward
*   **Tactical Entry:** By entering on the confirmed M1 close instead of waiting for the full M5, Fabio significantly improves his R:R ratio, often achieving 1:4 to 1:10 returns [7].
*   **Footprint Confirmation:** A high-confidence entry is further validated if a large "cell" (Big Trade) of the opposing aggressive force is clearly destroyed during the M1 breakout [4].
""".strip()

# Add conflict_resolution_pingpong
data['knowledge_by_topic']['conflict_resolution_pingpong'] = """
When the institutional flow is in conflict (e.g., buyers and sellers are both showing absorption at different levels in a range), Fabio Valentini switches from a trend-following mindset to a balance-room mindset [1, 2].

### 1. CVD as the Bias Decider
*   **CVD as a Proxy:** Since the Big Trades filter might show equal fighting on both sides, he uses the **Cumulative Volume Delta (CVD)** to determine which side is exerting more pressure ("pushing on the gas") [2].
*   **Validation Required:** Even if CVD shows a clear distribution/accumulation bias, he remains **FLAT** until the price itself validates the direction through a breakout and a follow-up volume spike [4, 5].
*   **Mixed CVD = No Trade:** If even the CVD is oscillating without direction, his rule is absolute: **"Do not interact here"** [2, 3].

### 2. The "Ping-Pong" Model (Mean Reversion)
*   **Range Trading:** Instead of trying to guess the breakout direction in a choppy range, he adopts a "Ping-Pong" model [6].
*   **Execution:** He buys the absorption at the lower range limit and sells the absorption at the upper range limit, treating the market as a bouncing ball between institutional walls [6, 7].
*   **Tight Stops:** This mode requires extremely tight "Hard Stops" behind the identified Big Trade bubbles [7].
""".strip()

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Updated knowledge/fabio_knowledge.json with Timing and Conflict rules.")
