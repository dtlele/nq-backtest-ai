import urllib.request
import re
import json
import html as html_lib

def get_transcript(video_id):
    url = f'https://www.youtube.com/watch?v={video_id}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8')
    
    match = re.search(r'"captions":({"playerCaptionsTracklistRenderer".*?})', html)
    if not match:
        return 'No captions found'
    
    captions_json = json.loads(match.group(1))
    caption_tracks = captions_json['playerCaptionsTracklistRenderer']['captionTracks']
    
    target_track = caption_tracks[0]
    for track in caption_tracks:
        if track['languageCode'] in ['it', 'en']:
            target_track = track
            break
            
    xml_url = target_track['baseUrl']
    xml_req = urllib.request.Request(xml_url, headers={'User-Agent': 'Mozilla/5.0'})
    xml_content = urllib.request.urlopen(xml_req).read().decode('utf-8')
    
    texts = re.findall(r'<text[^>]*>(.*?)</text>', xml_content)
    texts = [html_lib.unescape(t) for t in texts]
    return ' '.join(texts)

if __name__ == '__main__':
    try:
        print(get_transcript('jsUTbjwpFVk'))
    except Exception as e:
        print(e)
