"""
Estrae i blocchi di codice dalla risposta di Kimi K3 e crea i file src/v2/.
Usa SOLO il testo di Kimi K3 — nessuna modifica.
"""
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SOURCE = BASE_DIR / "output" / "kimi_k3_build_20260719_231537.md"

# Mappa header Kimi K3 -> path file reale
FILE_MAP = {
    "src/v2/config.py":       BASE_DIR / "src/v2/config.py",
    "src/v2/models.py":       BASE_DIR / "src/v2/models.py",
    "src/v2/state.py":        BASE_DIR / "src/v2/state.py",
    "src/v2/gex.py":          BASE_DIR / "src/v2/gex.py",
    "src/v2/detectors.py":    BASE_DIR / "src/v2/detectors.py",
    "src/v2/gates.py":        BASE_DIR / "src/v2/gates.py",
    "src/v2/risk.py":         BASE_DIR / "src/v2/risk.py",
    "src/v2/execution.py":    BASE_DIR / "src/v2/execution.py",
    "src/v2/prompt_fabio.py": BASE_DIR / "src/v2/prompt_fabio.py",
    "src/v2/policy_llm.py":   BASE_DIR / "src/v2/policy_llm.py",
    "src/v2/engine.py":       BASE_DIR / "src/v2/engine.py",
    "src/v2/analytics.py":    BASE_DIR / "src/v2/analytics.py",
    "src/v2/__init__.py":     BASE_DIR / "src/v2/__init__.py",
    "src/v2/walkforward.py":  BASE_DIR / "src/v2/walkforward.py",
    "scripts/v2/run_backtest_v2.py": BASE_DIR / "scripts/v2/run_backtest_v2.py",
    "tests/test_v2.py":       BASE_DIR / "tests/test_v2.py",
}

def extract_blocks(text: str) -> dict:
    """
    Cerca pattern: ### `path/to/file.py` seguito da ```python ... ```
    Restituisce dict path -> codice.
    """
    results = {}
    # Pattern: header con filename, poi blocco python
    pattern = re.compile(
        r"###\s+`([^`]+\.(?:py|json))`[^\n]*\n+```python\n(.*?)```",
        re.DOTALL
    )
    for m in pattern.finditer(text):
        filename = m.group(1).strip()
        code = m.group(2)
        results[filename] = code
        print(f"  Trovato: {filename} ({len(code):,} chars)")
    return results

def main():
    print("=" * 60)
    print("Estrazione codice Kimi K3 → src/v2/")
    print("=" * 60)

    text = SOURCE.read_text(encoding="utf-8", errors="replace")
    print(f"\nFile sorgente: {len(text):,} chars\n")

    blocks = extract_blocks(text)
    print(f"\nTotale blocchi trovati: {len(blocks)}\n")

    created = []
    skipped = []

    for filename, code in blocks.items():
        # Cerca il path corrispondente
        target = FILE_MAP.get(filename)
        if target is None:
            # prova match parziale
            for k, v in FILE_MAP.items():
                if filename.endswith(k.split("/")[-1]):
                    target = v
                    break

        if target is None:
            print(f"  SKIP (non mappato): {filename}")
            skipped.append(filename)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code, encoding="utf-8")
        print(f"  CREATO: {target.relative_to(BASE_DIR)} ({len(code):,} chars)")
        created.append(str(target.relative_to(BASE_DIR)))

    # Crea __init__.py vuoto per i package se mancante
    for pkg in [BASE_DIR / "src/v2", BASE_DIR / "scripts/v2", BASE_DIR / "tests"]:
        init = pkg / "__init__.py"
        if not init.exists():
            pkg.mkdir(parents=True, exist_ok=True)
            init.write_text("", encoding="utf-8")
            print(f"  CREATO: {init.relative_to(BASE_DIR)} (package init vuoto)")

    print(f"\n{'='*60}")
    print(f"Creati: {len(created)} file")
    if skipped:
        print(f"Saltati: {skipped}")
    print("\nFile creati:")
    for f in created:
        print(f"  {f}")

if __name__ == "__main__":
    main()
