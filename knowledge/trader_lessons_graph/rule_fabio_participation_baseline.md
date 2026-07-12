# Participation Baseline

**Trader**: Fabio
**Knowledge Node**: participation_baseline

## Dettagli e Regole Operative
In Fabio Valentini's model, the participation baseline of **4,000-5,000 contracts** on the NASDAQ (NQ) refers specifically to the **volume of the individual candidate bar** (measured candle by candle) performing a breakout or test, rather than the average session volume [1, 2].

### **1. Candidate Bar vs. Average Volume**
While the threshold is applied to the **specific candle** attempting a move, it is used contextually in two ways:
*   **Candle-by-Candle Validation:** Fabio monitors the volume of the current bar to ensure institutional "market makers" are actually providing liquidity for the move [1, 3]. If a move happens with low volume, he classifies it as a "lack of participation" or "noise" rather than true institutional intent [3, 4].
*   **The "Soft Threshold" for Failed Auctions:** As established in our 2026 methodology refinement, for **Mean Reversion / Failed Auction** setups at structural extremes (VAH, VAL, IB Ext), a lower threshold of **3,500+ contracts** can be accepted if Footprint shows extreme absorption (Big Trade walls) [Methodology Refinement 2026].
*   **The 10k M5 Rule:** For approving a Failed Auction, Fabio also uses a 5-minute threshold of **10,000 contracts** (avg 2,000/min), which is valid ONLY for reversals from extremes where trapped traders are clearly visible [Methodology Refinement 2026].

### **2. Measuring on M5 (5-Minute) Bars**
In practice, the 1-minute baseline of 4,000-5,000 contracts must be **scaled proportionally** when looking at higher timeframes:
*   **The M5 Threshold:** For trend following, a volume of **18,000 contracts on an M5 bar is "not much"** because it averages out to only 3,600 contracts per minute [4]. 
*   **The "Steroid" Level for M5:** To justify a high-confidence entry (an "AAA" setup) on an M5 chart, the bar should ideally show a total volume exceeding **20,000-25,000 contracts** [4]. 

**Summary Table for NQ Participation**
| Timeframe | Mode | Threshold |
| :--- | :--- | :--- |
| **M1 (1-Min)** | Trend/Breakout | **4,000-5,000+ contracts** |
| **M1 (1-Min)** | Failed Auction | **3,500+ contracts** (Soft Threshold) |
| **M5 (5-Min)** | Trend/Breakout | **20,000-25,000+ contracts** |
| **M5 (5-Min)** | Failed Auction | **10,000+ contracts** (Conditional) |