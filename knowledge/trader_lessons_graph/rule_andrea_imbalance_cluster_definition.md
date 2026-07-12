# Imbalance Cluster Definition

**Trader**: Andrea
**Knowledge Node**: imbalance_cluster_definition

## Dettagli e Regole Operative
In the IBOB and broader order flow methodology, the following definitions and 
thresholds are used for diagonal imbalances:

### **1. The Imbalance Ratio**
The primary ratio that defines an imbalance cell in the footprint is **200% 
(2:1)** [1, 2]. 
*   **Initial Threshold (200%):** A number will change color (e.g., green for 
buy aggression, red/pink for sell aggression) if it is at least **two times 
larger** than its diagonal counterpart [2-4].
*   **Secondary Threshold (400%):** A more extreme imbalance is defined at 
**400% (4:1)** [3, 5]. On the Deep Charts platform, these cells are highlighted
with **higher color saturation** and "fattier" text to distinguish them as 
high-conviction institutional moves [3-5].

### **2. The Meaning of "Diagonal"**
"Diagonal" refers to the mechanical way aggressive market orders are matched 
against passive limit orders in the order book [1, 6]. 
*   **Mechanics:** In a double auction, a market order to buy is matched 
against a resting sell limit at the **ask** price, while a market order to sell
is matched against a resting buy limit at the **bid** price one tick below [1, 
6, 7]. 
*   **Comparison:** Therefore, an imbalance is not calculated horizontally (bid
vs. ask at the same price); it is calculated by comparing the **ask volume at 
one price level** to the **bid volume one tick lower** [2, 6, 7].

### **3. Imbalance Clusters**
While the "diagonal" rule describes how one cell is compared to another, the 
**"cluster"** requirement for IBOB confirmation refers to **consecutive price 
levels** [8, 9].
*   **Requirement:** For a breakout to be considered valid, you look for **two 
to three (or more) of these imbalances appearing in a row** at sequential ticks
within the same breakout candle [8-10].
*   **Significance:** A single imbalance might be noise, but a cluster of 2–3 
(or even 5 in strong moves) proves that one side has completely taken control 
of the auction and is "eating" through multiple levels of the order book with 
vengeance [8, 9, 11].