"""
Thin wrapper around the `claude -p` CLI for non-interactive inference.
Uses the active Claude Code subscription -- no ANTHROPIC_API_KEY needed.

Response cache: identical prompts are served from disk, saving tokens and
ensuring deterministic replays during backtesting.
Cache file: agent_memory/llm_cache.json
"""
import hashlib
import json
import subprocess
import shutil
from pathlib import Path

CACHE_FILE = Path(__file__).parent.parent.parent / "agent_memory" / "llm_cache.json"


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _cache_key(system_prompt: str, user_msg: str) -> str:
    raw = f"{system_prompt}\x00{user_msg}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _claude_exe() -> str:
    """Resolve the claude executable path (handles Windows .cmd wrapper)."""
    for name in ("claude", "claude.cmd"):
        path = shutil.which(name)
        if path:
            return path
    raise FileNotFoundError("claude CLI not found in PATH -- is Claude Code installed?")


def claude_ask(system_prompt: str, user_msg: str, timeout: int = 120,
               use_cache: bool = True) -> str:
    """Send system+user prompt to Claude via CLI and return the response text.

    If use_cache=True (default) and an identical prompt was answered before,
    the cached response is returned without calling claude -p.
    """
    key = _cache_key(system_prompt, user_msg)

    if use_cache:
        cache = _load_cache()
        if key in cache:
            return cache[key]

    full_prompt = f"{system_prompt}\n\n---\n\n{user_msg}"
    result = subprocess.run(
        [_claude_exe(), "-p"],
        input=full_prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"claude -p failed (rc={result.returncode}): {result.stderr[:200]}"
        )

    response = result.stdout.strip()

    if use_cache and response:
        cache = _load_cache()
        cache[key] = response
        _save_cache(cache)

    return response
