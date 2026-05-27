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

CACHE_FILE = Path(__file__).parent.parent.parent / "agent_memory" / "llm_cache.json"

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


def _cache_key(system_prompt: str, user_msg: str) -> str:
    """Cache key built from base system_prompt + user_msg only.
    Dynamic rules are intentionally EXCLUDED from the key so that
    minor rule updates don't bust the cache for identical market data.
    """
    raw = f"{system_prompt}\x00{user_msg}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
    override_file = Path(r"C:\Users\Mauro\Documents\nq-backtest\agent_memory\human_decisions.jsonl")
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


# ── Gemini backend ─────────────────────────────────────────────────────────────

# Session-level context cache: {system_prompt_hash -> cache_name}
_gemini_ctx_cache: dict = {}

def _get_or_create_gemini_cache(client, model: str, system_prompt: str) -> str:
    """
    Opt3: Gemini API-level Context Caching.
    Currently disabled because the system prompt is < 4096 tokens (minimum required by Gemini).
    """
    return ""


def _ask_gemini(system_prompt: str, user_msg: str) -> str:
    from google import genai
    from google.genai.errors import APIError
    import os
    import time
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set in .env")
        
    client = genai.Client(api_key=api_key)
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # Opt3: Try to use server-side context cache for the system prompt
    cache_name = _get_or_create_gemini_cache(client, model, system_prompt)
    
    max_retries = 8
    for attempt in range(max_retries):
        try:
            if cache_name:
                # Use the cached system prompt
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        {"role": "user", "parts": [{"text": user_msg}]}
                    ],
                    config={"cached_content": cache_name}
                )
            else:
                # Fallback: standard call with system+user merged
                response = client.models.generate_content(
                    model=model,
                    contents=[
                        {"role": "user", "parts": [{"text": f"System Guidelines:\n{system_prompt}\n\nTask:\n{user_msg}"}]}
                    ]
                )
            
            # Strip markdown code blocks if gemini returned them
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
                
            # Log token usage
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    in_tok = response.usage_metadata.prompt_token_count or 0
                    out_tok = response.usage_metadata.candidates_token_count or 0
                    log_file = Path(r"C:\Users\Mauro\Documents\nq-backtest\agent_memory\token_usage.log")
                    with open(log_file, "a") as f:
                        f.write(f"{in_tok},{out_tok}\n")
            except Exception as e:
                pass
                
            return text.strip()
            
        except APIError as e:
            # Handle transient errors (429, 503, 500, 504) with exponential backoff
            if e.code in (429, 503, 500, 504) and attempt < max_retries - 1:
                # If we get multiple 503s, stop retries after 4 attempts (attempt index 3)
                if e.code == 503 and attempt >= 3:
                    print(f"  [GEMINI API] 503 persisted after 4 attempts. Exiting retries.", flush=True)
                    return ""
                # Drop context cache after repeated 503/429 errors
                if e.code in (429, 503) and attempt >= 2 and cache_name:
                    print(f"  [GEMINI API] 503/429 persists. Dropping context cache for fallback.", flush=True)
                    cache_name = ""
                    
                sleep_sec = 2 ** (attempt + 1)
                # Cap sleep time to 30s
                if sleep_sec > 30:
                    sleep_sec = 30
                    
                print(f"  [GEMINI API] Transient error {e.code} ({e.message or 'No message'}). Retrying in {sleep_sec}s (attempt {attempt + 1}/{max_retries})...", flush=True)
                time.sleep(sleep_sec)
                continue
            else:
                print(f"  [GEMINI API] Fatal API error: {e}", flush=True)
                raise
        except Exception as e:
            # Catch other unexpected network issues
            if attempt < max_retries - 1:
                sleep_sec = 2 ** (attempt + 1)
                print(f"  [GEMINI API] Unexpected error: {e}. Retrying in {sleep_sec}s...", flush=True)
                time.sleep(sleep_sec)
                continue
            else:
                raise
                
    raise RuntimeError("Gemini API retries exhausted.")


# ── OpenRouter backend ─────────────────────────────────────────────────────────

def _ask_openrouter(system_prompt: str, user_msg: str) -> str:
    # Append educational context/suggestions to ensure prompt exceeds 4096 tokens for Cache Read
    import os
    from pathlib import Path
    try:
        padding_file = Path("C:/Users/Mauro/Documents/nq-backtest/knowledge/amt_glossary_padding.txt")
        if padding_file.exists():
            system_prompt += "\n\n" + padding_file.read_text(encoding="utf-8")
    except Exception:
        system_prompt += "\n\n" + ("PAD " * 4000)
    
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
    model = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    
    max_retries = 8
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                extra_headers={
                    "HTTP-Referer": "http://localhost:8000",
                    "X-Title": "AgentForge Backtester",
                }
            )
            
            try:
                usage = response.usage
                if usage:
                    in_tok = getattr(usage, "prompt_tokens", 0)
                    out_tok = getattr(usage, "completion_tokens", 0)
                    log_file = Path(r"C:\Users\Mauro\Documents\nq-backtest\agent_memory\token_usage.log")
                    with open(log_file, "a") as f:
                        f.write(f"OPENROUTER,{in_tok},{out_tok}\n")
            except Exception:
                pass
                
            text = response.choices[0].message.content.strip()
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
            use_cache: bool = True) -> str:
    """Send system+user prompt to the configured LLM and return the response.

    Provider is selected via LLM_PROVIDER env var (default: human).
    Cached responses are returned without calling the LLM.
    """
    # Load dynamic rules and inject into system_prompt
    dynamic_rules_file = Path(__file__).parent.parent.parent / 'knowledge' / 'dynamic_rules.json'
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
            print(f"  [DEBUG] Error injecting dynamic rules: {e}")

    key = _cache_key(system_prompt, user_msg)

    provider = _get_provider()
    print(f"  [DEBUG] llm_ask using provider: {provider}", flush=True)
    
    if use_cache:
        cache = _load_cache()
        if key in cache:
            return cache[key]

    if provider == "claude":
        response = _ask_claude(system_prompt, user_msg, timeout)
    elif provider == "gemini":
        response = _ask_gemini(system_prompt, user_msg)
    elif provider == "openrouter":
        response = _ask_openrouter(system_prompt, user_msg)
    elif provider == "human":
        response = _ask_human(system_prompt, user_msg)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use 'claude', 'gemini', 'openrouter', or 'human'.")

    if use_cache and response and provider != "human":
        cache = _load_cache()
        cache[key] = response
        _save_cache(cache)

    return response


# Backward compat alias
claude_ask = llm_ask
