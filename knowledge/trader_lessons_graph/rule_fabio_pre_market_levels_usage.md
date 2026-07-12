# Pre Market Levels Usage

**Trader**: Fabio
**Knowledge Node**: pre_market_levels_usage

## Dettagli e Regole Operative
Based on the sources, Fabio Valentini defines and utilizes the pre-market range
with specific mechanical rules that prioritize institutional context over 
standalone execution.

### **Definition of the Pre-Market Range**
The pre-market range is generally defined as the **Extended Trading Hours 
(ETH)**, which encompasses the price action occurring during the Asian and 
London sessions before the **09:30 AM EST New York cash open** [1, 2].
*   **The Window:** While he acknowledges specific sub-ranges like the "Asian 
range" (characterized as a low-probability "gray box"), he focuses on the total
excursion (high and low) created during the overnight hours to identify where 
liquidity has been "engineered" before the New York battle begins [3, 4].
*   **Separation of Data:** He explicitly keeps ETH data visible as a reference
for these structural levels but **excludes it from his session Volume Profile**
computation, which uses only the 09:30–16:00 EST data to ensure he is analyzing
the "peak of interest" [1, 5].

### **Contextual Usage vs. Standalone Entry**
Valentini does **not** use pre-market highs or lows as standalone entry levels.
Instead, they serve as **essential context** for triggers that occur once the 
cash session is active:

*   **Liquidity Sweeps and Failed Auctions:** Pre-market levels are used to 
identify "Look Above and Fail" (or below) scenarios. A high-probability setup 
occurs when the market breaks a **pre-market low/high** immediately at or after
the 09:30 open but fails to achieve **acceptance** (a full-body candle close), 
snapping back into the range [6, 7]. 
*   **Validation for IVB Setups:** These levels provide the "narrative" for the
Initial Volume Breakout (IVB). For example, if price breaks below a pre-market 
low with "massive aggression" but then reclaims that range, it validates a 
**Mean Reversion/Squeeze** trade targeting the session POC or the opposite 
pre-market extreme [6, 8].
*   **Profit Targets:** Pre-market highs and lows are frequently used as 
**primary algorithmic targets**. In one live trade example, Valentini entered a
long at 6390 and set his target at 6405 specifically because it was the 
established **pre-market high** [9].
*   **Avoidance Rule:** He explicitly states, **"Usually I don't trade 
pre-market open"** because he wants to wait for the New York session to provide
a clear institutional bias and the volume "steroids" necessary to confirm a 
move [10, 11].

### **Concrete Summary of the Logic**
| Level | Role in Model |
| :--- | :--- |
| **Pre-Market High/Low** | **Location Context:** Defines the "dealing range" 
and identifies where liquidity is resting [12, 13]. |
| **Failed Auction at Level** | **The Trigger:** Price pierces the pre-market 
level at the open but produces a wick/shadow and snap-back [6, 12]. |
| **Order Flow at Level** | **Validation:** Requires 30+ contract bubbles (NQ) 
on the wicks to prove absorption at that pre-market boundary [14]. |

In summary, the pre-market range is the structural "map," but the **Initial 
Volume Breakout (IVB)** and the order flow within the first 15–30 minutes of 
New York are the "triggers" that justify the risk [15, 16].