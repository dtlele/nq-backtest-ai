# Target Selection Hierarchy

**Trader**: Fabio
**Knowledge Node**: target_selection_hierarchy

## Dettagli e Regole Operative
Based on Fabio Valentini’s model, target selection is driven by **Auction 
Market Theory (AMT)** and statistical probability, focusing on where the market
is most likely to seek equilibrium or "Fair Value." He prioritizes "base 
hits"—high-probability exits—over chasing low-probability "home runs" [1-3].

### **Priority Order of Targets**
While specific to the day type, the general hierarchy of targets is as follows:
1.  **Developing POC (Current Session):** The "ultimate magnet" and primary 
point of interest for any trade returning to balance [4, 5].
2.  **IVB Protection Level (TP1):** The algorithmic target for breakouts, 
representing the highest probable excursion (65–70% probability) [6, 7].
3.  **Opposite Value Area Edge:** Used for "ping-pong" strategies when an 
auction fails at one extreme [8, 9].
4.  **Previous Day POC / High Volume Nodes (HVN):** Macro gravity points that 
act as secondary magnets if session levels are cleared [9, 10].

---

### **Specific Target Selection by Setup**

#### **(a) Mean Reversion Squeeze on a Balance Day**
*   **Target:** The **Developing POC** (Point of Control) of the current 
session [4, 11].
*   **Logic:** On balance days, the market is in a state of equilibrium. When 
price probes outside the Value Area and fails, it statistically gravitates back
to the level where the most volume has been transacted for that day (Fair 
Value) [4, 12].

#### **(b) IVB Breakout on a Trend Day**
*   **Target:** The **Protection Level (TP1)** [6, 7].
*   **Logic:** Once "acceptance" (a full-body candle close) occurs outside the 
15- or 30-minute IVB range, the algorithm plots a Protection Level. This is a 
proprietary calculation based on historical data showing the **highest probable
excursion** for that session [6, 13]. Fabio typically exits the entire position
here because the probability of the move continuing beyond this point drops 
significantly [12].

#### **(c) Failed Auction at IVB Edge**
*   **Target:** The **Developing POC** or the **Opposite IVB Edge** [14, 15].
*   **Logic:** A failed auction (wicks at the edge with high absorption) 
signals that the market is not ready to leave the current balance [11, 16]. The
price is expected to "ping-pong" back to the middle of the range (POC) or the 
opposite side of the established initial balance [14].

---

### **Nearest vs. Most Probable Target**
Fabio **always prioritizes the most probable target**, which frequently 
coincides with the nearest major high-volume level. 

*   **The 70% Rule:** He notes that the market returns to the POC/Fair Value 
with roughly 70% probability [12, 17]. He argues it is "not worth it" to hold 
for the remaining 30% extension if it means risking the profit already realized
[12, 18].
*   **Against Greed:** He emphasizes that professional traders "sit like a 
king" on their profit once a high-probability target is hit [19]. Chasing 
targets like 1:30 or 1:40 risk-to-reward ratios decreases the win rate to 
unsustainable levels (~10%), whereas targeting the 50% retracement or session 
POC maintains a consistent equity curve [20, 21].
*   **Trailing Stop Logic:** On highly directional days (e.g., "Trump tweet" 
days or high-volatility sessions), he may leave a small "runner" (e.g., 25% of 
the position) to target the **TP2** or a **macro-high/low**, but only after 
securing the bulk of the profit at the high-probability Protection Level [6, 
22, 23].