# Ivb Breakout Vs False Balance May01

**Trader**: Fabio
**Knowledge Node**: ivb_breakout_vs_false_balance_may01

## Dettagli e Regole Operative
On a **balance day**, Fabio Valentini’s model treats the Initial Volume 
Breakout (IVB) edge as a critical decision point where the market either 
transitions into **price discovery** or undergoes an **auction failure**. The 
maximum confidence of **65** for the trade taken on May 1st indicates that the 
setup reached his minimum threshold for execution by meeting specific 
mechanical and order flow filters [1, 2].

### **1. Valid IVB Breakout vs. False Attempt**
The primary filter for a valid breakout on a balance day is **acceptance** 
outside the range established in the first 15–30 minutes of the New York 
session [3, 4].

*   **The Acceptance Rule (Body vs. Wick):** A valid breakout requires a 
**full-body candle close** decisively outside the IVB High or Low [5]. If the 
price pierces the level but produces a **wick (shadow)** and returns inside the
range, it is classified as a **failed auction** or "look above and fail" [6, 
7].
*   **The "Second Drive" Protocol:** Valentini explicitly warns, **"Don't take 
the first drive"** [8]. A high-confidence breakout (65+) typically requires:
    1.  A breakout and acceptance (full-body close).
    2.  A retracement to test the broken edge or a nearby **Low Volume Node 
(LVN)**.
    3.  A **"second drive"** that resumes the original direction with renewed 
aggression [9, 10].
*   **The Participation Baseline:** A breakout lacks "steroids" and is likely 
false if volume is below **4,000–5,000 contracts per 1-minute candle** on the 
NASDAQ [11]. Low volume at the edge indicates a "liquidity gap" rather than 
institutional intent [12].

### **2. Order Flow Requirements at the IVB Edge**
The order flow must confirm whether participants are **initiating** a move or 
being **absorbed** at the boundary [13, 14].

*   **For a Valid Breakout (Initiative):** "Big Trade" bubbles (filtered for 
**30+ contracts**) must populate the **body** of the breakout candle [15]. This
proves that aggressive participants are successfully finding a counterparty and
accepting new, higher/lower prices [16].
*   **For a False Breakout (Absorption/Squeeze):**
    *   **The Wall:** Clusters of big trades (ideally totaling **300+ 
contracts** at a single tick) must appear on the **wicks** [17]. This signals 
aggressive traders "punching a wall" of passive limit orders and getting 
swallowed [18, 19].
    *   **Effort vs. Result:** The model looks for a mathematical 
discrepancy—high volume effort with zero price result [19]. For a failed 
breakout at the high, a candle with **high positive delta but a negative 
close** is a prime signal to fade the move [13].
    *   **CVD Alignment:** In a valid breakout, the **Cumulative Volume Delta 
(CVD)** should be "pushing on the gas" and making new highs alongside price 
[20]. A divergence (CVD making a high while price fails) confirms a false 
breakout [21].

### **3. Context of the May 1st Trade**
With an IB of 102 points and a max confidence of 65, the trade taken likely 
occurred at the **periphery** (IB High/Low) rather than at the POC or HVN, as 
Valentini identifies the middle of a balance day as a **"zone of chop"** with 
no edge [22]. The confidence score of 65 suggests that at least one of his 
**AAA triggers** was present: either a successful **Second Drive** following an
IVB breakout or a massive **Absorption Wall** at the range edge that triggered 
a **Squeeze** back toward the session POC [16, 23, 24].