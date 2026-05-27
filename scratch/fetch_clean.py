from youtube_transcript_api import YouTubeTranscriptApi
import json

try:
    transcript_list = YouTubeTranscriptApi.list_transcripts('cUTsoU-15Tc')
    transcript = transcript_list.find_transcript(['it', 'en']).fetch()
    
    full_text = []
    for item in transcript:
        time_sec = int(item['start'])
        mins = time_sec // 60
        secs = time_sec % 60
        full_text.append(f"[{mins:02d}:{secs:02d}] {item['text']}")
        
    with open('scratch/transcript.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(full_text))
    print("Transcript saved successfully.")
except Exception as e:
    print(f"Error: {e}")
