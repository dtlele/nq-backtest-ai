import json

with open('agent_memory/reasoning_log.jsonl', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if '2025-01-28' in line:
            try:
                t = json.loads(line)
                time_et = t.get('bar_time_et', '')
                if time_et and ('10:1' in time_et or '10:20' in time_et or '10:21' in time_et or '10:22' in time_et or '10:23' in time_et):
                    print("="*80)
                    print(f"Index: {i} | Time ET: {time_et}")
                    print(f"Decision: {t.get('decision')} | Fabio Setup: {t.get('fabio_setup')} | Direction: {t.get('trade_direction') or t.get('fabio_direction')}")
                    print(f"Fabio Reasoning:\n{t.get('fabio_reasoning')}")
                    if t.get('andrea_reasoning'):
                        print(f"Andrea Reasoning:\n{t.get('andrea_reasoning')}")
                    if t.get('no_trade_reason'):
                        print(f"No Trade Reason: {t.get('no_trade_reason')}")
            except Exception as e:
                print(f"Error parsing line {i}: {e}")
