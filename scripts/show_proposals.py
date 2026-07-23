import json, re
with open('agent_memory/llm_cache.json', 'r') as f:
    data = json.load(f)
for k, v in data.items():
    s = str(v)
    if '"direction": "long"' in s or '"direction": "short"' in s:
        try:
            txt = s.strip()
            if txt.startswith('```'):
                txt = txt.split('```')[1].lstrip('json').strip()
            jstart = txt.find('{')
            jend = txt.rfind('}') + 1
            if jstart >= 0 and jend > jstart:
                inner = txt[jstart:jend]
                parsed = json.loads(inner)
                d = parsed.get("direction")
                c = parsed.get("confidence")
                setup = parsed.get("setup")
                e = parsed.get("entry")
                st = parsed.get("stop")
                t = parsed.get("target")
                print(f"  KEY: {k[:20]} dir={d} conf={c} setup={setup} entry={e} stop={st} target={t}")
        except Exception as e:
            print(f"  ERR: {e}")
