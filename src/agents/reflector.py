import asyncio
import os
import datetime
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_ai import Agent

class LessonLearned(BaseModel):
    """
    Struttura della lezione estratta dall'errore.
    """
    concept_name: str = Field(..., description="Nome conciso del pattern o dell'errore (es. 'Failed Squeeze on High Delta')")
    lesson_markdown: str = Field(..., description="Testo completo in Markdown che descrive l'errore e la regola da seguire in futuro. NON includere i blocchi ```markdown ma solo il testo.")

# Agente Riflessivo per l'apprendimento continuo
reflector_agent = Agent(
    model='openai:z-ai/glm-5.2', # Usiamo DeepSeek
    output_type=LessonLearned,
    system_prompt=(
        "Sei il 'Cervello Riflessivo' di un Agente di Trading sul Nasdaq. "
        "Il tuo scopo è analizzare un trade che si è chiuso in STOP LOSS (o che è andato male). "
        "Riceverai il ragionamento originale dell'Esecutore e il contesto di mercato. "
        "Devi estrarre una lezione operativa da memorizzare nel Knowledge Graph per non ripetere l'errore. "
        "La lezione deve essere formattata in Markdown, chiara, e indicare in quali condizioni "
        "evitare quel setup in futuro."
    )
)

async def reflect_on_trade(trade_log: dict):
    """
    Analizza un trade perdente e salva la lezione.
    trade_log è un dizionario con i dati del trade (ragionamento, pnl, market state, ecc)
    """
    if trade_log.get("pnl", 0) >= 0:
        print("Trade in profitto. Nessuna lezione urgente da memorizzare.")
        return
        
    print(f"\n[Reflector] Analizzo il trade perso: {trade_log.get('trade_id', 'unknown')}")
    prompt = f"Analizza questo trade fallito:\n{trade_log}"
    
    try:
        result = await reflector_agent.run(prompt)
        lesson = result.output if hasattr(result, 'output') else result.data
        
        # Salva in Markdown (Cartella di Revisione Umana)
        base_dir = Path(__file__).parent.parent.parent
        pending_dir = base_dir / "knowledge" / "pending_reviews"
        pending_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = lesson.concept_name.replace(" ", "_").lower()
        file_path = pending_dir / f"lesson_reflector_{safe_name}_{timestamp_str}.md"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# Lezione Imparata (DRAFT): {lesson.concept_name}\n\n")
            f.write(lesson.lesson_markdown)
            f.write("\n\n---\n*Generato automaticamente da Reflector Agent - IN ATTESA DI APPROVAZIONE UMANA*")
            
        print(f"[Reflector] Lezione DRAFT salvata in: {file_path}")
        print("[Reflector] ATTENZIONE: La regola non è stata inserita nel Grafo.")
        print("[Reflector] Per approvarla, sposta il file in 'knowledge/nuove_lezioni/' e lancia graph_updater.py")
        
    except Exception as e:
        print(f"Errore durante la riflessione: {e}")

if __name__ == "__main__":
    # Test stub
    os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"
    if "OPENROUTER_API_KEY" in os.environ:
        os.environ["OPENAI_API_KEY"] = os.environ["OPENROUTER_API_KEY"]
        
    test_log = {
        "trade_id": "TEST_001",
        "action": "LONG",
        "market_state": "Prezzo a ridosso dell'IB High, delta positivo",
        "original_reasoning": "Ho tentato un breakout dell'IB High perché il delta era +500",
        "result": "Falsa rottura, crollato subito giù",
        "pnl": -150
    }
    
    asyncio.run(reflect_on_trade(test_log))
