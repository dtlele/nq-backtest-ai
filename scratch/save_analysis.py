"""Recupera la sintesi finale dalla cache e la salva in un file markdown."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.append(str(ROOT))

from src.agents.llm_client import llm_ask, _cache_key, _load_cache

SYSTEM_PROMPT_MERGE = (
    "Sei un assistente AI esperto in analisi di trading. "
    "Hai ricevuto le analisi di sezioni consecutive di uno stesso video. "
    "Produci una sintesi coerente, dettagliata e ben strutturata di tutto il contenuto."
)

# Ricostruisce il merge_user_msg come fa analyze_youtube.py
video_id = "xUyqIjCfZzg"
original_prompt = ("Analizza questo segmento del video di live trading con Fabio Valentini e "
                   "Carmine Rosato. Descrivi: chi parla, cosa mostrano i grafici (Jigsaw/footprint/"
                   "order flow), i trade presi con entry/exit/ragionamento, i concetti di orderflow "
                   "spiegati, e qualsiasi insight operativo rilevante.")

SYSTEM_PROMPT_VIDEO = (
    "Sei un assistente AI esperto in analisi video di trading. "
    "Analizza dettagliatamente tutto quello che vedi e senti nel video: "
    "chi parla, cosa mostrano i grafici, le decisioni operative, i concetti discussi."
)

# Carica tutti i chunk dalla cache
cache = _load_cache()
tmp_dir = ROOT / "tmp_data"

chunks_text = []
chunk_params = [
    (0, 600), (600, 1200), (1200, 1800), (1800, 2400), (2400, 3000),
    (3000, 3600), (3600, 4200), (4200, 4800), (4800, 5400), (5400, 6000),
    (6000, 6600), (6600, 7200), (7200, 7800), (7800, 8400), (8400, 9000),
    (9000, 9600), (9600, 10200), (10200, 10800), (10800, 11400), (11400, 12000),
    (12000, 12600), (12600, 13200), (13200, 13777)
]

print(f"Caricamento {len(chunk_params)} chunk dalla cache...")
for i, (s, e) in enumerate(chunk_params):
    # nome file stabile come usato dallo script
    comp_suffix = "_comp" if True else ""
    stable = tmp_dir / f"yt_{video_id}_s{s}_e{e}_final.mp4"
    key = _cache_key(SYSTEM_PROMPT_VIDEO, original_prompt, str(stable))
    if key in cache:
        chunks_text.append(cache[key])
        print(f"  [OK] Chunk {i+1}/23 ({s//60}:{s%60:02d}-{e//60}:{e%60:02d})")
    else:
        print(f"  [MISS] Chunk {i+1}/23 NON trovato in cache!")

print(f"\n{len(chunks_text)}/{len(chunk_params)} chunk trovati.")

# Recupera la sintesi finale dalla cache
combined = "\n\n---\n\n".join(
    [f"## Sezione {i+1}\n{text}" for i, text in enumerate(chunks_text)]
)
user_msg = (
    f"Domanda originale dell'utente: {original_prompt}\n\n"
    f"Di seguito le analisi di ciascuna sezione del video:\n\n{combined}\n\n"
    f"Produci ora una sintesi finale completa e ben strutturata."
)
merge_key = _cache_key(SYSTEM_PROMPT_MERGE, user_msg)
if merge_key in cache:
    final = cache[merge_key]
    print("[OK] Sintesi finale trovata in cache!")
else:
    print("[INFO] Sintesi non ancora in cache, la genero ora...")
    final = llm_ask(system_prompt=SYSTEM_PROMPT_MERGE, user_msg=user_msg, use_cache=True)

# Salva su file
output_file = ROOT / "output" / "fabio_carmine_full_analysis.md"
output_file.parent.mkdir(parents=True, exist_ok=True)
output_file.write_text(
    f"# Analisi Completa: Trading LIVE con Fabio Valentini & Carmine Rosato\n\n"
    f"**Video:** https://www.youtube.com/watch?v=xUyqIjCfZzg\n\n"
    f"---\n\n{final}",
    encoding="utf-8"
)
print(f"\n[OK] Analisi salvata in: {output_file}")
print(f"Lunghezza: {len(final)} caratteri")
