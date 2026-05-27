import json
import os

padding_file = "C:/Users/Mauro/Documents/nq-backtest/knowledge/amt_glossary_padding.txt"

# Part 1: Keep the original 6 rules and glossary
original_glossary = """--- THEORETICAL AMT GLOSSARY & HISTORICAL SUGGESTIONS (FOR CONTEXT ONLY) ---

[NOTE FOR THE AI AGENT]
The following section contains general Auction Market Theory concepts and some historical observations from past trades.
Do NOT treat these as strict, unbreakable rules. They are provided strictly as background context and suggestions.
We are currently gathering statistical data (we need at least 100 trades before creating hard rules).
You are free to evaluate the market as you see fit.

1. MACRO TIMING SUGGESTIONS
It has been observed that during the 09:45 EST and 10:00 EST macroeconomic news windows, Market Makers often pull passive liquidity. This creates a "liquidity void". During these windows, heavy delta might be artificial (the result of stop runs rather than true institutional absorption). You may want to be more cautious during these times, but it is not a hard rule.

2. SURGICAL STOP PLACEMENT SUGGESTIONS
Historically, placing a stop loss directly above/below the absolute extreme of a wick has exposed trades to the "retail liquidity pool", making them vulnerable to stop hunts. A safer theoretical approach is to hide the stop loss in the "belly" of the P-shape or b-shape volume profile (e.g., just behind a thick cluster of Big Trades).

3. THE "SECOND DRIVE" CONCEPT
In pure Auction Market Theory, the first test of a key level (First Drive) often acts as a probe to find passive liquidity. The Second Drive (re-testing the level after a pullback) provides a higher-probability confirmation of a Failed Auction. You may use this as a structural guideline.

4. RESPONSE VS INITIATIVE (RNI PATTERN)
Absorption (e.g., heavy negative delta on a bullish candle) represents the "Response" phase (a passive wall). True breakouts usually require the "Initiative" phase, where the delta aggressively flips direction to sweep the book. Front-running the absorption without waiting for the initiative carries higher risk.

5. VOLUME PROFILE LEDGES
Institutional defense walls are theoretically found at Low Volume Nodes (LVN) or near the Point of Control (POC), because institutions prefer to defend positions at discounted prices rather than chasing extremes.

6. IBOB (Initial Balance Orderflow Breakout)
A genuine structural breakout of the Initial Balance usually requires the candle body to close completely outside the IB range. A wick piercing the IB boundary often indicates a sweep/absorption rather than true price acceptance.

[END OF SUGGESTIONS - USE AS CONTEXT ONLY]

"""

# Part 2: Extract real contextual knowledge to build padding weight
context = "\n\n--- EXTENDED SYSTEM CONTEXT AND ROADMAP ---\n"
try:
    with open("C:/Users/Mauro/Documents/nq-backtest/DASHBOARD_AND_ROADMAP.md", "r", encoding="utf-8") as f:
        context += "PROJECT ROADMAP:\n" + f.read() + "\n\n"
except Exception:
    pass

try:
    with open("C:/Users/Mauro/Documents/nq-backtest/agent_memory/loss_audit_results.json", "r", encoding="utf-8") as f:
        audit_data = json.load(f)
        context += "HISTORICAL AUDIT LOGS:\n" + json.dumps(audit_data, indent=2) + "\n\n"
except Exception:
    pass

# Combine everything
final_content = original_glossary + context

with open(padding_file, "w", encoding="utf-8") as f:
    f.write(final_content)

print(f"Padding pulito rigenerato. Nuova dimensione: {os.path.getsize(padding_file)} bytes")
