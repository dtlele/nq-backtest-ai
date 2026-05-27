import json

# Update andrea_knowledge.json
with open(r'c:\Users\Mauro\Documents\nq-backtest\knowledge\andrea_knowledge.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 1. Update pbd_shapes
pbd_shapes = data['knowledge_by_topic']['pbd_shapes']
target_pbd = '\"price discovery\" that was rejected [24, 25].'
replacement_pbd = '\"price discovery\" that was rejected [24, 25].\\n*   **The Imbalance Defense Failure**: If a cluster of institutional \"Big Trades\" (30+ contracts) is defended, price must bounce within 2-3 ticks. If a strong candle slices through the cluster and **closes beyond it**, the institutional defense has officially failed [Inquiry 2026].'
data['knowledge_by_topic']['pbd_shapes'] = pbd_shapes.replace(target_pbd, replacement_pbd)

# 2. Update trade_management
trade_mgmt = data['knowledge_by_topic']['trade_management']
target_mgmt = 'close and then on a test of an imbalance cluster) [5, 6]. This allows him to'
replacement_mgmt = 'close and then on a test of an imbalance cluster) [5, 6]. This allows him to\\n*   **Trailing Strategy (Strangle Price)**: On high-momentum trend days, once the 2:1 R/R target is reached, the remaining runner (25-50%) is trailed behind the most recent **M1 absorption bubbles**. If a new cluster forms and is defended, the stop is moved tightly behind it (strangling the price) [Inquiry 2026].\\n*   **Final Target (The VWAP/Ledge)**: The ultimate exit for trend-day runners is either a major structural **ledge** on the composite profile or a **re-touch of the VWAP**, where institutional liquidity typically resets [Inquiry 2026].\\n*   **Scaling Out (Early Profits)**: He does not always wait for a final macro'
data['knowledge_by_topic']['trade_management'] = trade_mgmt.replace(target_mgmt, replacement_mgmt)

# Write back
with open(r'c:\Users\Mauro\Documents\nq-backtest\knowledge\andrea_knowledge.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Updated andrea_knowledge.json successfully")
