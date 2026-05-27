import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

api_key = os.environ.get("GEMINI_API_KEY")
print(f"API Key found in .env: {api_key[:8]}...{api_key[-4:] if api_key else ''}")
print(f"LLM_PROVIDER in .env: {os.environ.get('LLM_PROVIDER')}")
print(f"GEMINI_MODEL in .env: {os.environ.get('GEMINI_MODEL')}")

try:
    from google import genai
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    print("Testing connection to Gemini...")
    response = client.models.generate_content(
        model=model,
        contents="Hello! Confirm if you can read this."
    )
    print("Connection SUCCESSFUL!")
    print(f"Response: {response.text.strip()}")
except Exception as e:
    print(f"Connection FAILED: {e}")
