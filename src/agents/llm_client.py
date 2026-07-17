"""
Unified LLM client — supports Claude CLI (default) and Human-in-the-loop.

Provider selection:
  - Set LLM_PROVIDER=human (default) or LLM_PROVIDER=claude in .env
  - Claude uses `claude -p` CLI (requires Claude Code installation)
  - Human mode uses a prompt-based or mailbox-based manual entry.

Response cache: identical prompts are served from disk.
Cache file: agent_memory/llm_cache.json
"""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

CACHE_FILE        = Path(__file__).parent.parent.parent / "agent_memory" / "llm_cache.json"
CACHE_SNAPSHOT_DIR = Path(__file__).parent.parent.parent / "agent_memory" / "cache_snapshots"
DYNAMIC_RULES_FILE = Path(__file__).parent.parent.parent / "knowledge" / "dynamic_rules.json"

# ── Provider config ──────────────────────────────────────────────────────────

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

def _get_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "human").lower()

# ── Cache ────────────────────────────────────────────────────────────────────

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


def _rules_hash() -> str:
    """SHA256 of current dynamic_rules.json content — used to version the cache."""
    if DYNAMIC_RULES_FILE.exists():
        try:
            content = DYNAMIC_RULES_FILE.read_bytes()
            return hashlib.sha256(content).hexdigest()[:12]
        except OSError:
            pass
    return "norules"


def _cache_key(system_prompt: str, user_msg: str, video_path: str = None, provider: str = None, model: str = None) -> str:
    """Cache key built from system_prompt (includes dynamic rules) + user_msg.
    The rules hash is embedded so entries become stale automatically when rules change.
    """
    video_info = f"\x00{video_path}" if video_path else ""
    provider_info = f"\x00{provider}" if provider else ""
    model_info = f"\x00{model}" if model else ""
    raw = f"{system_prompt}\x00{user_msg}{video_info}{provider_info}{model_info}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()



def snapshot_cache() -> str:
    """Save a dated snapshot of the current cache keyed by rules version.
    Returns the snapshot filename, or empty string if cache is empty.
    Call this after a full backtest run to persist a stable reference.
    """
    cache = _load_cache()
    if not cache:
        return ""
    CACHE_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    import datetime
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    rules_v = _rules_hash()
    fname = CACHE_SNAPSHOT_DIR / f"cache_{stamp}_rules_{rules_v}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump({"rules_hash": rules_v, "entries": cache}, f, ensure_ascii=False)
    print(f"  [CACHE] Snapshot saved: {fname.name} ({len(cache)} entries)", flush=True)
    return str(fname)


def restore_cache_snapshot(snapshot_path: str) -> int:
    """Restore a cache snapshot into the active cache (merges, does not replace).
    Returns number of entries restored.
    """
    p = Path(snapshot_path)
    if not p.exists():
        print(f"  [CACHE] Snapshot not found: {snapshot_path}", flush=True)
        return 0
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    entries = data.get("entries", data)  # support both formats
    cache = _load_cache()
    before = len(cache)
    cache.update(entries)
    _save_cache(cache)
    restored = len(cache) - before
    print(f"  [CACHE] Restored {restored} new entries from snapshot (total: {len(cache)})", flush=True)
    return restored


def list_cache_snapshots() -> list:
    """List available snapshots ordered newest first."""
    if not CACHE_SNAPSHOT_DIR.exists():
        return []
    snaps = sorted(CACHE_SNAPSHOT_DIR.glob("cache_*.json"), reverse=True)
    return [str(s) for s in snaps]


# ── Claude backend ───────────────────────────────────────────────────────────

def _claude_exe() -> str:
    for name in ("claude", "claude.cmd"):
        path = shutil.which(name)
        if path:
            return path
    raise FileNotFoundError("claude CLI not found in PATH -- is Claude Code installed?")


def _ask_claude(system_prompt: str, user_msg: str, timeout: int = 120) -> str:
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
    return result.stdout.strip()


# ── Human / Chat Agent backend ───────────────────────────────────────────────

