import urllib.request
import urllib.parse
import re
import json
import os
import subprocess
from pathlib import Path

# Termini di ricerca per i maestri
QUERIES = [
    "World Class Edge masterclass",
    "World Class Edge Fabio Valentini",
    "World Class Edge Andrea",
    "MatFinOg Fabio",
    "MatFinOg Masterclass"
]

def search_youtube(query: str, limit: int = 3):
    """Cerca su YouTube e restituisce i primi N URL di video trovati."""
    print(f"\n[Search] Cerco su YouTube: {query}")
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query) + "&sp=CAI%253D" # sp=CAI%3D ordina per data (recenti)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    found_urls = []
    
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
        match = re.search(r'var ytInitialData = (\{.*?\});<\/script>', html)
        if match:
            data = json.loads(match.group(1))
            
            def find_videos(obj):
                if len(found_urls) >= limit: return
                if isinstance(obj, dict):
                    if 'videoRenderer' in obj:
                        renderer = obj['videoRenderer']
                        title = ""
                        if 'title' in renderer and 'runs' in renderer['title']:
                            title = ''.join([r.get('text', '') for r in renderer['title']['runs']])
                        vid = renderer.get('videoId', '')
                        
                        # Filtro antispam base: ignoriamo gli shorts se possibile
                        if title and vid and len(vid) == 11:
                            video_link = f"https://www.youtube.com/watch?v={vid}"
                            if video_link not in [v['url'] for v in found_urls]:
                                found_urls.append({"title": title, "url": video_link})
                                
                    for k, v in obj.items():
                        find_videos(v)
                elif isinstance(obj, list):
                    for item in obj:
                        find_videos(item)
                        
            find_videos(data)
    except Exception as e:
        print(f"Errore nella ricerca per {query}: {e}")
        
    return found_urls

def run_discovery():
    print("=== AVVIO AUTODISCOVERY VIDEO ===")
    all_videos = []
    for q in QUERIES:
        vids = search_youtube(q, limit=2) # Prendiamo i 2 più recenti per ogni query
        all_videos.extend(vids)
        
    # Rimuovi duplicati basati su URL
    unique_videos = {v['url']: v['title'] for v in all_videos}
    
    print(f"\nTrovati {len(unique_videos)} video unici recenti/masterclass:")
    for url, title in unique_videos.items():
        print(f" - {title}\n   {url}")
        
    print("\nLancio il Video Crawler in background per analizzare ed estrarre la conoscenza...")
    crawler_script = Path(__file__).parent.parent / "src" / "video_crawler.py"
    
    for url in unique_videos.keys():
        print(f"\nInvio al Crawler: {url}")
        # Usa subprocess per lanciare il crawler. In un ambiente reale potremmo lanciarli asincroni.
        cmd = ["python", str(crawler_script), url]
        try:
            # Per evitare di bloccare il server per ore, eseguiamo solo il primo a scopo dimostrativo o limitiamo
            subprocess.call(cmd, env=os.environ)
        except Exception as e:
            print(f"Errore nell'analisi di {url}: {e}")

if __name__ == "__main__":
    run_discovery()
