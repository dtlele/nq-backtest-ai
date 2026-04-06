import subprocess, sys, time

def nlm_use_notebook(notebook_id: str) -> None:
    """Switch active NLM notebook."""
    subprocess.run(
        [sys.executable, '-m', 'notebooklm', 'use', notebook_id],
        capture_output=True, text=True, timeout=60
    )

def nlm_ask(question: str, notebook_id: str, retry: int = 0) -> str:
    """Ask a question to a NLM notebook. Returns answer string."""
    # Switch notebook first
    nlm_use_notebook(notebook_id)
    time.sleep(1)
    result = subprocess.run(
        [sys.executable, '-m', 'notebooklm', 'ask', question],
        capture_output=True, text=True, timeout=180
    )
    if 'Authentication expired' in result.stderr or 'notebooklm login' in result.stderr:
        raise RuntimeError("[AUTH EXPIRED] Run 'python -m notebooklm login' then retry.")
    if result.returncode != 0 and retry < 2:
        time.sleep(5)
        return nlm_ask(question, notebook_id, retry + 1)
    return result.stdout.strip()
