#!/usr/bin/env python
"""
analyze_gdrive.py — Analizza video da Google Drive con MiniMax M3 via OpenRouter.

Uso:
  # Video pubblico (link condiviso)
  python scripts/analyze_gdrive.py "https://drive.google.com/file/d/FILE_ID/view"

  # Video privato (usa cookie del browser)
  python scripts/analyze_gdrive.py "https://drive.google.com/file/d/FILE_ID/view" --cookies-from-browser chrome

  # Con nome personalizzato
  python scripts/analyze_gdrive.py "URL" --name "fabio_lezione1" --chunk-minutes 10
"""
import os
import sys
import re
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).parent.parent.absolute()
sys.path.append(str(ROOT))

from src.agents.llm_client import llm_ask, _cache_key, _load_cache

DEFAULT_CHUNK_MINUTES = 10
SYSTEM_PROMPT_VIDEO = (
    "Sei un assistente AI esperto in analisi video di trading con visione di grafici in tempo reale. "
    "Analizza OGNI DETTAGLIO visibile e udibile nel video in modo ESAUSTIVO e APPROFONDITO. "
    "Per ogni segmento fornisci: "
    "(1) CHI PARLA e il suo ruolo/stile; "
    "(2) COSA MOSTRANO I GRAFICI: strumento, timeframe, prezzo, struttura di mercato, "
    "Volume Profile (POC/VAH/VAL/HVN/LVN), footprint/delta, livelli chiave, indicatori attivi; "
    "(3) OGNI TRADE OSSERVATO: direzione, entry precisa, ragionamento verbale, stop loss, target, "
    "gestione, esito; "
    "(4) OGNI CONCETTO TEORICO: definizione completa + come si applica operativamente; "
    "(5) INSIGHT PSICOLOGICI: come reagisce a errori/vincite/perdite; "
    "(6) DETTAGLI TECNICI: parametri, shortcut, pattern DOM, sequenze candele, big trades. "
    "Non omettere nulla. Essere prolissi e precisi e FONDAMENTALE."
)
SYSTEM_PROMPT_MERGE = (
    "Sei un analista di trading senior. Produci un documento MASTERCLASS COMPLETO ed ESAUSTIVO "
    "basato sulle analisi di tutte le sezioni del video. "
    "NON sintetizzare in modo eccessivo: mantieni TUTTI i dettagli. "
    "Ogni trade, ogni concetto, ogni regola operativa deve essere documentata completamente. "
    "Usa sezioni strutturate, tabelle, esempi numerici concreti."
)


def extract_gdrive_id(url: str) -> str:
    m = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)
    m = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if m:
        return m.group(1)
    return "gdrive_unknown"


def ffmpeg_path() -> str:
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except ImportError:
        pass
    import shutil
    return shutil.which("ffmpeg") or "ffmpeg"


def seconds_to_hms(sec: int) -> str:
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}"


def get_video_duration(url: str, cookies_browser: str = None) -> int:
    try:
        try:
            import static_ffmpeg
            static_ffmpeg.add_paths()
        except ImportError:
            pass
        import yt_dlp
        opts = {'quiet': True, 'no_warnings': True}
        if cookies_browser:
            opts['cookiesfrombrowser'] = (cookies_browser,)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return int(info.get('duration', 0))
    except Exception as e:
        print(f"[WARN] Durata non rilevata: {e}")
        return 0


def download_segment(url: str, output_dir: Path, file_id: str,
                     start_sec: int, end_sec: int,
                     cookies_browser: str = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename_base = f"gdrive_{file_id}_s{start_sec}_e{end_sec}"
    temp_template = str(output_dir / f"{filename_base}.%(ext)s")

    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
    except ImportError:
        pass

    start_str = seconds_to_hms(start_sec)
    end_str = seconds_to_hms(end_sec)
    print(f"[WAIT] Download {start_str} - {end_str}...")

    cmd = [
        "python", "-m", "yt_dlp",
        "--format", "worst[ext=mp4]/worst/best[height<=360]",
        "-o", temp_template,
        "--download-sections", f"*{start_str}-{end_str}",
        "--force-keyframes-at-cuts",
        "--quiet", "--no-warnings",
    ]
    if cookies_browser:
        cmd += ["--cookies-from-browser", cookies_browser]
    cmd.append(url)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Errore download:\n{result.stderr}")

    files = list(output_dir.glob(f"{filename_base}.*"))
    if not files:
        raise FileNotFoundError("Nessun file generato da yt-dlp.")

    downloaded = files[0]
    size_mb = downloaded.stat().st_size / (1024 * 1024)
    print(f"[OK] Scaricato: {downloaded.name} ({size_mb:.2f} MB)")
    return downloaded


def compress_segment(input_path: Path, target_mb: float = 14.0) -> Path:
    output_path = input_path.with_name(input_path.stem + "_comp.mp4")
    size_mb = input_path.stat().st_size / (1024 * 1024)

    if size_mb <= target_mb:
        print(f"[INFO] Gia piccolo ({size_mb:.2f} MB), skip compressione.")
        return input_path

    print(f"[WAIT] Compressione {size_mb:.2f} MB → 144p...")
    cmd = [
        ffmpeg_path(), "-y", "-i", str(input_path),
        "-vf", "scale=-2:144",
        "-vcodec", "libx264", "-crf", "35", "-preset", "fast",
        "-acodec", "aac", "-ar", "22050", "-b:a", "48k", "-ac", "1",
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WARN] Compressione fallita, uso originale.")
        return input_path

    try:
        input_path.unlink()
    except Exception:
        pass

    comp_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"[OK] Compresso: {output_path.name} ({comp_mb:.2f} MB)")
    return output_path


