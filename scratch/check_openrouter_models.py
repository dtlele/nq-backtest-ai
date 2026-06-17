import urllib.request
import json

url = "https://openrouter.ai/api/v1/models"
try:
    with urllib.request.urlopen(url) as response:
        data = json.loads(response.read().decode())
        models = data.get("data", [])
        print(f"Total models found: {len(models)}")
        
        # Filter and print Claude, GPT-4, and DeepSeek models
        for m in models:
            id_lower = m["id"].lower()
            if "claude" in id_lower or "gpt-4" in id_lower or "deepseek" in id_lower or "haiku" in id_lower:
                print(f"ID: {m['id']} | Name: {m['name']} | Input Cost: {m.get('pricing', {}).get('prompt', 0)} | Output Cost: {m.get('pricing', {}).get('completion', 0)}")
except Exception as e:
    print(f"Error fetching models: {e}")
