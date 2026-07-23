import json
with open('agent_memory/llm_cache.json', 'r') as f:
    data = json.load(f)
for k, v in data.items():
    print(f"=== KEY: {k[:20]} ===")
    print(str(v)[:1500])
    print()
    break
