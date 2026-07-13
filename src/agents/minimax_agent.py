import os
from pathlib import Path
from src.agents.llm_client import llm_ask

def analyze_video(video_path: str, prompt: str = "Descrivi nel dettaglio cosa succede in questo video, concentrandoti sui pattern di trading, footprint o price action se presenti.") -> str:
    """
    Usa il modello Minimax via OpenRouter per visionare e comprendere un video.
    Assicurati che `llm_client.py` sia configurato per accettare e encodare il video.
    """
    video_file = Path(video_path)
    if not video_file.exists():
        raise FileNotFoundError(f"Video non trovato: {video_path}")
        
    print(f"  [MINIMAX] Inviando il video {video_file.name} al modello per la comprensione...")
    
    # Sostituisci con l'ID corretto del modello Minimax su OpenRouter che supporta la vision/video
    # Ad esempio: "minimax/video-01" o il nome corretto. 
    # NOTA: OpenRouter potrebbe richiedere Gemini o Claude per l'analisi video pura, 
    # ma proviamo a forzare minimax se supportato.
    model_id = "minimax/video-01" 
    
    system_prompt = (
        "Sei 'Minimax', un analista quantitativo esperto. "
        "Il tuo compito è guardare i video forniti dall'utente fotogramma per fotogramma, "
        "comprendere l'azione dei prezzi, i pattern di order flow e fornire un riassunto dettagliato."
    )
    
    try:
        response = llm_ask(
            system_prompt=system_prompt,
            user_msg=prompt,
            video_path=str(video_file),
            provider="openrouter",
            model=model_id,
            timeout=300 # I video richiedono più tempo
        )
        return response
    except Exception as e:
        print(f"  [MINIMAX] Errore durante l'analisi video: {e}")
        return str(e)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python minimax_agent.py <percorso_del_video.mp4> [prompt_opzionale]")
        sys.exit(1)
        
    v_path = sys.argv[1]
    usr_prompt = sys.argv[2] if len(sys.argv) > 2 else "Analizza questo video di trading."
    
    result = analyze_video(v_path, usr_prompt)
    print("\n=== RISPOSTA MINIMAX ===\n")
    print(result)
    print("\n========================")
