import json

with open('agent_memory/reasoning_log.jsonl', encoding='utf-8') as f:
    for idx, line in enumerate(f):
        if idx == 11:
            data = json.loads(line)
            print(json.dumps(data, indent=2))
            break
