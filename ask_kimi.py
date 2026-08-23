import sys
from pathlib import Path

# Aggiungi project root a sys.path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.llm_client import llm_ask

def main():
    status_file = PROJECT_ROOT / "STATUS_REVIEW_KIMI.md"
    if not status_file.exists():
        print("Errore: STATUS_REVIEW_KIMI.md non trovato.")
        return

    content = status_file.read_text(encoding="utf-8")
    
    system_prompt = """
Sei Kimi K3, un AI Engineer esperto. Il tuo compito è revisionare il lavoro svolto sulla piattaforma volumetrica DeepPrint Pro.
Leggi il resoconto qui sotto e rispondi alla domanda finale sul problema dei dati (simulazione OHLCV vs download tick data reali da Databento).
Fornisci consigli e direttive su come procedere domani. Rispondi in italiano.
"""
    
    print("Inviando la richiesta a Kimi K3 (via OpenRouter)... attendere.")
    response = llm_ask(system_prompt, content, use_cache=False)
    
    output_file = PROJECT_ROOT / "KIMI_REVIEW_RESPONSE.md"
    output_file.write_text(f"# Risposta di Kimi K3\n\n{response}", encoding="utf-8")
    
    print(f"\nRisposta ricevuta e salvata in: {output_file.name}")
    print("\n--- INIZIO RISPOSTA ---")
    print(response)
    print("--- FINE RISPOSTA ---\n")

if __name__ == "__main__":
    main()