def _ask_human(system_prompt: str, user_msg: str) -> str:
    import sys
    import json
    from pathlib import Path
    
    # --- DECISION OVERRIDE LOGIC ---
    # Check if a manual decision already exists in the override file
    override_file = Path(r"C:\Users\Mauro\Documents\nq-backtest-clean\agent_memory\human_decisions.jsonl")
    key = _cache_key(system_prompt, user_msg)
    
    if override_file.exists():
        try:
            with open(override_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    data = json.loads(line)
                    print(f"  [DEBUG] comparing: {data.get('key')} == {key}", flush=True)
                    if data.get("key") == key:
                        # Use the pre-recorded decision
                        print(f"  [HUMAN OVERRIDE] Using pre-recorded decision for key: {key[:8]}...", flush=True)
                        return json.dumps(data["decision"])
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [DEBUG] override read error: {e}", flush=True)
            pass

    print("\n" + "="*80, flush=True)
    print(" >>> CHAT AGENT IN THE LOOP: DECISION REQUIRED <<<", flush=True)
    print(f" --- KEY: {key} ---", flush=True)
    print("="*80, flush=True)
    
    # Save last request for easier automation by AI peers
    last_req_file = Path(__file__).parent.parent.parent / "agent_memory" / "last_human_request.json"
    last_req_file.parent.mkdir(parents=True, exist_ok=True)
    with open(last_req_file, "w", encoding="utf-8") as f:
        json.dump({"key": key, "system_prompt": system_prompt, "user_msg": user_msg}, f, indent=2)

    print("--- CONTEXT ---", flush=True)
    print(user_msg, flush=True)
    print("="*80, flush=True)
    
    # --- NEW ASYNCHRONOUS MAILBOX SYSTEM ---
    mailbox_dir = Path(__file__).parent.parent.parent / "agent_memory" / "mailbox"
    mailbox_dir.mkdir(parents=True, exist_ok=True)
    
    # Save a dedicated request file for the external agent/human to find easily
    req_file = mailbox_dir / f"request_{key}.json"
    with open(req_file, "w", encoding="utf-8") as f:
        json.dump({"key": key, "system_prompt": system_prompt, "user_msg": user_msg}, f, indent=2)

    print(f"  [MAILBOX] Awaiting decision: agent_memory/mailbox/decision_{key[:8]}...", flush=True)
    
    import time
    while True:
        decision_file = mailbox_dir / f"decision_{key}.json"
        if decision_file.exists():
            try:
                with open(decision_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Support both {"decision": ...} and direct decision objects
                decision = data.get("decision") if isinstance(data, dict) and "decision" in data else data
                
                print(f"  [MAILBOX] Decision received for key: {key[:8]}", flush=True)
                
                # Archive to override file for persistence
                override_file.parent.mkdir(parents=True, exist_ok=True)
                with open(override_file, "a", encoding="utf-8") as f_ov:
                    f_ov.write(json.dumps({"key": key, "decision": decision}) + "\n")
                
                # Cleanup: remove request and decision files
                decision_file.unlink()
                if req_file.exists(): req_file.unlink()
                
                return json.dumps(decision)
            except (json.JSONDecodeError, OSError, PermissionError):
                pass # Wait if file is being written or locked

        # Non-blocking check for interactive input (TTY only)
        if sys.stdin.isatty():
            try:
                import select
                if select.select([sys.stdin], [], [], 0.0)[0]:
                    response = sys.stdin.readline().strip()
                    if response:
                        parsed = json.loads(response)
                        override_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(override_file, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"key": key, "decision": parsed}) + "\n")
                        if req_file.exists(): req_file.unlink()
                        return response
            except (json.JSONDecodeError, EOFError):
                pass
        
        time.sleep(2) # Silent polling


# Gemini backend removed - only OpenRouter, Claude, and Human are supported



# ── OpenRouter backend ─────────────────────────────────────────────────────────

