import json

print("Extracting Fabio's reasoning from recent trades...\n")
with open('dashboard/public/data/status.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
    for t in d.get('ALL_TRADES', []):
        print(f"Date: {t['date']} | Time: {t.get('entry_time', '')} | Dir: {t['direction'].upper()} | Confidence: {t.get('final_confidence', 'N/A')}")
        print(f"Setup: {t.get('setup_type', 'N/A')}")
        print(f"Reasoning: {t.get('fabio_reasoning', '')}")
        print("-" * 80)

