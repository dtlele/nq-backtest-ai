# Institutional Activity

**Trader**: Andrea
**Knowledge Node**: institutional_activity

## Dettagli e Regole Operative
Andrea identifies institutional activity (Smart Money) by looking for the 
"anatomy and physiology" of price movements through Market By Order (MBO) data,
which allows him to distinguish between one large institutional order and many 
small retail orders [1-3]. He characterizes retail activity as "noise" because 
it accounts for only about 5% of total daily volume, whereas the remaining 95% 
is driven by a small number of large participants like banks, hedge funds, and 
pension funds [4, 5].

### **Institutional Contract Sizes and Filters**
To isolate "Smart Money" from retail noise, Andrea uses specific volume and 
contract size filters:
*   **NQ (Nasdaq) Filter:** While Andrea primarily trades the ES, he mentions 
that institutional signatures on the NQ are often isolated by focusing on "big 
trades" rather than standard footprints [6]. (Note: Although specific NQ filter
sizes were discussed in previous conversation turns, the current sources 
emphasize that the threshold must be adjusted for volatility [7]).
*   **ES (S&P 500) Filter:** Andrea uses an iceberg and big trade indicator set
to a minimum cluster of **300 to 400 contracts** [7]. However, he notes that 
during the high-volume New York cash session, 300 contracts is "not close to be
enough" and the threshold must be increased to accurately capture institutional
participation [7].
*   **Large-Scale Activity:** Institutional orders can be massive; Andrea 
specifically cites **2,000-contract icebergs** as a common signature of a "big 
market participant" manipulating the book to hide their true size [8-10].

### **Institutional Orderflow Patterns**
Andrea identifies smart money through three primary "footprint" signatures:
*   **Icebergs (Absorption):** A big participant hides a large order by showing
only a small "tip" (e.g., 20 contracts) in the book [8, 10]. As market orders 
consume the tip, it is **constantly reloaded** in milliseconds [11]. This 
appears as "silence" or "stillness" in price while huge volume is being 
executed at a single level [11, 12].
*   **Effort with No Result:** This occurs when a footprint shows a **huge 
Delta (often >25%)** and massive volume on a candle wick, but price fails to 
break the level [12, 13]. This indicates an institution is passively absorbing 
all aggressive pressure [12].
*   **Book Sweeping (Stop Runs):** Institutions occasionally "sweep" the entire
order book, creating vertical price sprints [14, 15]. This is identified in the
footprint by **"zeros"** on one side of the candle (indicating price moved too 
fast for the auction to match) and an extreme **Delta above 50%** [16, 17].

### **Institutional Time of Day**
The "real fun begins" during the periods of highest institutional liquidity 
[18]:
*   **New York Opening Auction (09:30 EST):** This is the most significant 
window where institutions pour in orders that could not be filled during the 
overnight session [19]. Andrea typically waits for the first **15 minutes** for
the "initial balance" to form before identifying the institutional path [20, 
21].
*   **Closing Auction (15:50 – 16:00 EST):** Andrea reveals that the **last 10 
minutes of the session** are when the most volume is actually traded [22, 23]. 
This is when day-trading algorithms, hedge funds, and ETFs rebalance their 
massive positions, creating a "feast" for market makers [22, 23].
*   **News Avoidance:** Conversely, institutions (specifically market makers) 
often **withdraw liquidity** immediately before and after news like NFP or CPI,
leading to "toxic flow" and empty books [24, 25]. Andrea considers these 
"noisy" periods untradeable [25, 26].