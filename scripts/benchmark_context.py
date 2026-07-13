import time
import os
import sys

from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.agents.llm_client import llm_ask

# Dummy system prompt
SYSTEM_PROMPT = "You are a trading bot analyzing footprint data. Return JSON with confidence 0-100."

# Generate 7 bars of footprint
bars_7 = "\n".join([f"Bar {i}: Open: 100, High: 105, Low: 95, Close: 102, Delta: {i*10}, Vol: 500" for i in range(7)])
# Generate 14 bars of footprint
bars_14 = "\n".join([f"Bar {i}: Open: 100, High: 105, Low: 95, Close: 102, Delta: {i*10}, Vol: 500" for i in range(14)])

def run_test(bars_text, label):
    user_msg = f"Analyze these footprint bars:\n{bars_text}\nReturn JSON."
    print(f"\n--- Testing {label} ---")
    print(f"Payload size: {len(user_msg)} characters")
    
    start = time.time()
    try:
        res = llm_ask(SYSTEM_PROMPT, user_msg)
        elapsed = time.time() - start
        print(f"Response received in {elapsed:.2f} seconds.")
        print(f"Response length: {len(res)} characters")
        return elapsed
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    print("Benchmarking Reflex Context (7 bars vs 14 bars) over OpenRouter API...")
    
    # Warmup
    run_test(bars_7, "Warmup (7 bars)")
    
    # Test 7 bars
    t7 = run_test(bars_7, "Reflex Stage (7 bars)")
    
    # Test 14 bars
    t14 = run_test(bars_14, "Deep Audit Stage (14 bars)")
    
    if t7 and t14:
        diff = t14 - t7
        pct = (diff / t7) * 100 if t7 > 0 else 0
        print(f"\n--- Results ---")
        print(f"Time saved by using 7 bars instead of 14: {abs(diff):.2f} seconds ({abs(pct):.1f}%)")
