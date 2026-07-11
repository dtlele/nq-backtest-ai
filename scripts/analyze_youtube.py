#!/usr/bin/env python
"""
analyze_youtube.py — Analizza video YouTube con MiniMax M3 via OpenRouter.

Uso:
  python scripts/analyze_youtube.py URL [--start HH:MM:SS] [--end HH:MM:SS]
                                        [--chunk-minutes N] [--prompt "..."]
                                        [--model minimax/minimax-m3]
                                        [--keep] [--force]

Note:
  - Il video viene scaricato in bassa risoluzione (formato worst[ext=mp4]) per
    ridurre le dimensioni senza intaccare la qualità minima necessaria.
  - Per segmenti > CHUNK_MINUTES minuti, il video viene automaticamente
    suddiviso in chunk, ciascun chunk analizzato separatamente, e i risultati
    vengono uniti in un'unica analisi finale testuale.
  - La risposta per ogni chunk viene salvata in cache: chiamate successive con
    gli stessi parametri restituiscono immediatamente il risultato senza
    riscaricare o richiamare l'API.
"""
import os
import sys
import argparse
import urllib.parse
from pathlib import Path
import subprocess
import yt_dlp

# Aggiunge la cartella root al path per importare src
ROOT = Path(__file__).parent.parent.absolute()
sys.path.append(str(ROOT))

from src.agents.llm_client import llm_ask, _cache_key, _load_cache

# ── Costanti ──────────────────────────────────────────────────────────────────

DEFAULT_CHUNK_MINUTES = 10        # Lunghezza massima di ogni chunk in minuti
SYSTEM_PROMPT_VIDEO = (
    "Sei un assistente AI esperto in analisi video di trading con visione di grafici in tempo reale. "
    "Analizza OGNI DETTAGLIO visibile e udibile nel video in modo ESAUSTIVO e APPROFONDITO. "
    "Per ogni segmento fornisci: "
    "(1) CHI PARLA e il suo ruolo/stile; "
    "(2) COSA MOSTRANO I GRAFICI — strumento, timeframe, prezzo corrente, struttura del mercato, "
    "Volume Profile (POC/VAH/VAL/HVN/LVN), footprint/delta visibile, livelli chiave disegnati, "
    "indicatori attivi (VWAP, Bookmap, DOM); "
    "(3) OGNI TRADE OSSERVATO — direzione, entry precisa, ragionamento verbale, stop loss, target, "
    "gestione durante il trade, esito se visibile; "
    "(4) OGNI CONCETTO TEORICO SPIEGATO — con definizione completa e come si applica operativamente; "
    "(5) INSIGHT PSICOLOGICI E COMPORTAMENTALI — come reagiscono a errori, a trade vincenti/perdenti; "
    "(6) QUALSIASI DETTAGLIO TECNICO SPECIFICO — parametri di configurazione, scorciatoie usate, "
    "pattern sul DOM, sequenze di candele, big trades visibili. "
    "Non omettere nulla. Essere prolissi e precisi e' FONDAMENTALE."
)
SYSTEM_PROMPT_MERGE = (
    "Sei un analista di trading senior che deve produrre un documento di riferimento COMPLETO ed ESAUSTIVO "
    "basato sulle analisi di tutte le sezioni di un video di trading. "
    "Il documento finale deve essere una MASTERCLASS DOCUMENT che un trader puo usare come guida operativa completa. "
    "NON sintetizzare in modo eccessivo: mantieni TUTTI i dettagli importanti di ogni sezione. "
    "Ogni trade, ogni concetto, ogni regola operativa deve essere documentata in modo completo. "
    "Usa sezioni ben strutturate, tabelle, esempi numerici concreti dove disponibili. "
    "Il documento deve essere sufficientemente lungo e dettagliato da catturare il valore INTEGRALE del video."
)


# ── Utility ───────────────────────────────────────────────────────────────────

