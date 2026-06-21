# Failed Auction Variants

**Trader**: Andrea
**Knowledge Node**: failed_auction_variants

## Dettagli e Regole Operative
Andrea Cimi’s system categorizes failed auctions as **statistical anomalies** 
where the market attempts to find new value but fails to attract participation,
leading to a reversion to the previous area of balance [1-3]. While the 
fundamental trigger—a **candle closing back inside the range**—remains 
consistent, the context and specific rules vary depending on where the failure 
occurs [2, 4, 5].

### **1. Types of Failed Auctions by Location**

*   **Value Area (VA) Edges:** This is the most common type, occurring when 
price moves outside the 70% first standard deviation (fair value) [2, 6]. Cimi 
views these as "cheap" or "premium" prices where smart money is likely to push 
the auction back toward the mean [2, 7]. 
*   **Prior Session/Daily Highs and Lows:** These are often referred to as 
**"stop runs"** or "liquidity sweeps" [3, 8]. Cimi identifies these by looking 
for a poke beyond the high/low that fails to build a new high-volume node, 
suggesting it was merely a search for liquidity rather than a true trend 
initiative [9-11].
*   **Opening Range (IB):** A failed auction occurs if the price breaks out of 
the 5-minute or 15-minute opening range but immediately **closes back inside** 
[12-14]. This indicates the market is not ready for "discovery" and prefers to 
auction within the previous session's liquidity [13].
*   **Ledges (HVN to LVN Transitions):** Cimi looks for failed auctions at 
"ledges," which are the points where a high-volume node (balance) drops off 
into a low-volume node (imbalance) [15, 16]. If price fails to traverse the 
low-volume void and returns to the HVN, it is traded as a failure [16].

### **2. Differences in Rules and Criteria**

The rules for identifying and trading these failures differ based on the 
following orderflow dynamics:

*   **Participation vs. Absorption:**
    *   **At VA Edges:** Cimi looks for **exhaustion**, where volume and delta 
dry up as price moves outside the range, followed by increasing volume as it 
re-enters [2, 10].
    *   **At Session Highs/Lows:** He prioritizes **absorption**, often 
identified by **Iceberg orders** (large hidden orders) or a high delta (>25%) 
that results in no price progress [10, 17, 18].
*   **Win Rate and Trend Context:**
    *   Failed auctions that occur **with the macro trend** (e.g., a B-shape 
failure at the bottom of a bearish trend that reverts to the center) have a 
statistically higher win rate [6, 19].
    *   Failed auctions that **reverse the trend** (e.g., price breaking above 
a P-shape range and failing) are considered riskier and require a more 
conservative "wait for acceptance" approach [20, 21].
*   **Targeting Logic:**
    *   **Standard Target:** The **Point of Control (POC)** or the nearest 
high-volume node is the conservative target for any failed auction [2, 22].
    *   **Aggressive Target:** For a high-conviction failed auction at a VA 
edge, the target is the **opposite side of the distribution** [2, 23].
    *   **Impulse Target:** In the "P reversal model," if a failed auction 
breaks the entire consolidation, the target is the **beginning of the initial 
impulse** [4, 24].

### **3. The "Break-In" Entry Trigger**
Regardless of location, the precise entry is the **"Break-In"**: the market 
must not only poke outside the level but must **close back inside** the 
previous range [2, 7]. Cimi emphasizes that without a clear range forming 
outside the level (acceptance), any breakout is a potential failure [25]. He 
often waits for a **retest** of the range edge or a specific **imbalance 
cluster** to time the entry with a tight stop-loss placed one tick beyond the 
failure point [26-28].