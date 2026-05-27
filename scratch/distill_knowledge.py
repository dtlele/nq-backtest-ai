import json
import os
import time
from pathlib import Path
from google import genai
from google.genai.errors import ClientError
from dotenv import load_dotenv

load_dotenv('.env')
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

DISTILL_PROMPT = """You are an expert trading systems engineer.
I will give you a piece of conversational text describing a trading rule or context.
Rewrite it into a hyper-condensed, strict set of mathematical/logical rules (bullet points).
- Remove all conversational prose.
- Keep ONLY the raw logic (e.g., thresholds, conditions, setups).
- Make it as short as possible without losing trading rules.
- Do NOT use markdown code blocks, just raw text.
"""

def distill_text(text: str) -> str:
    if len(text) < 50:
        return text
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            time.sleep(4.1) # respect 15 RPM
            response = client.models.generate_content(
                model=model,
                contents=[
                    {"role": "user", "parts": [{"text": f"{DISTILL_PROMPT}\n\nTEXT:\n{text}"}]}
                ]
            )
            return response.text.strip()
        except ClientError as e:
            if e.code == 429:
                print(f"  [429] Sleeping 60s...")
                time.sleep(60)
            else:
                raise
    return text

def distill_batch(items: dict) -> dict:
    if not items: return {}
    
    # Construct a single batched prompt
    prompt = DISTILL_PROMPT + "\n\nPlease process the following items. Return the output as a valid JSON object where keys are the original IDs, and values are the condensed text.\n\n"
    prompt += json.dumps(items, indent=2, ensure_ascii=False)
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            time.sleep(5)
            response = client.models.generate_content(
                model=model,
                contents=[{"role": "user", "parts": [{"text": prompt}]}]
            )
            text = response.text.strip()
            if text.startswith("```json"): text = text[7:]
            elif text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            return json.loads(text.strip())
        except ClientError as e:
            if e.code == 429:
                print(f"  [429] Sleeping 60s...")
                time.sleep(60)
            else:
                print(f"  [API Error] {e}")
                time.sleep(30)
        except json.JSONDecodeError:
            print("  [JSON Error] Failed to parse batch output. Retrying...")
            time.sleep(5)
    return items # fallback to original if failed

def chunk_dict(d: dict, size=5):
    it = iter(d)
    for i in range(0, len(d), size):
        yield {k: d[k] for k in [next(it) for _ in range(min(size, len(d) - i))]}

def process_file(in_path: str, out_path: str):
    print(f"Processing {in_path}...")
    with open(in_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    out_data = {}
    for section in ['knowledge_by_topic', 'simplified_strategy', 'trading_rules', 'confirmation_rules']:
        if section in data:
            print(f"--- Section: {section} ---")
            out_data[section] = {}
            # Filter for string values only
            valid_items = {k: v for k, v in data[section].items() if isinstance(v, str) and len(v) > 50}
            short_items = {k: v for k, v in data[section].items() if isinstance(v, str) and len(v) <= 50}
            out_data[section].update(short_items)
            
            for batch in chunk_dict(valid_items, 10):
                print(f"  Distilling batch of {len(batch)} items...")
                distilled = distill_batch(batch)
                # Merge back
                for k in batch:
                    out_data[section][k] = distilled.get(k, batch[k])
                    
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out_data, f, indent=2, ensure_ascii=False)
    print(f"Saved {out_path}")

if __name__ == '__main__':
    base = Path(r"C:\Users\Mauro\Documents\nq-backtest\knowledge")
    
    fabio_in = base / "fabio_knowledge.json"
    fabio_out = base / "fabio_distilled.json"
    process_file(fabio_in, fabio_out)
    
    andrea_in = base / "andrea_knowledge.json"
    andrea_out = base / "andrea_distilled.json"
    if andrea_in.exists():
        process_file(andrea_in, andrea_out)
