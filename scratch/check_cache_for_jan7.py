import json
from pathlib import Path

cache_file = Path('agent_memory/llm_cache.json')
with open(cache_file, encoding='utf-8') as f:
    cache = json.load(f)

print(f"Total entries: {len(cache)}")

found = False
for k, v in cache.items():
    if "21797.75" in v or "21797.25" in v or "21787.50" in v or "21662.50" in v:
        print(f"Found cache key: {k}")
        print(v)
        found = True

if not found:
    print("No cache entries found for Jan 7 successful run!")
