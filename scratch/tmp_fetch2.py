import sys
from youtube_transcript_api import YouTubeTranscriptApi

video_id = 'jsUTbjwpFVk'

try:
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    # try italian first, then english
    try:
        transcript = transcript_list.find_transcript(['it']).fetch()
    except:
        transcript = transcript_list.find_transcript(['en']).fetch()
        
    text = ' '.join([item['text'] for item in transcript])
    print(text)
except Exception as e:
    print(f"Error fetching transcript: {e}")
