import json
with open('agent_memory/llm_cache.json', 'r') as f:
    data = json.load(f)
# Mostra le entries con direction=long/short per intero
for k, v in data.items():
    s = str(v)
    if '"direction": "long"' in s or '"direction": "short"' in s:
        print(f"=== KEY: {k[:20]} ===")
        print(s[:1500])
        print()
        break  # mostra solo la prima