def get_yt_video_id(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname in ('youtu.be', 'www.youtu.be'):
        return parsed.path[1:]
    if parsed.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        query = urllib.parse.parse_qs(parsed.query)
        return query.get('v', ['unknown'])[0]
    return "unknown"

def parse_time_to_seconds(time_str: str) -> int:
    if not time_str:
        return 0
    if ":" in time_str:
        parts = list(map(int, time_str.split(':')))
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return int(time_str)

def seconds_to_hms(sec: int) -> str:
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"

def get_video_duration(url: str) -> int:
    try:
        try:
            import static_ffmpeg
            static_ffmpeg.add_paths()
        except ImportError:
            pass
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return int(info.get('duration', 0))
    except Exception as e:
        print(f"[WARN] Impossibile recuperare la durata del video: {e}")
        return 0

def ffmpeg_path() -> str:
    """Restituisce il percorso di ffmpeg (static_ffmpeg o system)."""
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except ImportError:
        pass
    import shutil
    return shutil.which("ffmpeg") or "ffmpeg"


# ── Download e Compressione ───────────────────────────────────────────────────

def download_segment(url: str, output_dir: Path, video_id: str,
                     start_sec: int, end_sec: int) -> Path:
    """Scarica una sezione del video in bassa risoluzione."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename_base = f"yt_{video_id}_s{start_sec}_e{end_sec}"
    
    # Cerca se esiste già il file segmentato
    files = list(output_dir.glob(f"{filename_base}.*"))
    if files:
        downloaded = files[0]
        size_mb = downloaded.stat().st_size / (1024 * 1024)
        print(f"[OK] Segmento esistente: {downloaded.name} ({size_mb:.2f} MB)")
        return downloaded

    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except ImportError:
        pass

    start_str = seconds_to_hms(start_sec)
    end_str = seconds_to_hms(end_sec)
    
    # Prova prima il download parziale nativo
    print(f"[WAIT] Download segmento {start_str} - {end_str}...")
    temp_template = str(output_dir / f"{filename_base}.%(ext)s")
    cmd = [
        "python", "-m", "yt_dlp",
        "--format", "worst[ext=mp4]/worst",
        "-o", temp_template,
        "--download-sections", f"*{start_str}-{end_str}",
        "--quiet", "--no-warnings",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        files = list(output_dir.glob(f"{filename_base}.*"))
        if files:
            downloaded = files[0]
            size_mb = downloaded.stat().st_size / (1024 * 1024)
            print(f"[OK] Segmento scaricato: {downloaded.name} ({size_mb:.2f} MB)")
            return downloaded

    # Fallback se fallisce (es. crash di ffmpeg/access violation)
    print(f"[WARN] Download-sections fallito o crash ffmpeg. Provo a scaricare il video completo e tagliarlo...")
    full_template = str(output_dir / f"yt_{video_id}_full.%(ext)s")
    
    full_files = list(output_dir.glob(f"yt_{video_id}_full.*"))
    if not full_files:
        print(f"[WAIT] Download video completo in bassa risoluzione...")
        cmd_full = [
            "python", "-m", "yt_dlp",
            "--format", "worst[ext=mp4]/worst",
            "-o", full_template,
            "--quiet", "--no-warnings",
            url
        ]
        result_full = subprocess.run(cmd_full, capture_output=True, text=True)
        if result_full.returncode != 0:
            raise RuntimeError(f"Errore nel download del video completo:\n{result_full.stderr}")
        full_files = list(output_dir.glob(f"yt_{video_id}_full.*"))
        if not full_files:
            raise FileNotFoundError("Impossibile scaricare il video completo.")

    full_video = full_files[0]
    out_sliced = output_dir / f"{filename_base}.mp4"
    
    print(f"[WAIT] Taglio segmento locale {start_str} - {end_str} con ffmpeg...")
    cmd_slice = [
        ffmpeg_path(), "-y",
        "-ss", start_str,
        "-to", end_str,
        "-i", str(full_video),
        "-c", "copy",
        str(out_sliced)
    ]
    result_slice = subprocess.run(cmd_slice, capture_output=True, text=True)
    if result_slice.returncode != 0:
        raise RuntimeError(f"Errore ffmpeg nel taglio del segmento:\n{result_slice.stderr}")
        
    size_mb = out_sliced.stat().st_size / (1024 * 1024)
    print(f"[OK] Segmento tagliato localmente: {out_sliced.name} ({size_mb:.2f} MB)")
    return out_sliced

def compress_segment(input_path: Path, target_mb: float = 14.0) -> Path:
    """
    Comprime il video SOLO sulla risoluzione (144p), mantenendo il FPS originale.
    Questo approccio e' compatibile con il backend di MiniMax (che rifiuta FPS < 1).
    Il target e' di circa 14 MB per non superare i limiti di payload di OpenRouter.
    """
    output_path = input_path.with_name(input_path.stem + "_comp.mp4")
    size_mb = input_path.stat().st_size / (1024 * 1024)

    if size_mb <= target_mb:
        print(f"[INFO] Segmento gia' piccolo ({size_mb:.2f} MB), compressione non necessaria.")
        return input_path

    print(f"[WAIT] Compressione ({size_mb:.2f} MB -> target {target_mb:.0f} MB, 144p, FPS invariato)...")

    cmd = [
        ffmpeg_path(), "-y",
        "-i", str(input_path),
        # Manteniamo FPS originale, riduciamo solo la risoluzione a 144p
        "-vf", "scale=-2:144",
        "-vcodec", "libx264",
        "-crf", "35",
        "-preset", "fast",
        "-acodec", "aac",
        "-ar", "22050",
        "-b:a", "48k",
        "-ac", "1",
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WARN] Compressione fallita. Uso il file originale.\n{result.stderr[-300:]}")
        return input_path

    try:
        input_path.unlink()
    except Exception:
        pass

    comp_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"[OK] Compressione completata: {output_path.name} ({comp_mb:.2f} MB)")
    return output_path


# ── Analisi Chunk ─────────────────────────────────────────────────────────────

def stable_video_path(tmp_dir: Path, video_id: str, start_sec: int, end_sec: int) -> Path:
    return tmp_dir / f"yt_{video_id}_s{start_sec}_e{end_sec}_final.mp4"

def analyze_chunk(url: str, tmp_dir: Path, video_id: str,
                  start_sec: int, end_sec: int, prompt: str, model: str,
                  force: bool = False, keep: bool = False) -> str:
    """Analizza un chunk di video. Usa la cache se disponibile."""

    final_path = stable_video_path(tmp_dir, video_id, start_sec, end_sec)

    # Controlla cache preventiva
    cache_key = _cache_key(SYSTEM_PROMPT_VIDEO, prompt, str(final_path), provider="openrouter")
    if not force:
        cache = _load_cache()
        if cache_key in cache:
            print(f"[CACHE] Hit per il chunk {seconds_to_hms(start_sec)}-{seconds_to_hms(end_sec)}")
            return cache[cache_key]

    downloaded = None
    try:
        downloaded = download_segment(url, tmp_dir, video_id, start_sec, end_sec)

        # Compressione SOLO sulla risoluzione, FPS invariato
        downloaded = compress_segment(downloaded)

        # Rinomina al percorso stabile (usato come chiave cache)
        if downloaded != final_path:
            if final_path.exists():
                final_path.unlink()
            downloaded.rename(final_path)
            downloaded = final_path

        print(f"[AI] Invio chunk {seconds_to_hms(start_sec)}-{seconds_to_hms(end_sec)} a OpenRouter...")
        response = llm_ask(
            system_prompt=SYSTEM_PROMPT_VIDEO,
            user_msg=prompt,
            use_cache=True,
            video_path=str(downloaded)
        )
        return response

    finally:
        if downloaded and downloaded.exists() and not keep:
            try:
                downloaded.unlink()
            except Exception:
                pass


# ── Merge Finale ──────────────────────────────────────────────────────────────

def merge_analyses(chunks_text: list[str], original_prompt: str) -> str:
    """Unisce le analisi dei chunk in un unico testo coerente."""
    if len(chunks_text) == 1:
        return chunks_text[0]

    combined = "\n\n---\n\n".join(
        [f"## Sezione {i+1}\n{text}" for i, text in enumerate(chunks_text)]
    )
    user_msg = (
        f"Domanda originale: {original_prompt}\n\n"
        f"Di seguito le analisi COMPLETE di ogni sezione del video (in ordine cronologico):\n\n{combined}\n\n"
        "ISTRUZIONI PER LA SINTESI FINALE:\n"
        "Produci un documento MASTERCLASS completo con le seguenti sezioni OBBLIGATORIE e DETTAGLIATE:\n"
        "1. OVERVIEW GENERALE (chi sono i trader, piattaforme usate, mercati trattati, filosofia generale)\n"
        "2. STRUMENTI E CONFIGURAZIONE (ogni piattaforma con dettagli di setup, parametri, layout)\n"
        "3. CONCETTI DI ORDER FLOW INSEGNATI (OGNI concetto con: definizione completa, come si legge sul grafico, "
        "   quando entra in gioco, esempi concreti dal video, regola operativa derivante)\n"
        "4. METODOLOGIA OPERATIVA COMPLETA (il loro processo passo-passo dall'analisi macro all'esecuzione)\n"
        "5. OGNI TRADE OSSERVATO NEL VIDEO (tabella completa + narrativa dettagliata per ogni trade: "
        "   timestamp, strumento, bias, entry, stop, target, gestione, esito, concetto applicato, commenti verbali)\n"
        "6. GESTIONE DEL RISCHIO (regole esplicite, sizing, R/R usati, psicologia del rischio)\n"
        "7. ERRORI E POST-MORTEM (se discussi: cosa non ha funzionato e perche)\n"
        "8. REGOLE E PRINCIPI ESPLICITI (ogni regola enunciata verbalmente dai trader, citazione diretta se possibile)\n"
        "9. INSIGHT AVANZATI E CONCETTI SOTTILI (osservazioni meno ovvie, sfumature operative)\n"
        "10. COSA MANCA / COSA IMPARARE ANCORA (lacune identificate, prossimi passi suggeriti)\n"
        "NON troncare, NON essere conciso. Ogni sezione deve essere COMPLETA e RICCA di dettagli."
    )
    print("[AI] Creazione sintesi finale ESTESA dei chunk...")
    return llm_ask(
        system_prompt=SYSTEM_PROMPT_MERGE,
        user_msg=user_msg,
        use_cache=True
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Analizza una sezione di un video YouTube con MiniMax M3 via OpenRouter.")
    parser.add_argument("url", type=str, help="URL del video di YouTube")
    parser.add_argument("--prompt", type=str,
                        default="Fornisci un'analisi dettagliata del video: chi parla, cosa mostrano i grafici e le decisioni operative prese.",
                        help="Domanda da porre al modello")
    parser.add_argument("--model", type=str, default="minimax/minimax-m3",
                        help="Modello OpenRouter (default: minimax/minimax-m3)")
    parser.add_argument("--start", type=str, default="00:00",
                        help="Tempo di inizio (HH:MM:SS o MM:SS o secondi)")
    parser.add_argument("--end", type=str, default=None,
                        help="Tempo di fine (HH:MM:SS o MM:SS o secondi)")
    parser.add_argument("--chunk-minutes", type=int, default=DEFAULT_CHUNK_MINUTES,
                        help=f"Lunghezza di ogni chunk in minuti (default: {DEFAULT_CHUNK_MINUTES})")
    parser.add_argument("--keep", action="store_true", help="Mantieni i file video temporanei")
    parser.add_argument("--force", action="store_true", help="Ignora la cache e riesegui le chiamate API")
    args = parser.parse_args()

    if "OPENROUTER_API_KEY" not in os.environ:
        print("[ERROR] OPENROUTER_API_KEY non impostata nel .env o nelle variabili d'ambiente.")
        sys.exit(1)

    os.environ["LLM_PROVIDER"] = "openrouter"
    os.environ["OPENROUTER_MODEL"] = args.model

    video_id = get_yt_video_id(args.url)
    tmp_dir = ROOT / "tmp_data"

    start_sec = parse_time_to_seconds(args.start)
    end_sec = parse_time_to_seconds(args.end) if args.end else None

    # Se non c'è end, recupera la durata del video
    if end_sec is None:
        print("[INFO] Recupero durata del video...")
        duration = get_video_duration(args.url)
        end_sec = duration if duration > 0 else start_sec + 600
        print(f"[INFO] Durata totale: {seconds_to_hms(duration)}. Analisi fino a {seconds_to_hms(end_sec)}.")

    total_seconds = end_sec - start_sec
    chunk_seconds = args.chunk_minutes * 60

    # Costruisce la lista dei chunk
    chunks = []
    t = start_sec
    while t < end_sec:
        chunk_end = min(t + chunk_seconds, end_sec)
        chunks.append((t, chunk_end))
        t = chunk_end

    print(f"\n[INFO] Segmento: {seconds_to_hms(start_sec)} - {seconds_to_hms(end_sec)} "
          f"({total_seconds//60} min, {len(chunks)} chunk da {args.chunk_minutes} min)")

    # Analizza ogni chunk
    results = []
    for i, (cs, ce) in enumerate(chunks):
        print(f"\n[CHUNK {i+1}/{len(chunks)}] {seconds_to_hms(cs)} - {seconds_to_hms(ce)}")
        result = analyze_chunk(
            url=args.url,
            tmp_dir=tmp_dir,
            video_id=video_id,
            start_sec=cs,
            end_sec=ce,
            prompt=args.prompt,
            model=args.model,
            force=args.force,
            keep=args.keep
        )
        results.append(result)
        print(f"[OK] Chunk {i+1} completato.")

    # Merge finale
    final = merge_analyses(results, args.prompt)

    # Salva sempre su file (evita UnicodeEncodeError su Windows cp1252)
    output_dir = ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    vid_id = get_yt_video_id(args.url)
    out_file = output_dir / f"analysis_{vid_id}.md"
    out_file.write_text(
        f"# Analisi Completa: {args.url}\n\n"
        f"**Segmento**: {args.start} — {args.end or 'fine'}\n\n---\n\n{final}",
        encoding="utf-8"
    )
    print(f"\n[OK] Analisi salvata in: {out_file}")
    print(f"[OK] Lunghezza: {len(final)} caratteri, {len(final.splitlines())} righe")

    # Stampa su stdout con UTF-8 forzato (evita crash cp1252)
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print("\n" + "=" * 60)
    print("ANALISI FINALE DI MINIMAX M3:")
    print("=" * 60)
    print(final)
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
