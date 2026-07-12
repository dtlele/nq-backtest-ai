# Confirmation Timeframe

**Trader**: Andrea
**Knowledge Node**: confirmation_timeframe

## Dettagli e Regole Operative
Based on the sources, the time frame used for the **IBOB trigger** depends on 
the specific Initial Balance (IB) window you are using for that setup. There is
a consistent relationship between the size of the range and the candle used for
the breakout close.

### **The Timeframe Rule**
Andrea Cimi explains a specific hierarchy for defining the breakout trigger:
*   **For a 15-minute Initial Balance (Standard):** You require a **5-minute 
candle** to close outside the range [1, 2].
*   **For a 5-minute Initial Balance (Aggressive/Gap Fill):** You require a 
**1-minute candle** to close outside the range [1, 3].

### **1-Minute vs. 5-Minute Confirmation**
While the mechanical breakout trigger is defined by the close of a candle 
(either 5-min or 1-min), the **refined IBOB model** frequently uses the 
1-minute chart for specific orderflow confirmations:

1.  **Bias vs. Entry:** Andrea typically keeps a 5-minute chart open to 
identify the overall **"bias"** and structural levels, while simultaneously 
using a 1-minute chart to time the **"entry"** pattern [4, 5].
2.  **Orderflow Timing Model:** To secure a tighter stop and higher 
risk-to-reward ratio (e.g., 1:2 or 1:3), you drop to the 1-minute chart to look
for an **imbalance cluster** (at least 2–3 diagonal imbalances) occurring in 
the breakout candle [6, 7].
3.  **The "Invitation":** The 1-minute chart allows you to see the 
"nitty-gritty" of who is dominating the auction in real-time, proving that the 
breakout is being supported by institutional initiative rather than being a 
"mere poke" [6, 8, 9].

### **Summary of the Trigger**
The IBOB trigger is effectively a **two-step process** in live sessions:
*   **The mechanical trigger** is the **5-minute candle close** (for the 
standard 15-min IB) [2, 10].
*   **The execution confirmation** is often done on the **1-minute chart** to 
identify the specific imbalance clusters and "big trade" bubbles that tell you 
the "party" is actually moving in your direction [6, 11].

As Andrea notes, if you are looking for the most mechanical approach, you 
simply enter at the candle close. However, for a professional "timing" model, 
you look at the **1-minute footprint** to confirm that aggressive buyers or 
sellers have successfully taken control of the auction [6, 12].