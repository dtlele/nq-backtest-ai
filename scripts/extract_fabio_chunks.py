import sys
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.append(str(ROOT))

from src.agents.llm_client import _cache_key, _load_cache
from scripts.analyze_youtube import SYSTEM_PROMPT_VIDEO, seconds_to_hms

def main():
    video_id = "DyS79Eb92Ug"
    duration = 8500  # 2h21m40s = 8500s
    chunk_seconds = 600
    prompt = "Analizza TUTTO in dettaglio esaustivo: chi parla, cosa mostra sui grafici, ogni trade con entry/stop/target/esito, ogni concetto teorico con regola operativa completa, ogni esempio numerico, ogni insight psicologico e tecnico. Non omettere nulla."
    
    # Inietta le dynamic rules come fa llm_ask
    system_prompt = SYSTEM_PROMPT_VIDEO
    dynamic_rules_file = ROOT / 'knowledge' / 'dynamic_rules.json'
    if dynamic_rules_file.exists():
        try:
            with open(dynamic_rules_file, encoding='utf-8') as f:
                rules_data = json.load(f)
                rules_list = rules_data.get("dynamic_rules", [])
                if rules_list:
                    corrections_block = "\n\n## ACTIVE LIVE CORRECTIONS (DYNAMIC RULES FROM PRIOR SESSIONS)\n"
                    corrections_block += "You MUST strictly follow these dynamic heuristics generated from recent post-mortem audits to avoid repeating past errors:\n"
                    for rule in rules_list:
                        corrections_block += f"- [{rule.get('rule_id', 'RULE')}] (Topic: {rule.get('topic', 'General')}) {rule.get('description', '')} -> ACTION: {rule.get('action', 'Follow carefully')}\n"
                    system_prompt = system_prompt + corrections_block
        except Exception as e:
            print(f"Error injecting dynamic rules: {e}")

    # Costruisci la lista dei chunk
    chunks = []
    t = 0
    while t < duration:
        chunk_end = min(t + chunk_seconds, duration)
        chunks.append((t, chunk_end))
        t = chunk_end

    output_dir = ROOT / "output" / "chunks_DyS79Eb92Ug"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cache = _load_cache()
    print(f"Loaded cache with {len(cache)} entries.")
    
    found_count = 0
    for i, (cs, ce) in enumerate(chunks):
        final_path = ROOT / "tmp_data" / f"yt_{video_id}_s{cs}_e{ce}_final.mp4"
        
        # Prova le varie combinazioni di provider/model per la chiave cache
        key = _cache_key(system_prompt, prompt, str(final_path), provider="openrouter", model=None)
        
        if key in cache:
            chunk_content = cache[key]
            out_file = output_dir / f"chunk_{i+1:02d}_{seconds_to_hms(cs).replace(':', '-')}_{seconds_to_hms(ce).replace(':', '-')}.md"
            out_file.write_text(chunk_content, encoding="utf-8")
            print(f"[OK] Chunk {i+1} trovato e scritto: {out_file.name}")
            found_count += 1
        else:
            print(f"[MISS] Chunk {i+1} ({seconds_to_hms(cs)}-{seconds_to_hms(ce)}) non trovato in cache.")
            
    print(f"Estrazione completata: {found_count}/{len(chunks)} chunk salvati in {output_dir}")

if __name__ == "__main__":
    main()
