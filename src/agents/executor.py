from pydantic import BaseModel, Field
from typing import Literal, Optional
from pydantic_ai import Agent, RunContext
import subprocess
import os

class MarketState(BaseModel):
    """
    Rappresenta lo stato del mercato in un dato momento (Barra M5 o M1).
    Input principale per l'agente esecutore.
    """
    timestamp: str = Field(..., description="Timestamp della barra (es. 2025-04-30 09:35)")
    close_price: float = Field(..., description="Prezzo di chiusura della barra")
    delta: int = Field(..., description="Delta dell'order flow (acquisti - vendite a mercato)")
    volume: int = Field(..., description="Volume totale scambiato")
    ib_high: float = Field(..., description="Initial Balance High")
    ib_low: float = Field(..., description="Initial Balance Low")
    vwap: float = Field(..., description="Livello del VWAP corrente")
    market_structure: str = Field(..., description="Struttura: balance, trend_up, trend_down")
    
class TradingSignal(BaseModel):
    """
    Rappresenta la decisione formale presa dall'agente.
    Pydantic forza l'output a rispettare strettamente questa struttura.
    """
    action: Literal['LONG', 'SHORT', 'HOLD'] = Field(..., description="L'azione da compiere")
    confidence_score: float = Field(..., description="Punteggio di confidenza da 0.0 a 1.0", ge=0.0, le=1.0)
    stop_loss: Optional[float] = Field(None, description="Livello di stop loss assoluto (obbligatorio se action è LONG o SHORT)")
    take_profit: Optional[float] = Field(None, description="Livello di take profit (opzionale)")
    reasoning: str = Field(..., description="Spiegazione dettagliata della motivazione strategica e dei pattern riconosciuti")

# Creazione dell'Agente PydanticAI
# Usa il modello specificato, o gpt-4o-mini di default. 
executor_agent = Agent(
    model='openai:z-ai/glm-5.2', # Usiamo DeepSeek tramite OpenRouter
    output_type=TradingSignal,
    system_prompt=(
        "Sei il 'Cervello Esecutore' per il trading ad alta precisione sul Nasdaq (NQ). "
        "Analizza il MarketState fornito e usa lo strumento `query_past_experience` se hai dubbi su specifici setup "
        "(es. 'Squeeze', 'Failed Auction', 'Absorption'). "
        "Le regole fondamentali di sopravvivenza sono dettate dall'Initial Balance (IB): "
        "- False rotture oltre IB High con delta negativo portano spesso a forti reverse. "
        "- Devi produrre SOLO output formattato come TradingSignal. Sii estremamente rigido."
    ),
)

async def execute_trade_decision(state: MarketState) -> TradingSignal:
    """
    Esegue l'agente passandogli lo stato attuale del mercato.
    """
    print(f"  [Executor] Valutando la situazione alle {state.timestamp} al prezzo {state.close_price}...")
    result = await executor_agent.run(
        f"Analizza questo stato di mercato: {state.model_dump_json()}"
    )
    # Debug: print what result contains
    # print(f"  [Debug Result Dir]: {dir(result)}")
    try:
        if hasattr(result, 'data'):
            return result.data
        elif hasattr(result, 'output'):
            return result.output
        else:
            return result
    except Exception as e:
        raise

@executor_agent.tool
async def query_past_experience(ctx: RunContext, pattern_keyword: str) -> str:
    """
    Interroga il Knowledge Graph di Graphify per recuperare la saggezza dei trader storici.
    Usa parole chiave in inglese legate ad Auction Market Theory (es. 'Squeeze', 'Failed Auction').
    """
    print(f"  [Graphify] L'Agente sta consultando il grafo per: '{pattern_keyword}'...")
    base_dir = os.path.dirname(__file__)
    graph_dir = os.path.abspath(os.path.join(base_dir, '..', '..', 'knowledge', 'trader_lessons_graph'))
    graphify_exe = r"C:\Users\Mauro\AppData\Local\Programs\Python\Python313\Scripts\graphify.exe"
    
    # Costruiamo la chiamata CLI per graphify
    cmd = [
        graphify_exe, 
        "query", 
        f"{pattern_keyword}", 
        "--graph", os.path.join(graph_dir, "graphify-out", "graph.json"),
        "--backend", "openai"
    ]
    
    try:
        # Usa env var ereditate per sfruttare OPENAI_API_KEY ecc.
        proc = subprocess.run(cmd, capture_output=True, text=True, env=os.environ, timeout=30)
        if proc.returncode == 0:
            return f"Risultato dal Knowledge Graph per '{pattern_keyword}':\n{proc.stdout}"
        else:
            return f"Impossibile consultare il grafo. Errore: {proc.stderr}"
    except Exception as e:
        return f"Errore locale nell'esecuzione della query Graphify: {str(e)}"
