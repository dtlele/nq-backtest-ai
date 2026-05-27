import urllib.request
import re

url = "https://www.youtube.com/@MatFinOg/shorts"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    html = urllib.request.urlopen(req).read().decode('utf-8')
    match = re.search(r'var ytInitialData = (\{.*?\});<\/script>', html)
    if match:
        data_str = match.group(1).lower()
        if 'valentini' in data_str or 'ibv' in data_str:
            print("Found mentions!")
            import json
            data = json.loads(match.group(1))
            # Just search all strings in the json
            def find_mentions(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        find_mentions(v)
                elif isinstance(obj, list):
                    for item in obj:
                        find_mentions(item)
                elif isinstance(obj, str):
                    if 'valentini' in obj.lower() or 'ibv' in obj.lower():
                        print("Mention:", obj)
            find_mentions(data)
        else:
            print("No mentions of valentini or ibv in shorts page data.")
except Exception as e:
    print("Error:", e)
