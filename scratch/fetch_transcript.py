from youtube_transcript_api import YouTubeTranscriptApi
import json

try:
    transcript = YouTubeTranscriptApi.get_transcript('cUTsoU-15Tc', languages=['it', 'en'])
    with open('scratch/transcript.json', 'w', encoding='utf-8') as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)
    print("Transcript saved.")
except Exception as e:
    print(f"Error: {e}")
