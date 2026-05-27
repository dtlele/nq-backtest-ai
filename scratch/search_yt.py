import urllib.request
import re
import urllib.parse
import json
import sys

# Change default stdout encoding to utf-8
sys.stdout.reconfigure(encoding='utf-8')

queries = ['MatFinOg IBV', 'MatFinOg Fabio Valentini', 'MatFinOg IVB']

for query in queries:
    print(f"\n--- Searching YouTube for: {query} ---")
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
        match = re.search(r'var ytInitialData = (\{.*?\});<\/script>', html)
        if match:
            data = json.loads(match.group(1))
            videos = []
            def find_videos(obj):
                if isinstance(obj, dict):
                    if 'videoRenderer' in obj:
                        renderer = obj['videoRenderer']
                        title = ""
                        if 'title' in renderer and 'runs' in renderer['title']:
                            title = ''.join([r.get('text', '') for r in renderer['title']['runs']])
                        vid = renderer.get('videoId', '')
                        if title and vid:
                            videos.append(f"Title: {title}\nURL: https://www.youtube.com/watch?v={vid}")
                    for k, v in obj.items():
                        find_videos(v)
                elif isinstance(obj, list):
                    for item in obj:
                        find_videos(item)
            find_videos(data)
            
            for v in set(videos):
                print(v)
        else:
            print("ytInitialData not found for", query)
    except Exception as e:
        print("Error:", e)
