#!/usr/bin/env python
"""
extract_video_knowledge.py

Legge la sintesi di un video analizzato e usa LLM per estrarre:
1. Concetti formativi insegnati
2. Trade live osservati
3. Gap di conoscenza vs sistema corrente
4. Suggerimenti per aggiornare dynamic_rules e prompt

Output: knowledge/video_knowledge_gaps_<id>.md + knowledge/video_trades_log_<id>.md
"""
import os, sys, re, argparse
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.append(str(ROOT))
os.environ.setdefault("LLM_PROVIDER", "openrouter")
os.environ.setdefault("OPENROUTER_MODEL", "minimax/minimax-m3")

from src.agents.llm_client import llm_ask

SYSTEM = (
    "Sei un esperto analista di trading che studia video educativi e sessioni live. "
    "Estrai conoscenza strutturata, azionabile e confrontala con sistemi esistenti."
)

def load_analysis(analysis_file: Path) -> str:
    if analysis_file.exists():
        return analysis_file.read_text(encoding="utf-8")
    # Fallback to default chunk-based merge if requested default and it doesn't exist
    if "fabio_carmine_full_analysis.md" in str(analysis_file):
        chunks = sorted((ROOT / "output" / "chunks").glob("chunk_*.md"))
        if chunks:
            return "\n\n---\n\n".join([c.read_text(encoding="utf-8") for c in chunks])
    raise FileNotFoundError(f"Analysis file not found: {analysis_file}")

def load_agent_prompts() -> str:
    parts = []
    for f in sorted((ROOT / "src" / "agents").glob("*.py"))[:5]:
        txt = f.read_text(encoding="utf-8", errors="ignore")
        matches = re.findall(r'"""[^"]{50,}"""', txt)
        if matches:
            parts.append(f"## {f.name}\n" + "\n".join(matches[:2]))
    return "\n\n".join(parts)

def extract(analysis_file: Path, video_id: str, title: str):
    print(f"[INFO] Caricamento analisi da: {analysis_file}")
    analysis = load_analysis(analysis_file)
    print(f"[INFO] {len(analysis)} chars")

    # 1. Concetti
    print("[AI] Estrazione concetti formativi...")
    r1 = llm_ask(SYSTEM, (
        f"Dall analisi seguente del video '{title}', estrai in markdown strutturato:\n"
        "1. CONCETTI CHIAVE con definizione operazionale e come si legge sul grafico\n"
        "2. REGOLE OPERATIVE esplicite enunciate dai trader\n"
        "3. SETUP con trigger, entry, stop, target\n"
        "4. STRUMENTI (piattaforme e configurazione)\n\n"
        f"ANALISI:\n{analysis[:8000]}"
    ), use_cache=True)

    # 2. Trade live
    print("[AI] Estrazione trade live...")
    r2 = llm_ask(SYSTEM, (
        f"Dall analisi del video '{title}', elenca tutti i TRADE LIVE osservati.\n"
        "Per ognuno: timestamp approssimativo, strumento, direzione, contesto, entry, stop, target, esito, concetto applicato.\n"
        "Formato: tabella markdown + narrativa per i trade piu significativi.\n\n"
        f"ANALISI:\n{analysis[:8000]}"
    ), use_cache=True)

    # 3. Gap vs sistema
    print("[AI] Gap analysis vs sistema corrente...")
    prompts = load_agent_prompts()
    r3 = llm_ask(SYSTEM, (
        "Hai due input:\n\n"
        f"A) CONCETTI DAL VIDEO:\n{r1[:3500]}\n\n"
        f"B) PROMPT CORRENTI DEL SISTEMA:\n{prompts[:2500]}\n\n"
        "Identifica:\n"
        "1. Concetti del video NON presenti nel sistema corrente\n"
        "2. Regole operative che potrebbero migliorare il sistema\n"
        "3. Suggerimenti concreti per aggiornare prompt e dynamic_rules (con priorita ALTA/MEDIA/BASSA)\n"
        "4. Cosa manca ancora da imparare (suggerisci prossimi video da cercare)"
    ), use_cache=True)

    # Salva
    kdir = ROOT / "knowledge"
    kdir.mkdir(exist_ok=True)
    slug = video_id.replace("/", "_")

    gf = kdir / f"video_knowledge_gaps_{slug}.md"
    gf.write_text(
        f"# Knowledge Gaps: {title}\n\n**Video**: {video_id}\n\n---\n\n"
        f"## Concetti Estratti\n\n{r1}\n\n---\n\n"
        f"## Gap vs Sistema Corrente\n\n{r3}",
        encoding="utf-8"
    )
    print(f"[OK] {gf}")

    tf = kdir / f"video_trades_log_{slug}.md"
    tf.write_text(
        f"# Trade Log: {title}\n\n**Video**: {video_id}\n\n---\n\n{r2}",
        encoding="utf-8"
    )
    print(f"[OK] {tf}")

    print("\n=== ANTEPRIMA GAP ANALYSIS ===")
    print(r3[:2000].encode("ascii", "replace").decode())

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis-file", default="output/fabio_carmine_full_analysis.md", help="Path to analysis file")
    ap.add_argument("--video-id", default="xUyqIjCfZzg")
    ap.add_argument("--title", default="Live Trading con Fabio Valentini e Carmine Rosato")
    args = ap.parse_args()
    
    analysis_path = ROOT / args.analysis_file if not Path(args.analysis_file).is_absolute() else Path(args.analysis_file)
    extract(analysis_path, args.video_id, args.title)
