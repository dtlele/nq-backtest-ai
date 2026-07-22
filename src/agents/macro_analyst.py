import json
import os
from pathlib import Path
from src.agents.llm_client import llm_ask
from src.data.overnight_processor import process_overnight_session

def generate_daily_roadmap(target_date_str: str, overnight_trades_file: str) -> dict:
    """
    Legge i dati GEX e le statistiche Overnight, e interroga l'LLM per generare la Roadmap.
    """
    # 1. Carica GEX dal file JSON di configurazione
    # Convertiamo i path per assicurarci che funzionino ovunque
    base_dir = Path("C:/Users/Mauro/Documents/nq-backtest-clean")
    gex_path = base_dir / 'config' / 'daily_gex.json'
    gex_data = {}
    if gex_path.exists():
        with open(gex_path, 'r', encoding='utf-8') as f:
            all_gex = json.load(f)
            gex_data = all_gex.get(target_date_str, {})
            
    # 2. Calcola le metriche della sessione Overnight
    overnight_stats = {}
    if os.path.exists(overnight_trades_file):
        overnight_stats = process_overnight_session(overnight_trades_file, target_date_str)
    else:
        print(f"[WARN] File trades overnight non trovato: {overnight_trades_file}")
        
    # 3. Costruisce il Prompt per il LLM
    system_prompt = """You are an Institutional Macro Analyst for NQ futures (Nasdaq 100), trained by Fabio Valentini's methodology.
Your job is to analyze the Gamma Exposure (GEX) levels and the Overnight (Globex) volume profile to create a Daily Roadmap.
You must generate 3 possible scenarios for the upcoming RTH (Regular Trading Hours) session, preceded by a DEEP, EXTENDED reflection on the market structure.

CRITICAL RULES FOR ANALYSIS:
1. GEX (if available): Positive GEX dampens volatility (fade breakouts), Negative GEX amplifies volatility (trade breakouts). Treat Call/Put Walls as magnets/barriers.
2. If GEX is NOT available, focus entirely on the Overnight Profile: Overnight High, Overnight Low, Overnight POC (Point of Control), and VWAP.
3. Your `context_analysis` MUST BE a deep, extended 2-3 paragraph reflection. You must explicitly list the available levels and explain IN DETAIL how price could interact with them, which ranges are available, and how a trader should practically use these levels today. Do not write a short summary; write a comprehensive market prep.

Respond ONLY with valid JSON matching this exact schema:
{
  "context_analysis": "<A deep, extended reflection on all available levels, explaining how price could move within them and how to use them. Write at least 4-5 rich sentences.>",
  "bullish_scenario": {"trigger_description": "<what must happen to confirm bullish trend>", "target_level": <float>},
  "bearish_scenario": {"trigger_description": "<what must happen to confirm bearish trend>", "target_level": <float>},
  "chop_scenario": {"range_high": <float>, "range_low": <float>}
}"""

    user_prompt = f"""## DATA FOR {target_date_str}
GEX Levels (Pre-calculated):
{json.dumps(gex_data, indent=2)}

Overnight Session Stats (18:00 ET to 09:30 ET):
{json.dumps(overnight_stats, indent=2)}

Please generate the Daily Roadmap JSON."""

    # 4. Chiama il modello LLM
    model = "z-ai/glm-5.2"
    print(f"Richiesta della Daily Roadmap a {model} per la data {target_date_str}...")
    raw = llm_ask(system_prompt, user_prompt, model=model)
    
    # Pulisce l'output JSON
    if raw.startswith('```'):
        raw = raw.split('```')[1].lstrip('json').strip()
        
    try:
        data = json.loads(raw)
        # Salviamo l'informazione di base per log
        data['date'] = target_date_str
        data['overnight_vwap'] = overnight_stats.get('overnight_vwap')
    except json.JSONDecodeError:
        print(f"Errore: Il modello non ha restituito JSON valido. Output grezzo:\n{raw[:200]}")
        data = {"error": "Invalid JSON generated"}
        
    # 5. Salva l'output nella cartella output/
    output_dir = base_dir / 'output'
    output_dir.mkdir(exist_ok=True)
    out_file = output_dir / f'daily_roadmap_{target_date_str}.json'
    
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"Roadmap salvata con successo in: {out_file}")
    return data

if __name__ == "__main__":
    # Test script isolato
    test_date = "2025-01-09"
    test_file = f"C:/Users/Mauro/Documents/databento-data/glbx-mdp3-{test_date.replace('-', '')}.trades.csv"
    
    roadmap = generate_daily_roadmap(test_date, test_file)
    print("\n[RISULTATO ROADMAP]")
    print(json.dumps(roadmap, indent=2, ensure_ascii=False))
