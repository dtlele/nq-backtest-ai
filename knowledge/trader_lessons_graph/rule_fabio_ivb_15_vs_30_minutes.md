# Ivb 15 Vs 30 Minutes

**Trader**: Fabio
**Knowledge Node**: ivb_15_vs_30_minutes

## Dettagli e Regole Operative
In recent live sessions and videos, Fabio Valentini defines the **Initial 
Volume Breakout (IVB)** range as variable, typically spanning the first **15 to
30 minutes** of the New York session, though it can extend up to **60 minutes**
depending on the trader's objectives [1-3].

### **15 vs. 30 Minute Definition**
Fabio uses different timeframes for the IVB based on the intended trading 
style:
*   **15 Minutes:** Often used for **scalping** or more aggressive entries [1, 
4]. In some live sessions, he explicitly monitors the "range di apertura a 15 
minuti" composed of three 5-minute candles [5, 6].
*   **30 Minutes:** This is frequently highlighted in his "Simplest Orderflow 
Trading Model" walkthroughs. He notes that the market’s direction for the day 
often becomes clear **15 to 30 minutes** after the open [7]. In backtesting 
demonstrations, he often waits for the **full 30 minutes** to complete before 
the IVB range is "cleanly defined" and the algorithm plots the high-probability
targets [8-10].

### **Is the Duration Variable?**
Yes, the duration is variable and depends on how the opening auction unfolds:
*   **Unfolding Interaction:** Fabio explains that the IVB range is a **dynamic
level** that continues to expand and update until the chosen time limit (15, 
30, or 60 minutes) is reached [9-11].
*   **Resolution of the Battle:** He waits for the first 30 minutes to provide 
"stability" because the opening is characterized by a "big battle" between 
aggressive participants [1, 12, 13]. The IVB is essentially the footprint of 
who won that initial battle [14, 15].
*   **Style Choice:** He explicitly states that the choice between 15, 30, or 
60 minutes **"depends how you want to use it,"** whether for quick scalps or 
establishing a broader intraday bias [1, 16].

### **Changes Over Time**
While the foundational logic of the Opening Range Breakout (ORB) dates back to 
the 1990s, Fabio’s modern refinement involves putting these standard timeframes
**"on steroids"** by pairing them with order flow [2, 4]. Rather than just a 
fixed time-based breakout, he now emphasizes waiting for **acceptance** (a 
full-body candle close) outside the 15- or 30-minute range and a **"Second 
Drive"** (retracement and resumption) before committing to a trade [17, 18].