def analyze_chunk(url: str, tmp_dir: Path, file_id: str,
                  start_sec: int, end_sec: int, prompt: str,
                  cookies_browser: str = None,
                  force: bool = False, keep: bool = False) -> str:

    final_path = tmp_dir / f"gdrive_{file_id}_s{start_sec}_e{end_sec}_final.mp4"
    cache_key = _cache_key(SYSTEM_PROMPT_VIDEO, prompt, str(final_path))

    if not force:
        cache = _load_cache()
        if cache_key in cache:
            print(f"[CACHE] Hit chunk {seconds_to_hms(start_sec)}-{seconds_to_hms(end_sec)}")
            return cache[cache_key]

    downloaded = None
    try:
        downloaded = download_segment(url, tmp_dir, file_id, start_sec, end_sec, cookies_browser)
        downloaded = compress_segment(downloaded)

        if downloaded != final_path:
            if final_path.exists():
                final_path.unlink()
            downloaded.rename(final_path)
            downloaded = final_path

        print(f"[AI] Invio chunk a OpenRouter ({seconds_to_hms(start_sec)}-{seconds_to_hms(end_sec)})...")
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


def merge_analyses(chunks_text: list, original_prompt: str) -> str:
    if len(chunks_text) == 1:
        return chunks_text[0]

    combined = "\n\n---\n\n".join(
        [f"## Sezione {i+1}\n{text}" for i, text in enumerate(chunks_text)]
    )
    user_msg = (
        f"Domanda: {original_prompt}\n\n"
        f"Analisi complete di ogni sezione:\n\n{combined}\n\n"
        "Produci MASTERCLASS DOCUMENT con:\n"
        "1. OVERVIEW (trader, stile, mercati, piattaforme)\n"
        "2. OGNI CONCETTO (definizione + lettura grafico + regola operativa)\n"
        "3. OGNI TRADE (tabella + narrativa: entry/stop/target/esito/concetto applicato)\n"
        "4. REGOLE ESPLICITE (citate verbalmente)\n"
        "5. GESTIONE RISCHIO (sizing, stop, R/R)\n"
        "6. INSIGHT AVANZATI E PATTERN SOTTILI\n"
        "NON troncare. Massimo dettaglio."
    )
    print("[AI] Merge finale chunk...")
    return llm_ask(system_prompt=SYSTEM_PROMPT_MERGE, user_msg=user_msg, use_cache=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="URL Google Drive del video")
    parser.add_argument("--name", default=None, help="Nome per output (es. fabio_lezione1)")
    parser.add_argument("--prompt", default=(
        "Analizza il video in modo COMPLETO: chi parla, cosa mostra sui grafici, "
        "ogni trade con entry/stop/target/esito, ogni concetto con regola operativa, "
        "ogni insight psicologico e tecnico."
    ))
    parser.add_argument("--model", default="minimax/minimax-m3")
    parser.add_argument("--chunk-minutes", type=int, default=DEFAULT_CHUNK_MINUTES)
    parser.add_argument("--cookies-from-browser", dest="cookies_browser", default=None,
                        help="Browser per auth: chrome, edge, firefox (video privati)")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if "OPENROUTER_API_KEY" not in os.environ:
        print("[ERROR] OPENROUTER_API_KEY non impostata nel .env")
        sys.exit(1)

    os.environ["LLM_PROVIDER"] = "openrouter"
    os.environ["OPENROUTER_MODEL"] = args.model

    file_id = extract_gdrive_id(args.url)
    video_name = args.name or file_id
    tmp_dir = ROOT / "tmp_data"

    print(f"[INFO] Google Drive File ID: {file_id}")
    print("[INFO] Recupero durata...")
    duration = get_video_duration(args.url, args.cookies_browser)
    if duration == 0:
        print("[WARN] Durata non rilevata. Inserisci manualmente con --end HH:MM:SS")
        print("[INFO] Fallback: analizzo i primi 60 minuti")
        duration = 3600

    print(f"[INFO] Durata: {seconds_to_hms(duration)}")

    chunk_seconds = args.chunk_minutes * 60
    chunks = []
    t = 0
    while t < duration:
        chunks.append((t, min(t + chunk_seconds, duration)))
        t += chunk_seconds

    print(f"[INFO] {len(chunks)} chunk da {args.chunk_minutes} min")

    results = []
    for i, (cs, ce) in enumerate(chunks):
        print(f"\n[CHUNK {i+1}/{len(chunks)}] {seconds_to_hms(cs)} - {seconds_to_hms(ce)}")
        try:
            result = analyze_chunk(
                url=args.url, tmp_dir=tmp_dir, file_id=file_id,
                start_sec=cs, end_sec=ce, prompt=args.prompt,
                cookies_browser=args.cookies_browser,
                force=args.force, keep=args.keep
            )
            results.append(result)
            print(f"[OK] Chunk {i+1} completato.")
        except Exception as e:
            print(f"[ERROR] Chunk {i+1} fallito: {e}. Continuo...")
            results.append(f"[CHUNK {i+1} NON ANALIZZATO: {e}]")

    final = merge_analyses(results, args.prompt)

    output_dir = ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"analysis_{video_name}.md"
    out_file.write_text(
        f"# Analisi: {video_name}\n\n**Fonte**: {args.url}\n\n---\n\n{final}",
        encoding="utf-8"
    )
    print(f"\n[OK] Analisi salvata: {out_file}")
    print(f"[OK] {len(final)} caratteri, {len(final.splitlines())} righe")

    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print("\n" + "=" * 60)
    print(f"ANALISI COMPLETA: {video_name}")
    print("=" * 60)
    print(final[:3000] + "\n...[vedi file per il resto]")
    print("=" * 60)


if __name__ == "__main__":
    main()
