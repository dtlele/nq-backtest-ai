# Setup Time Cutoff

**Trader**: Fabio
**Knowledge Node**: setup_time_cutoff

## Dettagli e Regole Operative
In Fabio Valentini’s model, while there isn't one universal "hard cutoff" 
second, there are clear statistical and structural thresholds where setups 
become significantly less reliable. He relies on Python-based data analysis to 
define these windows, noting that **trading at the wrong time can destroy a 
positive expectancy** [1, 2].

Based on the sources, here is the breakdown of his timing filters:

### **1. The 11:00 – 11:30 ET Transition (Initial Balance Phase)**
*   **The "One and Done" Threshold:** Fabio often views **11:30 AM ET** as a 
decision point. In live sessions, he has noted that once it approaches 11:30 AM
ET and the market is stuck in the middle of its range, the probability of a 
clean breakout or trend resumption decreases [3].
*   **Bank Lunch:** He identifies the mid-day period as a time when **"banks 
are at lunch,"** leading to a noticeable drop in institutional participation 
and volatility [4]. Trading in this "dead zone" often results in being "chopped
up" in a range-bound environment [5, 6].

### **2. The 1:00 PM ET (13:00) Statistical Cutoff**
*   **The Data-Driven Rule:** Through quantitative testing of his own metrics, 
Fabio concluded it is **not worth trading after 7:00 PM Italian time (which is 
1:00 PM ET)** [1]. 
*   **Win Rate Decay:** His data showed that his win rate dropped to 
approximately **20%** after this time. Consequently, he removes these hours 
from his operative plan to protect his equity curve [1].

### **3. The "Power Hour" Exception (1:30 PM – 3:00 PM ET)**
While he avoids the "lunch" lull, he identifies a specific afternoon window for
certain models:
*   **Structure:** He observes that if a session expands aggressively in the 
first hour and does not "Trump tweet" (experience a fresh fundamental shock), 
it will typically rebalance during the middle of the day [7].
*   **Execution Window:** Approximately **90% of his executions** for the "B 
model" (value area tests after expansion) occur between **7:30 PM and 9:00 PM 
Italian time (1:30 PM – 3:00 PM ET)** [8]. He calls this the **"Power Hour" 
expansion** [8, 9].

### **4. Last Valid Entry and Session Close**
*   **Simplified Model Limit:** In his "Simplified IVB Model," the focus is 
almost entirely on the **first three to four hours** of the New York session 
(9:30 AM – 1:30 PM ET) [10, 11].
*   **Absolute Stop:** He explicitly states that **4:00 PM ET (22:00 CET)** is 
"absolutely not operating hours" [12]. He does not hold positions overnight 
because of the increased margin requirements for futures and the lack of a 
day-trading edge in the electronic trading hours (ETH) [13, 14].

### **Summary of Timing Reliability**
| Time (ET) | Reliability | Market Context |
| :--- | :--- | :--- |
| **09:30 – 11:00** | **Highest (AAA)** | Opening battle; Peak institutional 
volume [15, 16]. |
| **11:00 – 11:30** | **Transition** | Decision point; checking for "one and 
done" [3]. |
| **11:30 – 13:30** | **Low** | "Banks at lunch"; range-bound chop/rebalancing 
[4, 7]. |
| **13:30 – 15:00** | **Medium/High** | "Power Hour"; trend 
resumption/re-accumulation [8]. |
| **After 15:00** | **Declining** | Closing auctions; high volatility but lower
edge consistency [17]. |

**Final Rule:** Fabio advises that if you have already hit your profit target 
for the day (e.g., a "Triple A" setup in the morning), you should **"sit like a
king"** on your profit and walk away rather than risking it in the 
lower-probability afternoon windows [18, 19].