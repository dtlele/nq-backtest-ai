import subprocess, sys, time, os

_AUTH_ERRORS = ('Authentication expired', 'notebooklm login', 'Redirected to', 'not authenticated')
_FALLBACK = '[NLM AUTH EXPIRED — run: python -m notebooklm login — using knowledge JSON only]'

# Lazy-init auth probe: None = not checked, True = expired, False = working
_auth_expired = None


def _check_auth_once(notebook_id: str) -> bool:
    """Probe NLM auth once. Returns True if expired."""
    global _auth_expired
    if _auth_expired is not None:
        return _auth_expired
    try:
        subprocess.run(
            [sys.executable, '-m', 'notebooklm', 'use', notebook_id],
            capture_output=True, text=True, timeout=30
        )
        result = subprocess.run(
            [sys.executable, '-m', 'notebooklm', 'ask', 'ping'],
            capture_output=True, text=True, timeout=30
        )
        combined = result.stdout + result.stderr
        _auth_expired = any(e in combined for e in _AUTH_ERRORS)
    except Exception:
        _auth_expired = True
    if _auth_expired:
        print("  [NLM] auth expired — skipping all NLM calls (use: python -m notebooklm login)")
    return _auth_expired


def nlm_use_notebook(notebook_id: str) -> None:
    """Switch active NLM notebook."""
    subprocess.run(
        [sys.executable, '-m', 'notebooklm', 'use', notebook_id],
        capture_output=True, text=True, timeout=60
    )

def nlm_ask(question: str, notebook_id: str, retry: int = 0) -> str:
    """Ask a question to a NLM notebook. Returns answer string.

    If authentication has expired, returns a descriptive fallback string
    instead of raising — the agent will still run using only its knowledge JSON.
    Re-authenticate by running: python -m notebooklm login
    """
    if os.environ.get("DISABLE_NLM") == "1":
        return "[NLM DISABLED for Audit Momentum]"

    if _check_auth_once(notebook_id):
        return _FALLBACK

    nlm_use_notebook(notebook_id)
    time.sleep(1)
    result = subprocess.run(
        [sys.executable, '-m', 'notebooklm', 'ask', question],
        capture_output=True, text=True, timeout=180
    )
    combined = result.stdout + result.stderr
    if any(e in combined for e in _AUTH_ERRORS):
        return _FALLBACK
    if result.returncode != 0 and retry < 2:
        time.sleep(5)
        return nlm_ask(question, notebook_id, retry + 1)
    return result.stdout.strip() or '[NLM: no response]'
