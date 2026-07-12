import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    cache_file = ROOT / "agent_memory" / "llm_cache.json"
    if not cache_file.exists():
        print("Cache file not found.")
        return
        
    with open(cache_file, encoding="utf-8") as f:
        cache = json.load(f)
        
    print(f"Total entries in cache: {len(cache)}")
    
    # Prendi gli ultimi 50 inserimenti
    keys = list(cache.keys())
    last_entries = keys[-50:]
    
    print("\n--- ULTIME 50 VOCI NELLA CACHE ---")
    for idx, k in enumerate(last_entries):
        val = cache[k]
        snippet = val[:150].replace('\n', ' ')
        print(f"Index: {len(keys) - 50 + idx} | Key: {k} | Length: {len(val)} | Snippet: {snippet}...")

if __name__ == "__main__":
    main()
