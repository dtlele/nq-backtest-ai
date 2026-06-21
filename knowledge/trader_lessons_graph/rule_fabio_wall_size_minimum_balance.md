# Wall Size Minimum Balance

**Trader**: Fabio
**Knowledge Node**: wall_size_minimum_balance

## Dettagli e Regole Operative
Based on Fabio Valentini’s model and recent live sessions, there is no single, 
rigid "minimum" contract number that acts as a magic threshold; however, **300 
contracts** at a single horizontal tick is explicitly cited as a **"perfect 
example"** of a valid institutional wall [1].

The decision to trade on a balance day is **primarily contextual**, governed by
the Law of Effort vs. Result and the specific location of the volume cluster.

### **1. The Numerical Benchmark (300+ Contracts)**
While Fabio uses a baseline filter of **30 contracts** to identify a single 
"Big Trade" bubble on NASDAQ [2], a protective "wall" is formed by a stacked 
cluster of these bubbles. 
*   **The "300 Rule":** In a specific example of absorption, Fabio identifies a
cluster totaling **300 contracts** (composed of individual trades like 72, 61, 
60, and 62) hitting one level with "zero results" as the ideal signature for a 
trade [1].
*   **Cluster Density:** Seeing a "mega-cluster" of approximately **8-10 big 
buyer/seller bubbles** striking the same tick or a narrow 2-tick range is the 
visual requirement for a wall [3, 4].

### **2. Why the "455 Contracts at HVN" was Skipped**
The specific backtesting example you mentioned (455 contracts skipped at an 
HVN) highlights the **Location Rule** in Fabio’s model:
*   **HVNs are Magnets, not Walls:** Fabio notes that **High Volume Nodes 
(HVNs)** are the levels the market touches with the *highest* probability and 
where price is most likely to station [5]. Trading at an HVN often means you 
are trading in the "middle" or "zone of chop," which Fabio explicitly forbids 
on balance days [6, 7].
*   **Walls require "Low Volume" Context:** A valid protective wall should 
ideally appear at the **periphery** (IVB High/Low) or near a **Low Volume Node 
(LVN)** [8, 9]. If 455 contracts appear at an HVN, it signals the market is 
"collecting orders" in equilibrium rather than failing an auction [6].

### **3. The "Failed Auction" Signature**
A wall is only tradeable despite balance if it produces a **Failed Auction** 
signature:
*   **Wicks over Bodies:** Aggressive volume (Effort) must appear on the 
**wicks/shadows** of the candle, resulting in no price displacement (Result) 
[10, 11].
*   **Delta Discrepancy:** A trade is justified when you see a candle with 
**high positive delta but a negative close** (or vice versa), proving the 
"wall" of passive limit orders swallowed the aggression [12, 13].

### **4. Participation and Confidence**
The "Confidence" score (e.g., your "conf 18" skip) relates to Fabio's 
**Participation Baseline**:
*   **The 4k-5k Rule:** Fabio distrusts moves that lack institutional weight. 
He typically requires a minimum participation of **4,000–5,000 contracts per 
1-minute candle** on the NASDAQ to validate intent [14, 15].
*   **Low Confidence = No Steroids:** If the "Big Trades" are scattered or the 
total session volume is low, the setup lacks the "steroids" needed to trigger a
high-probability squeeze [16, 17].

**Summary:** While **300 contracts** is the "perfect" benchmark for a wall, it 
must occur at the **range periphery** (not an HVN) and result in a 
**wick/absorption signature** to override the "balance = no trade" rule [1, 11,
12].