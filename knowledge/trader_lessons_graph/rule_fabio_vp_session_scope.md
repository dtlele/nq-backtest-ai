# Vp Session Scope

**Trader**: Fabio
**Knowledge Node**: vp_session_scope

## Dettagli e Regole Operative
Based on the provided sources, Fabio Valentini’s trade decisions are driven by 
**(d) a combination** of different Volume Profiles (VP). He utilizes a 
multi-layered approach that integrates long-term context, the previous day's 
structure, and the real-time development of the current session.

Here is the breakdown of which VP is used for each decision:

### **1. Determining Day Type (Balance/Trend)**
This decision is primarily a comparison between the **Previous NY Cash Session 
VP** and the **Developing VP of the Current Session**.
*   **The Comparison:** Fabio looks at whether the current price is building 
value within or outside the previous day’s Value Area (VA) [1]. 
*   **Balance Signal:** If the developing VP shows significant **overlap** with
the previous day’s VA, the day is classified as stationary or a "Balance Day" 
[1].
*   **Trend Signal:** A "Trend Day" is identified when the developing session 
achieves **acceptance** (building a new Value Area and Point of Control) 
completely outside the previous day's range [2, 3]. 

### **2. Finding Entry Levels (LVN, POC Proximity)**
Finding entries involves the **Previous NY Cash Session VP** for location and 
the **Developing VP** for timing and precision.
*   **Previous Session Levels:** He uses the **Value Area High (VAH) and Value 
Area Low (VAL)** of the previous session as major points of interest (POI) 
where he expects a reaction [4, 5].
*   **Low Volume Nodes (LVN):** Fabio identifies LVNs from previous 
distributions as "pivots" because they represent areas where price previously 
moved through effortlessly; he waits for price to return to these "virgin" 
areas to join a trend [6, 7].
*   **Developing IVB Edges:** In his simplified model, he uses the **Initial 
Volume Breakout (IVB)**—the VP of the first 15 to 30 minutes of the *current* 
session—to find the "sensitive area" between the developing Value Area edge and
its Point of Control (POC) for entries on a retracement [8, 9].

### **3. Setting Targets (VA Edge, POC)**
Setting targets relies heavily on the **Developing VP of the Current Session** 
and **Algorithmic Projections**.
*   **Developing Session POC:** On range-bound or mean-reverting days, Fabio 
explicitly states that the **POC of the current session** is the "ultimate 
magnet" and the best level to take your trade out [10, 11].
*   **The "Ping-Pong" Strategy:** If an auction fails at one edge of a Value 
Area (either previous or developing), he targets the **opposite edge** of that 
same Value Area, noting a 70% statistical probability of reaching it [12].
*   **Multi-Day Composite Targets:** For broader moves, he uses a **90-day 
composite VP** to identify the edges of long-term "Fair Value," treating the 
outer boundaries as ultimate targets or points where a move will likely exhaust
[13-15].
*   **Algorithmic Targets:** For trend breakouts, he uses the **IVB Model**, 
which plots a **"Protection Level" (TP1)**. This is a projected target based on
the statistical probability of a session's excursion following a valid breakout
[16].