def _ask_openrouter(system_prompt: str, user_msg: str, video_path: str = None, model: str = None) -> str:
    import os
    from pathlib import Path
    import time
    try:
        from openai import OpenAI
        import httpx
    except ImportError:
        raise ImportError("OpenRouter backend requires openai. Run: pip install openai httpx")
        
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set in .env")
        
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        http_client=httpx.Client(timeout=120.0)
    )
    if not model:
        model = os.environ.get("OPENROUTER_MODEL", "z-ai/glm-5.2")
    
    # Format messages based on whether video_path is provided
    if video_path and os.path.exists(video_path):
        import base64
        import mimetypes
        try:
            mime_type, _ = mimetypes.guess_type(video_path)
            if not mime_type:
                mime_type = "video/mp4"
            with open(video_path, "rb") as vf:
                video_data = base64.b64encode(vf.read()).decode("utf-8")
            
            user_content = [
                {"type": "text", "text": user_msg},
                {
                    "type": "video_url",
                    "video_url": {
                        "url": f"data:{mime_type};base64,{video_data}"
                    }
                }
            ]
        except Exception as e:
            print(f"  [OPENROUTER] Error encoding video {video_path}: {e}. Falling back to text-only.")
            user_content = user_msg
    else:
        user_content = user_msg

    max_retries = 8
    for attempt in range(max_retries):
        try:
            extra_body_params = {}
            if model == "z-ai/glm-5.2":
                # Inject reasoning effort: high to drop CoT latency under 5 seconds (supported level)
                extra_body_params["reasoning"] = {
                    "effort": "high",
                    "exclude": False
                }

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=8192,
                extra_headers={
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "AgentForge Backtester",
                },
                extra_body=extra_body_params
            )
            
            try:
                usage = response.usage
                if usage:
                    in_tok = getattr(usage, "prompt_tokens", 0)
                    out_tok = getattr(usage, "completion_tokens", 0)
                    log_file = Path(r"C:\Users\Mauro\Documents\nq-backtest-clean\agent_memory\token_usage.log")
                    with open(log_file, "a") as f:
                        f.write(f"OPENROUTER,{model},{in_tok},{out_tok}\n")
            except Exception:
                pass
            
            # Guard: response or choices can be None (MiniMax M3 intermittent issue)
            if response is None or not getattr(response, 'choices', None):
                raise ValueError(f"Model returned empty response (choices=None). Will retry.")
            choice = response.choices[0]
            text = getattr(choice.message, 'content', None)
            if text is None:
                # Try alternative fields (some models use 'reasoning' or tool_calls)
                raw_msg = choice.message
                refusal = getattr(raw_msg, 'refusal', None)
                finish_reason = getattr(choice, 'finish_reason', 'unknown')
                print(f"  [WARN] content=None from model. finish_reason={finish_reason}, refusal={refusal}")
                # Try to extract from model_extra if present
                extra = getattr(raw_msg, 'model_extra', {}) or {}
                text = extra.get('content') or extra.get('text') or refusal
                if not text:
                    raise ValueError(f"Model returned None content (finish_reason={finish_reason}). Possible video format issue.")
                
            text = text.strip()
            if text.startswith("```json"): text = text[7:]
            elif text.startswith("```"): text = text[3:]
            if text.endswith("```"): text = text[:-3]
            
            return text.strip()
            
        except Exception as e:
            if attempt < max_retries - 1:
                sleep_sec = min(30, 2 ** (attempt + 1))
                print(f"  [OPENROUTER API] Error: {e}. Retrying in {sleep_sec}s...", flush=True)
                time.sleep(sleep_sec)
                continue
            else:
                raise RuntimeError(f"OpenRouter API retries exhausted: {e}")


# ── Public API ───────────────────────────────────────────────────────────────

def llm_ask(system_prompt: str, user_msg: str, timeout: int = 120,
            use_cache: bool = True, video_path: str = None,
            provider: str = None, model: str = None) -> str:
    key = _cache_key(system_prompt, user_msg, video_path, provider, model)

    if provider is None:
        provider = _get_provider()
    print(f"  [DEBUG] llm_ask using provider: {provider} (model: {model})", flush=True)
    
    # Check global NO_CACHE environment variable override
    import os
    if os.environ.get("NO_CACHE") == "1":
        use_cache = False

    if use_cache:
        cache = _load_cache()
        if key in cache:
            print(f"  [CACHE HIT] Key: {key[:8]}...", flush=True)
            return cache[key]
        else:
            print(f"  [CACHE MISS] Key: {key[:8]}...", flush=True)

    if provider == "claude":
        response = _ask_claude(system_prompt, user_msg, timeout)
    elif provider == "openrouter":
        response = _ask_openrouter(system_prompt, user_msg, video_path, model=model)
    elif provider == "human":
        response = _ask_human(system_prompt, user_msg)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use 'claude', 'openrouter', or 'human'.")

    if use_cache and response and provider != "human":
        cache = _load_cache()
        cache[key] = response
        _save_cache(cache)
        # Auto-snapshot every 500 new entries to preserve work
        if len(cache) % 500 == 0 and len(cache) > 0:
            snapshot_cache()

    return response


# Backward compat alias
claude_ask = llm_ask

