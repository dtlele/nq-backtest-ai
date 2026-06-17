import json
from pathlib import Path

cache_file = Path('agent_memory/llm_cache.json')
if not cache_file.exists():
    print("Cache file not found!")
    exit()

with open(cache_file, encoding='utf-8') as f:
    cache = json.load(f)

print(f"Total cache entries: {len(cache)}")

# Search for entries with 2025-01-07 or 09:31 or 21786.00
matches = []
for k, v in cache.items():
    # k is the key, which is SHA256 of the prompt or maybe the prompt itself?
    # Let's inspect the keys and values.
    # In llm_client.py, key = _cache_key(system_prompt, user_msg)
    # Let's see what _cache_key returns. It returns a string.
    # Let's search inside the value (response) or the key if it's stored as dict
    # Wait, in llm_client.py, cache is stored as a flat dict.
    # Let's see what is inside cache. Let's print one key/value structure.
    # Actually, in llm_client.py, _cache_key is:
    # def _cache_key(system_prompt: str, user_msg: str, video_path: str = None) -> str:
    #     hasher = hashlib.sha256()
    #     hasher.update(system_prompt.encode('utf-8'))
    #     hasher.update(user_msg.encode('utf-8'))
    #     ...
    # So the key is a SHA256 hash string (64 hex characters)!
    # And the value is the LLM raw response string!
    # Let's search inside the values (responses) for keywords like "21782" or "21797" or "21786" or "577".
    # And let's print the value and key.
    if any(kw in v for kw in ["21782", "21797", "21786", "577", "trapped buyers", "reversal zone"]):
        matches.append((k, v))

print(f"Found {len(matches)} matching entries:")
for i, (k, v) in enumerate(matches[:10]):
    print(f"\n--- Match {i+1} (Key: {k}) ---")
    print(v)
