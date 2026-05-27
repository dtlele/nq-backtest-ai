import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# We use the google-genai SDK if available, otherwise requests
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY not found in .env")
    exit(1)

import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)
# We use gemini-2.5-flash if available, or 2.0-flash
model = genai.GenerativeModel(
    os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    generation_config={"response_mime_type": "application/json"}
)

MAILBOX_DIR = Path("agent_memory/mailbox")

def process_mailbox():
    print(f"Starting Gemini Auto-Mailbox... Watching {MAILBOX_DIR}")
    while True:
        requests = list(MAILBOX_DIR.glob("request_*.json"))
        for req_path in requests:
            try:
                with open(req_path, "r", encoding="utf-8") as f:
                    req_data = json.load(f)
                
                key = req_data["key"]
                system_prompt = req_data["system_prompt"]
                user_msg = req_data["user_msg"]
                
                print(f"\n[GEMINI] Processing request {key[:8]}...")
                
                # Call Gemini
                prompt = f"{system_prompt}\n\n---\n\n{user_msg}"
                response = model.generate_content(prompt)
                
                decision_text = response.text
                print(f"  Raw response: {decision_text}")
                
                # Try parsing it to ensure it's valid JSON
                decision = json.loads(decision_text)
                
                decision_path = MAILBOX_DIR / f"decision_{key}.json"
                with open(decision_path, "w", encoding="utf-8") as f:
                    json.dump(decision, f, indent=2)
                    
                print(f"  [GEMINI] Saved decision for {key[:8]}")
                
            except Exception as e:
                print(f"  [GEMINI] Error processing {req_path.name}: {e}")
                time.sleep(1)
        
        time.sleep(2)

if __name__ == "__main__":
    process_mailbox()
