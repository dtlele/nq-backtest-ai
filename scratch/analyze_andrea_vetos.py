import json
from collections import Counter

vetoes = []
total_fabio_ok = 0
total_approved = 0

with open('c:/Users/Mauro/Documents/nq-backtest/agent_memory/reasoning_log.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        if not line.strip(): continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        
        # We only care about decisions where Fabio was OK (confidence >= 75)
        fabio_conf = r.get('fabio_confidence', 0)
        if fabio_conf >= 75:
            total_fabio_ok += 1
            no_trade_reason = r.get('no_trade_reason') or ''
            
            # Check if Andrea vetoed
            is_veto = 'andrea_veto' in no_trade_reason or r.get('andrea_confirmation') is False
            if is_veto:
                vetoes.append(r)
            else:
                total_approved += 1

print(f"Total candidates approved by Fabio (>=75): {total_fabio_ok}")
print(f"Total approved by Andrea (consensus): {total_approved}")
print(f"Total vetoed by Andrea: {len(vetoes)}")
if vetoes:
    print("\nSample of Andrea Vetoes:")
    for v in vetoes[:15]:
        print(f"Date: {v.get('date')}, Setup: {v.get('setup_type')}")
        print(f"  Fabio ({v.get('fabio_confidence')}): {v.get('fabio_reasoning', '')[:150]}...")
        print(f"  Andrea ({v.get('andrea_confidence')}): {v.get('andrea_reasoning', '')[:150]}...")
        print(f"  Reason: {v.get('no_trade_reason')}")
        print("-" * 50)
