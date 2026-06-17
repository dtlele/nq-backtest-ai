import os
from pathlib import Path

# Prices per 1,000,000 tokens
PRICES = {
    "deepseek/deepseek-chat": {"input": 0.2002, "output": 0.8001},
    "anthropic/claude-sonnet-4.5": {"input": 3.00, "output": 15.00},
    "openai/gpt-4o": {"input": 2.50, "output": 10.00},
    # Alternatives for comparison
    "anthropic/claude-haiku-4.5": {"input": 1.00, "output": 5.00},
    "anthropic/claude-3.5-haiku": {"input": 0.80, "output": 4.00},
}

def get_cost(model, in_tokens, out_tokens):
    if model not in PRICES:
        return 0.0
    in_cost = (in_tokens / 1_000_000.0) * PRICES[model]["input"]
    out_cost = (out_tokens / 1_000_000.0) * PRICES[model]["output"]
    return in_cost + out_cost

def main():
    log_path = Path(r"C:\Users\Mauro\Documents\nq-backtest\agent_memory\token_usage.log")
    if not log_path.exists():
        print("Log file not found.")
        return

    with open(log_path, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    # We want to group the logs.
    # The logs are sequential. Let's print out the raw costs first.
    print("=== RAW CALL BREAKDOWN ===")
    total_cost = 0.0
    for idx, line in enumerate(lines, 1):
        parts = line.split(",")
        if len(parts) != 4:
            continue
        _, model, in_tok, out_tok = parts
        in_tok, out_tok = int(in_tok), int(out_tok)
        cost = get_cost(model, in_tok, out_tok)
        total_cost += cost
        print(f"Call {idx:02d} | {model:<30} | In: {in_tok:<5} | Out: {out_tok:<4} | Cost: ${cost:.5f}")
    
    print(f"\nTotal Run Cost: ${total_cost:.5f}\n")

    # Let's group by Trade evaluations
    # Trade 1: Calls 3 (Step 1), 4 & 5 (Step 2 + retry), 6 (DS Step 3), 7 (Claude Step 3), 8 (GPT4o Step 3), 9 (Andrea)
    # Trade 2: Calls 10 (Step 1), 11 (Step 2), 12 (DS Step 3), 13 (Claude Step 3), 14 (GPT4o Step 3), 15 (Andrea)
    # Trade 3 (Candidate rejected): Calls 17 (Step 1), 18 (Step 2), 19 (DS Step 3), 20 (Claude Step 3), 21 (GPT4o Step 3)
    # Others are isolated candidates that didn't trigger Step 2: Call 1 (13:31 Step 1), Call 2 (13:32 Step 1), Call 16 (13:35 Step 1)

    print("=== COST BY TRADE CONTEXT ===")
    
    # We will manually map the calls to keep it perfectly clean
    groups = {
        "Candidate 13:31 (Rejected at Step 1)": [0],
        "Candidate 13:32 (Rejected at Step 1)": [1],
        "Trade 1 at 13:33 (Stop Loss Hit)": [2, 3, 4, 5, 6, 7, 8],
        "Candidate 13:35 (Rejected at Step 1)": [15],
        "Trade 2 at 13:36 (Stop Loss Hit)": [9, 10, 11, 12, 13, 14],
        "Candidate 13:41 (Rejected at Step 3 Council)": [16, 17, 18, 19, 20]
    }

    for name, indices in groups.items():
        g_cost = 0.0
        g_in = 0
        g_out = 0
        models_used = {}
        for idx in indices:
            if idx >= len(lines):
                continue
            parts = lines[idx].split(",")
            _, model, in_tok, out_tok = parts
            in_tok, out_tok = int(in_tok), int(out_tok)
            cost = get_cost(model, in_tok, out_tok)
            g_cost += cost
            g_in += in_tok
            g_out += out_tok
            models_used[model] = models_used.get(model, 0) + cost
            
        print(f"\n{name}:")
        print(f"  Total Cost: ${g_cost:.5f} (In: {g_in}, Out: {g_out})")
        for m, mc in models_used.items():
            print(f"    - {m:<30}: ${mc:.5f}")

    # Now let's calculate the cost of a single Step 3 Council Audit specifically:
    # DeepSeek + Claude Sonnet 4.5 + GPT-4o
    print("\n=== STEP 3 COUNCIL AUDIT COST ONLY ===")
    
    # Trade 1 Council: calls 6, 7, 8
    # Trade 2 Council: calls 12, 13, 14
    # Trade 3 Council: calls 19, 20, 21
    c1_ds = lines[5].split(",")
    c1_cl = lines[6].split(",")
    c1_gpt = lines[7].split(",")
    
    c1_ds_c = get_cost(c1_ds[1], int(c1_ds[2]), int(c1_ds[3]))
    c1_cl_c = get_cost(c1_cl[1], int(c1_cl[2]), int(c1_cl[3]))
    c1_gpt_c = get_cost(c1_gpt[1], int(c1_gpt[2]), int(c1_gpt[3]))
    c1_tot = c1_ds_c + c1_cl_c + c1_gpt_c
    
    print(f"Trade 1 Council Cost: ${c1_tot:.5f}")
    print(f"  - DeepSeek: ${c1_ds_c:.5f} (In: {c1_ds[2]}, Out: {c1_ds[3]})")
    print(f"  - Claude Sonnet 4.5: ${c1_cl_c:.5f} (In: {c1_cl[2]}, Out: {c1_cl[3]})")
    print(f"  - GPT-4o: ${c1_gpt_c:.5f} (In: {c1_gpt[2]}, Out: {c1_gpt[3]})")
    
    c2_ds = lines[11].split(",")
    c2_cl = lines[12].split(",")
    c2_gpt = lines[13].split(",")
    
    c2_ds_c = get_cost(c2_ds[1], int(c2_ds[2]), int(c2_ds[3]))
    c2_cl_c = get_cost(c2_cl[1], int(c2_cl[2]), int(c2_cl[3]))
    c2_gpt_c = get_cost(c2_gpt[1], int(c2_gpt[2]), int(c2_gpt[3]))
    c2_tot = c2_ds_c + c2_cl_c + c2_gpt_c
    
    print(f"\nTrade 2 Council Cost: ${c2_tot:.5f}")
    print(f"  - DeepSeek: ${c2_ds_c:.5f} (In: {c2_ds[2]}, Out: {c2_ds[3]})")
    print(f"  - Claude Sonnet 4.5: ${c2_cl_c:.5f} (In: {c2_cl[2]}, Out: {c2_cl[3]})")
    print(f"  - GPT-4o: ${c2_gpt_c:.5f} (In: {c2_gpt[2]}, Out: {c2_gpt[3]})")
    
    # What if we replaced Claude Sonnet 4.5 with Claude 4.5 Haiku (or 3.5 Haiku)?
    # Claude Haiku 4.5 Input: 1.00/M, Output: 5.00/M
    # Let's project the cost of Claude Haiku in Council for Trade 1 and Trade 2:
    cl_haiku_c1 = get_cost("anthropic/claude-haiku-4.5", int(c1_cl[2]), int(c1_cl[3]))
    cl_haiku_c2 = get_cost("anthropic/claude-haiku-4.5", int(c2_cl[2]), int(c2_cl[3]))
    
    print(f"\n=== ESTIMATED COUNCIL COST WITH CLAUDE 4.5 HAIKU ===")
    print(f"Trade 1 Projected Council Cost: ${c1_ds_c + cl_haiku_c1 + c1_gpt_c:.5f} (Save: ${(c1_cl_c - cl_haiku_c1):.5f})")
    print(f"Trade 2 Projected Council Cost: ${c2_ds_c + cl_haiku_c2 + c2_gpt_c:.5f} (Save: ${(c2_cl_c - cl_haiku_c2):.5f})")
    
    # What if we used Claude 3.5 Haiku?
    cl35_haiku_c1 = get_cost("anthropic/claude-3.5-haiku", int(c1_cl[2]), int(c1_cl[3]))
    cl35_haiku_c2 = get_cost("anthropic/claude-3.5-haiku", int(c2_cl[2]), int(c2_cl[3]))
    print(f"\n=== ESTIMATED COUNCIL COST WITH CLAUDE 3.5 HAIKU ===")
    print(f"Trade 1 Projected Council Cost: ${c1_ds_c + cl35_haiku_c1 + c1_gpt_c:.5f} (Save: ${(c1_cl_c - cl35_haiku_c1):.5f})")
    print(f"Trade 2 Projected Council Cost: ${c2_ds_c + cl35_haiku_c2 + c2_gpt_c:.5f} (Save: ${(c2_cl_c - cl35_haiku_c2):.5f})")

if __name__ == "__main__":
    main()
