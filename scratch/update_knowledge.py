import json

file_path = 'knowledge/fabio_knowledge.json'

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Update participation_baseline
data['knowledge_by_topic']['participation_baseline'] = """
In Fabio Valentini's model, the participation baseline of **4,000-5,000 contracts** on the NASDAQ (NQ) refers specifically to the **volume of the individual candidate bar** (measured candle by candle) performing a breakout or test, rather than the average session volume [1, 2].

### **1. Candidate Bar vs. Average Volume**
While the threshold is applied to the **specific candle** attempting a move, it is used contextually in two ways:
*   **Candle-by-Candle Validation:** Fabio monitors the volume of the current bar to ensure institutional \"market makers\" are actually providing liquidity for the move [1, 3]. If a move happens with low volume, he classifies it as a \"lack of participation\" or \"noise\" rather than true institutional intent [3, 4].
*   **The \"Soft Threshold\" for Failed Auctions:** As established in our 2026 methodology refinement, for **Mean Reversion / Failed Auction** setups at structural extremes (VAH, VAL, IB Ext), a lower threshold of **3,500+ contracts** can be accepted if Footprint shows extreme absorption (Big Trade walls) [Methodology Refinement 2026].
*   **The 10k M5 Rule:** For approving a Failed Auction, Fabio also uses a 5-minute threshold of **10,000 contracts** (avg 2,000/min), which is valid ONLY for reversals from extremes where trapped traders are clearly visible [Methodology Refinement 2026].

### **2. Measuring on M5 (5-Minute) Bars**
In practice, the 1-minute baseline of 4,000-5,000 contracts must be **scaled proportionally** when looking at higher timeframes:
*   **The M5 Threshold:** For trend following, a volume of **18,000 contracts on an M5 bar is \"not much\"** because it averages out to only 3,600 contracts per minute [4]. 
*   **The \"Steroid\" Level for M5:** To justify a high-confidence entry (an \"AAA\" setup) on an M5 chart, the bar should ideally show a total volume exceeding **20,000-25,000 contracts** [4]. 

**Summary Table for NQ Participation**
| Timeframe | Mode | Threshold |
| :--- | :--- | :--- |
| **M1 (1-Min)** | Trend/Breakout | **4,000-5,000+ contracts** |
| **M1 (1-Min)** | Failed Auction | **3,500+ contracts** (Soft Threshold) |
| **M5 (5-Min)** | Trend/Breakout | **20,000-25,000+ contracts** |
| **M5 (5-Min)** | Failed Auction | **10,000+ contracts** (Conditional) |
""".strip()

# Update stop_placement
data['knowledge_by_topic']['stop_placement'] = """
Fabio Valentini places his stop loss with mathematical precision based on the institutional activity he identifies through the order flow. He treats institutional \"Big Trades\" as a literal wall of protection for his capital [1, 2].

### Where Exactly the Stop is Placed
*   **Behind the Institutional Wall:** Fabio places his stop loss directly **behind the cluster of \"Big Trades\"** (orders filtered by 30 contracts on NASDAQ) that initiated or defended the current move [1, 2]. 
*   **The \"Anti-Sweep\" Logic:** To minimize slippage in highly volatile environments, a specific tactic is placing the stop loss **one or two ticks before** a significant extreme (like a high or low) [Methodology Refinement 2026].
*   **Why 1-2 Ticks Before?** Because the market often accelerates violently once the actual extreme level is hit due to a cascade of triggered stop orders (liquidity sweep). Exiting just before this acceleration saves significant slippage [Methodology Refinement 2026].

### Dynamic Management
1.  **The \"Winner\" Level:** He places the stop behind the specific wall of orders that **\"won the battle\"** [10].
2.  **Fast Break-Even:** Fabio is famous for moving to **break-even** almost immediately (within 20-30 seconds) as soon as momentum is confirmed by CVD and a \"laser-like\" price move [7, 8].
3.  **The \"Must Have Reason\" Rule:** \"You must have reason or be out.\" If the specific institutional wall he hid behind is breached, the reason for the trade is gone, and he exits immediately regardless of price [2].
""".strip()

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Updated knowledge/fabio_knowledge.json successfully.")
