import os
import json
from pathlib import Path

def search():
    brain_dir = Path(r"C:\Users\Mauro\.gemini\antigravity\brain\7b2894bf-5820-44d9-a942-e238dea2433b")
    transcript_path = brain_dir / ".system_generated" / "logs" / "transcript.jsonl"
    
    with open(transcript_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                obj = json.loads(line)
                if obj.get("type") == "USER_INPUT":
                    content = obj.get("content", "")
                    print(f"Line {line_no} | USER: {content[:300]}")

if __name__ == "__main__":
    search()
