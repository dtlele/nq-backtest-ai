import os
import shutil
import subprocess
from pathlib import Path

def update_graph():
    print("=== INIZIO SINCRONIZZAZIONE GRAPHIFY ===")
    
    base_dir = Path(__file__).parent.parent
    nuove_lezioni_dir = base_dir / "knowledge" / "nuove_lezioni"
    graph_dir = base_dir / "knowledge" / "trader_lessons_graph"
    
    # Crea le cartelle se non esistono
    nuove_lezioni_dir.mkdir(parents=True, exist_ok=True)
    graph_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Trova tutti i file markdown nelle nuove lezioni
    md_files = list(nuove_lezioni_dir.glob("*.md"))
    if not md_files:
        print("Nessun nuovo file da aggiungere al grafo. Sincronizzazione terminata.")
        return
        
    print(f"Trovati {len(md_files)} nuovi documenti. Spostamento nel grafo principale...")
    
    # 2. Sposta i file
    for md_file in md_files:
        dest_path = graph_dir / md_file.name
        # Se esiste già, lo sovrascrive
        shutil.move(str(md_file), str(dest_path))
        print(f" -> {md_file.name} aggiunto alla libreria.")
        
    # 3. Lancia Graphify Extract (aggiornamento incrementale)
    print("\nLancio l'estrazione incrementale di Graphify...")
    graphify_exe = r"C:\Users\Mauro\AppData\Local\Programs\Python\Python313\Scripts\graphify.exe"
    
    extract_cmd = [
        graphify_exe,
        "extract",
        str(graph_dir),
        "--backend", "openai"  # Usa OpenRouter/Haiku o DeepSeek impostato in ENV
    ]
    
    try:
        proc_ext = subprocess.run(extract_cmd, capture_output=True, text=True, env=os.environ)
        print(proc_ext.stdout)
        if proc_ext.returncode != 0:
            print(f"[ERRORE EXTRACT] {proc_ext.stderr}")
            return
    except Exception as e:
        print(f"Errore lancio graphify: {e}")
        return
        
    # 4. Lancia Graphify Cluster per raggruppare i nuovi nodi e generare l'HTML
    print("\nRicostruzione delle comunità e generazione HTML (Cluster)...")
    cluster_cmd = [
        graphify_exe,
        "cluster-only",
        str(graph_dir),
        "--backend", "openai"
    ]
    
    try:
        proc_clust = subprocess.run(cluster_cmd, capture_output=True, text=True, env=os.environ)
        print(proc_clust.stdout)
        if proc_clust.returncode != 0:
            print(f"[ERRORE CLUSTER] {proc_clust.stderr}")
            return
    except Exception as e:
        print(f"Errore lancio graphify cluster: {e}")
        return
        
    print("\n=== SINCRONIZZAZIONE GRAPHIFY COMPLETATA! ===")

if __name__ == "__main__":
    update_graph()
