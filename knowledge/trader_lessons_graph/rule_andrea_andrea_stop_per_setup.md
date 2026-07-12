# Andrea Stop Per Setup

**Trader**: Andrea
**Knowledge Node**: andrea_stop_per_setup

## Dettagli e Regole Operative
Based on the sources, the stop-loss placement in Andrea Cimi’s methodology 
varies depending on whether you are using a strictly mechanical model or a 
refined orderflow timing model. 

### **(a) IBOB Breakout Stop Placement**
For the standard Initial Balance Orderflow Breakout, there are three primary 
placement options:
*   **Point of Control (POC):** The most common mechanical rule is to place the
stop **below the POC** (for longs) or **above the POC** (for shorts) of the 
breakout candle or the 15-minute Initial Balance range [1-3].
*   **Imbalance Clusters:** For a more "refined" and tighter entry, the stop 
can be tucked directly **behind the imbalance cluster** (the 2–3 diagonal 
imbalances) that confirmed the initiative [4, 5].
*   **Range Extremes:** A conservative, "calm" approach involves placing the 
stop **below the Initial Balance low** (for longs) or **above the Initial 
Balance high** (for shorts) [6-8].

### **(b) Failed Auction / Squeeze Stop Placement**
In reversal or "Break-In" setups, the stop is defined by the failed attempt:
*   **Extreme of the Rejection:** The stop is placed **above the high of the 
wick** (for shorts) or **below the low of the wick** (for longs) where the "big
bubble" of absorption appeared [9, 10]. 
*   **Defensive Level:** If price re-enters the range with high volume, the 
stop is placed behind the candle that successfully "won the battle" and closed 
back inside the Value Area [11, 12].

### **(c) Gap Fill Stop Placement**
For the 70% probability gap fill strategy, the stop is typically more 
mechanical:
*   **Slightly Above/Below the Opening Range:** The stop is placed **slightly 
above the high** of the opening 5-minute range (for gap down fills) or 
**slightly below the low** (for gap up fills) [13, 14].
*   **Structural Barrier:** Some models suggest placing the stop behind the 
specific **high volume node** that rejected the initial opening attempt [15].

### **Buffer and Instrument Specifics (NQ)**
*   **Big Trade Clusters:** Yes, in the refined timing models, the stop is 
intentionally placed **behind the big trade cluster** or the imbalance cluster 
because that level represents institutional "protection." If those orders are 
breached, the trade's premise of initiative is invalidated [4, 11, 16].
*   **Tick Buffer:** The sources do **not provide a rigid numerical tick 
buffer** (e.g., "exactly 4 ticks"). Instead, Andrea uses qualitative terms like
**"slightly below"** [17], **"poco sotto"** [7], or **"generously above"** 
[18].
*   **Exact Numbers for NQ:** While NQ is discussed as a more volatile momentum
asset, the sources **do not list a specific fixed point or tick distance** 
(like 20 points) for NQ stops. Andrea emphasizes that his software's "quantity 
mode" calculates the number of contracts automatically based on the 
**structural level** (POC or extreme) rather than a fixed point amount [19, 
20].

**Summary Table of Stop Placement**
| Pattern | Primary Stop Location |
| :--- | :--- |
| **IBOB Breakout** | Behind the POC or the Imbalance Cluster [1, 4] |
| **Failed Auction** | Above/Below the rejection wick (the absorption bubble) 
[10] |
| **Gap Fill** | Slightly beyond the opening range extreme [13] |
| **Conservative** | Behind the entire 15-minute Initial Balance range [7] |