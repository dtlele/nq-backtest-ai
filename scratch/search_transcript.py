import json

def search_user_inputs():
    transcript_path = r'C:\Users\Mauro\.gemini\antigravity\brain\e86b7458-2bf7-4121-9908-1844e8f5d6dd\.system_generated\logs\transcript.jsonl'
    
    with open(transcript_path, 'r', encoding='utf-8') as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                obj = json.loads(line)
                if obj.get('type') == 'USER_INPUT':
                    content = obj.get('content', '')
                    if 'luglio' in content.lower() or 'july' in content.lower():
                        print(f"Line {line_no} | USER: {content}")

if __name__ == '__main__':
    search_user_inputs()
