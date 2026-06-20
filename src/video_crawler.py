import os
import sys
import subprocess
from pathlib import Path

def crawl_and_learn(target_url: str):
    """
    Crawla un URL di YouTube (singolo video o playlist), 
    lo passa allo script di analisi Minimax,
    e a fine video aggiorna Graphify.
    """
    print(f"=== AVVIO VIDEO CRAWLER ===")
    print(f"Target: {target_url}")
    
    base_dir = Path(__file__).parent.parent
    scripts_dir = base_dir / "scripts"
    analyze_script = scripts_dir / "analyze_youtube.py"
    updater_script = base_dir / "src" / "graph_updater.py"
    output_reports_dir = base_dir / "output" / "reports"
    nuove_lezioni_dir = base_dir / "knowledge" / "nuove_lezioni"
    
    nuove_lezioni_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Recupera la lista dei video se è una playlist
    print("Analizzo l'URL per trovare i video...")
    try:
        # Usa yt-dlp per estrarre la lista piana degli URL
        result = subprocess.run(
            ["python", "-m", "yt_dlp", "--flat-playlist", "--get-id", target_url],
            capture_output=True, text=True, check=True
        )
        video_ids = [vid.strip() for vid in result.stdout.split('\n') if vid.strip()]
    except Exception as e:
        print(f"Errore nell'estrazione della playlist: {e}")
        return

    if not video_ids:
        print("Nessun video trovato.")
        return
        
    print(f"Trovati {len(video_ids)} video da analizzare.")
    
    for vid in video_ids:
        video_url = f"https://www.youtube.com/watch?v={vid}"
        print(f"\n--- PROCESSO VIDEO: {video_url} ---")
        
        # 2. Lancia l'analisi multimodale (MiniMax) via analyze_youtube.py
        # Usiamo subprocess.call così vediamo l'output a schermo
        cmd = [
            "python", str(analyze_script),
            video_url,
            "--model", "minimax/minimax-m3" # O il modello che usi di base
        ]
        
        ret = subprocess.call(cmd, env=os.environ)
        if ret != 0:
            print(f"Errore durante l'analisi del video {vid}. Salto al prossimo.")
            continue
            
        # 3. Lo script analyze_youtube.py produce un file MASTERCLASS in output/reports/
        # Dobbiamo trovare il file generato e spostarlo in knowledge/nuove_lezioni/
        # Assumiamo che il nome contenga il video_id.
        generated_mds = list(output_reports_dir.glob(f"*{vid}*.md"))
        if generated_mds:
            for md_file in generated_mds:
                dest = nuove_lezioni_dir / md_file.name
                import shutil
                shutil.copy(str(md_file), str(dest))
                print(f"Lezione estratta e copiata: {dest.name}")
                
            # 4. Aggiorna il Knowledge Graph
            print("Aggiorno il Knowledge Graph con la nuova lezione...")
            subprocess.call(["python", str(updater_script)], env=os.environ)
            print(f"Grafo aggiornato con successo per il video {vid}!")
        else:
            print(f"Non ho trovato il report testuale per il video {vid}. Controllare l'output di analyze_youtube.py.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Autonomously crawl YouTube and update Graphify")
    parser.add_argument("url", help="YouTube video or playlist URL")
    args = parser.parse_args()
    
    crawl_and_learn(args.url)
