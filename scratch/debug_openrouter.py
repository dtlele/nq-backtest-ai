import os
import sys
import base64
import requests
import mimetypes
from pathlib import Path
from dotenv import load_dotenv

# Load .env
load_dotenv(Path(__file__).parent.parent / ".env")

api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    print("Missing OPENROUTER_API_KEY")
    sys.exit(1)

tmp_dir = Path(__file__).parent.parent / "tmp_data"
# Cerca il file compresso
video_files = list(tmp_dir.glob("yt_xUyqIjCfZzg_s0_e1800_compressed.mp4"))

if not video_files:
    print("No compressed video file found in tmp_data.")
    sys.exit(1)

video_path = video_files[0]
print(f"Using video: {video_path} ({video_path.stat().st_size / (1024*1024):.2f} MB)")

# Encode to base64
print("Encoding video to base64...")
mime_type, _ = mimetypes.guess_type(str(video_path))
if not mime_type:
    mime_type = "video/mp4"

with open(video_path, "rb") as vf:
    video_data = base64.b64encode(vf.read()).decode("utf-8")

print("Sending request to OpenRouter...")
url = "https://openrouter.ai/api/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "http://localhost:8000",
    "X-Title": "AgentForge Debugger",
}

payload = {
    "model": "minimax/minimax-m3",
    "messages": [
        {"role": "system", "content": "Sei un assistente AI esperto in analisi video."},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Di cosa parla questo video?"},
                {
                    "type": "video_url",
                    "video_url": {
                        "url": f"data:{mime_type};base64,{video_data}"
                    }
                }
            ]
        }
    ]
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=300)
    print(f"Status Code: {response.status_code}")
    print("Response text (first 2000 chars):")
    print(response.text[:2000])
except Exception as e:
    print(f"Request failed: {e}")
