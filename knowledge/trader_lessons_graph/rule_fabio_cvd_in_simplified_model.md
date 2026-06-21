# Cvd In Simplified Model

**Trader**: Fabio
**Knowledge Node**: cvd_in_simplified_model

## Dettagli e Regole Operative
In Fabio Valentini’s methodology, the **Simplified Model** is designed to avoid
the "information overload" that often paralyzes beginners when looking at 
multiple order flow data points [1, 2]. While CVD is a powerful component of 
his personal "alpha," it is treated differently depending on the complexity of 
the setup.

### **CVD: Simplified vs. Advanced**
The **Simplified Model** (specifically the IVB Model 1 and Model 2) does 
**not** strictly require CVD [3-6]. Instead, it focuses on the **Initial Volume
Breakout (IVB)**, **Volume Profile framing**, and the **"Big Trades" 
(bubbles)** indicator [6, 7]. 

*   **Simplified Application:** Beginners are encouraged to ignore CVD and 
focus on the **Location** (Value Area edges/LVNs) and the **Trigger** (Big 
Trade bubbles in the candle body or on wicks) [1, 8].
*   **Advanced Application:** CVD is used as an **"anticipatory indicator"** in
the advanced version of the model to identify "steroids" or building pressure 
before price moves [9, 10]. It provides the "aha moment" for identifying 
trapped participants with more depth [11].

### **The Role of CVD in Mean Reversion**
In the **Mean Reversion (Inversion) Model**, CVD divergence acts as a 
high-confidence confirmation. It identifies a "discrepancy" where aggressive 
participants are pushing (effort) but the price is struggling to break a level 
(lack of result) [12, 13].

### **What Replaces CVD Divergence in a Mechanical Backtest?**
If you are building a mechanical backtest without CVD, the primary replacement 
for "absorption confirmation" is the **Law of Effort vs. Result** manifested 
through price action and **Big Trade clusters** [14, 15]:

1.  **Big Trade Placement (The "Wall"):** Instead of looking for a CVD line 
moving against price, look for **Big Trade bubbles (filtered for 30+ contracts 
on NQ)** appearing specifically on the **candle wicks/shadows** at a sensitive 
level (IVB High/Low or VAH/VAL) [14, 16, 17].
2.  **Numerical Threshold:** A "Wall" is mechanically defined by a mega-cluster
of these bubbles striking a single horizontal tick. A total of **300+ 
contracts** with zero price progress is cited as the "perfect example" of 
absorption [17, 18].
3.  **Delta Per Candle (Effort vs. Result):** While CVD is cumulative, you can 
use the **Delta of the individual candidate candle**. A valid absorption setup 
is a candle with a **high positive delta but a negative (red) closure** (for a 
short/squeeze) or a high negative delta but a positive (green) closure [15, 
19].
4.  **Failed Auction Signature:** Mechanically, the setup is confirmed when 
price probes above a range edge but fails to produce a **full-body candle 
close** outside that range, accompanied by high-volume wicks [20, 21].

**Summary:** In the simplified model, you replace the "leading" information of 
the CVD line with the **immediate "fact" of the Big Trade bubbles** hitting a 
wall on the wicks [22-24]. This ensures you are following the "smart money" 
participation without needing to interpret the complexities of a cumulative 
delta chart [25, 26].