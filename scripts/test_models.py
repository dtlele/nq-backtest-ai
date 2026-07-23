import os, requests, time, json
key = os.environ.get('OPENROUTER_API_KEY', '')

models_to_test = [
    'minimax/minimax-m2.5',
    'z-ai/glm-4.7-flash',
    'deepseek/deepseek-v4-flash',
    'z-ai/glm-5.2',
    'z-ai/glm-5',
    'minimax/minimax-m2.7',
]
prompt = """You are an elite NQ orderflow scalper. Make a decision in JSON.

## Snapshot
- bias: drive_down (-50)
- price: 21800
- vwap: 21850
- wall @ 21800 size=127 SELL
- delta cumulative last 6 bars: -494
- Volume: 7390
- IB high 21790, low 21740
- time: 10:20 ET

Return JSON: {"direction": "long|short|none", "confidence": 0-100, "setup": "pullback|squeeze|ivb|imbalance|none", "entry": float, "stop": float, "target": float, "reasoning": "<15 words>"}"""

for model in models_to_test:
    t0 = time.time()
    try:
        r = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={'model': model, 'messages': [{'role':'user','content':prompt}], 'max_tokens': 1500, 'temperature': 0.1},
            timeout=60,
        )
        elapsed = time.time() - t0
        d = r.json()
        content = d['choices'][0]['message'].get('content') or ''
        finish = d['choices'][0].get('finish_reason', 'unknown')
        tokens = d.get('usage', {})
        out_tok = tokens.get('completion_tokens', 0)
        print(f'{model}:')
        print(f'  {elapsed:.1f}s, finish={finish}, in={tokens.get("prompt_tokens","?")}, out={out_tok}')
        if content.strip():
            txt = content.strip()
            if txt.startswith('```'):
                txt = txt.split('```')[1].lstrip('json').strip()
            try:
                parsed = json.loads(txt)
                print(f'  JSON OK: dir={parsed.get("direction")}, conf={parsed.get("confidence")}, setup={parsed.get("setup")}')
            except Exception as e:
                print(f'  PARSE ERR: {e}')
                print(f'  Content[:200]: {content[:200]}')
        else:
            print(f'  EMPTY content (finish={finish})')
    except Exception as e:
        print(f'{model}: ERROR {e}')
    print()
