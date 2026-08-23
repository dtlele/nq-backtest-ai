import json

transcript_path = r'C:\Users\Mauro\.gemini\antigravity-cli\brain\089b3d8c-522c-4c30-8d6c-943e0cf4c0a7\.system_generated\logs\transcript.jsonl'
output_path = r'C:\Users\Mauro\Documents\nq-backtest\audit_ragionamenti.md'

with open(transcript_path, 'r', encoding='utf-8') as f, open(output_path, 'w', encoding='utf-8') as out:
    out.write('# Audit dei ragionamenti della build bloccata\n\n')
    for line in f:
        try:
            data = json.loads(line)
            if data.get('type') == 'PLANNER_RESPONSE':
                thinking = data.get('thinking', '')
                content = data.get('content', '')
                out.write(f'## Step {data.get("step_index")}\n')
                if thinking:
                    out.write(f'**Thinking:**\n{thinking}\n\n')
                if content:
                    out.write(f'**Content:**\n{content}\n\n')
                tools = data.get('tool_calls', [])
                if tools:
                    out.write('**Tool calls:**\n')
                    for tool in tools:
                        out.write(f'- {tool.get("name")}\n')
                out.write('---\n\n')
            elif data.get('type') == 'ERROR_MESSAGE':
                out.write(f'## ERROR at Step {data.get("step_index")}\n')
                out.write(f'**Error:** {data.get("error")} (Code: {data.get("error_code")})\n\n')
        except Exception as e:
            pass

print('Audit generato in audit_ragionamenti.md')
