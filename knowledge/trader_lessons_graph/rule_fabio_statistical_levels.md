# Statistical Levels

**Trader**: Fabio
**Knowledge Node**: statistical_levels

## Dettagli e Regole Operative
Fabio Valentini’s statistical algorithm is a proprietary model developed with 
the Deep Charts team, designed to identify high-probability price targets based
on **Auction Market Theory** and **Initial Balance Breakouts (IVB)** [1, 2].

### **The 'Protection Levels' (TP1)**
The "protection level" is a specific price target, also referred to as **TP1**,
that the algorithm automatically plots on the chart once the market breaks out 
of its initial range (typically the first 30 or 60 minutes of the New York 
session) [3, 4].
*   **Definition:** It represents the **"highest probable excursion"** for a 
single trading session following a confirmed breakout [1, 4].
*   **Purpose:** It allows Fabio to remove discretionary guesswork regarding 
where to take profits. Once a breakout is confirmed, the algorithm provides an 
objective "location" for the first target [3].
*   **Extended Average (TP2):** The algorithm also plots a secondary target 
called the "maximum extreme average," which offers a higher reward but carries 
a lower statistical probability of being reached compared to the protection 
level [3, 5].

### **Assigned Probabilities**
Fabio uses specific quantitative benchmarks to define the reliability of his 
targets:
*   **Protection Level (TP1):** Fabio assigns a **65% to 70% statistical 
probability** that the market will reach this level once the IVB range is 
broken [3, 4].
*   **Value Area Edges:** Based on the laws of a normal Gaussian distribution, 
**70% of the session's volume** is traded within the Value Area (defined by the
Value Area High and Low) [6-8]. 
*   **Reversion Probability:** If the market attempts to break out of value but
fails (an "auction failure"), there is a high probability—often cited as 
**70%**—that the price will gravitate back through the mean and reach the 
**opposite edge** of the Value Area [7, 9, 10].

### **How the Algorithm is Calculated**
The algorithm is not based on traditional technical indicators like moving 
averages but on **data-driven quantitative research** [2, 3].
*   **Historical Sample Size:** The model was built by analyzing "years and 
years of data" to find repetitive volatility patterns in the NASDAQ and S&P 500
[2, 3].
*   **Technologies Used:** The calculations utilize **neural networks and 
machine learning** to determine the most frequent price extensions relative to 
the opening range [2, 3].
*   **Variables Analyzed:** It factors in the relationship between **initial 
balance width, session volume, and standard deviation** to project where 
participants are most likely to find a new point of equilibrium (fair value) 
[3, 8, 11].
*   **Market Context:** The algorithm distinguishes between "consolidation 
sessions" and "directional sessions," adjusting the projected targets based on 
current market behavior [12].