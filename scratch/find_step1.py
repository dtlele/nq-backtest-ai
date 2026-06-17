import json
from pathlib import Path

cache_file = Path('agent_memory/llm_cache.json')
with open(cache_file, encoding='utf-8') as f:
    cache = json.load(f)

print("Finding step 1...")
for k, v in cache.items():
    if "bias" in v and "short" in v and "trapped_side" in v and "buyers" in v and "setup_valid" in v:
        print(f"Key: {k}")
        print(v)
        print("---")
