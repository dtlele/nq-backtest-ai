#!/usr/bin/env python
"""
video_context_helper.py — Helper per preparare il contesto del sistema NQ
===========================================================================
Carica master strategy, strategie correnti, dynamic rules, manuali e prompt
degli agenti per costruire un system prompt 'informato' da dare all'LLM
quando analizza un video di trading su YouTube.

Uso:
    from helpers.video_context_helper import load_trading_context, build_system_prompt
    ctx = load_trading_context()
    system = build_system_prompt(ctx, task="strategy_extraction")
"""
import json
import re
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).parent.parent

# ── I/O helpers ─────────────────────────────────────────────────────────────

def _read_json(rel_path: str) -> dict:
    p = ROOT / rel_path
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _read_text(rel_path: str, max_chars: int = 6_000) -> str:
    p = ROOT / rel_path
    if p.exists():
        txt = p.read_text(encoding="utf-8", errors="ignore")
        return txt[:max_chars]
    return ""


def _load_agent_prompts(max_per_file: int = 900, max_files: int = 4) -> str:
    """Estrae i system prompt / docstring dai file agente per inquadrare il linguaggio operativo."""
    parts = []
    agents_dir = ROOT / "src" / "agents"
    if not agents_dir.exists():
        return ""

    skip = {"llm_client.py", "video_context_helper.py", "video_analyzer.py"}
    py_files = sorted(agents_dir.glob("*.py"))
    for f in py_files:
        if f.name in skip:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            matches = re.findall(r'["\']{3}(.*?)["\']{3}', content, re.DOTALL)
            for m in matches:
                if len(m) > 120:
                    parts.append(f"# {f.name}\n{m[:max_per_file].strip()}\n")
                    break
        except Exception:
            pass
        if len(parts) >= max_files:
            break
    return "\n".join(parts)


# ── Caricamento contesto completo ───────────────────────────────────────────

def load_trading_context() -> Dict:
    """Ritorna un dizionario con tutto il contesto rilevante del sistema NQ."""
    return {
        "master_strategy": _read_json("master_strategy_v3.json"),
        "strategies": _read_json("knowledge/strategies.json"),
        "dynamic_rules": _read_json("knowledge/dynamic_rules.json"),
        "amt_mechanics": _read_json("knowledge/amt_mechanics.json"),
        "trading_manual": _read_text("knowledge/master_trading_manual.md", 6_000),
        "video_pipeline": _read_text("knowledge/video_analysis_pipeline.md", 3_000),
        "agent_prompts": _load_agent_prompts(),
    }


# ── Costruzione system prompt ────────────────────────────────────────────────

def build_system_prompt(ctx: Dict, task: str = "strategy_extraction") -> str:
    """
    Costruisce il system prompt arricchito con il contesto del sistema.
    
    task:
        - "strategy_extraction" : estrae una strategia strutturata JSON
        - "knowledge_gap"       : identifica gap vs sistema corrente
        - "default"             : solo contesto + istruzione generica
    """
    master = json.dumps(ctx.get("master_strategy", {}), indent=2, ensure_ascii=False)
    strategies = json.dumps(ctx.get("strategies", {}), indent=2, ensure_ascii=False)
    rules = json.dumps(ctx.get("dynamic_rules", {}), indent=2, ensure_ascii=False)
    mechanics = json.dumps(ctx.get("amt_mechanics", {}), indent=2, ensure_ascii=False)
    manual = ctx.get("trading_manual", "")
    video_pipe = ctx.get("video_pipeline", "")
    agent_prompts = ctx.get("agent_prompts", "")

    base = (
        "Sei un Analista Strategico Senior di Trading alimentato da AI. "
        "Devi analizzare contenuti video educativi di trading e produrre output "
        "strutturati, confrontandoli criticamente con il sistema operativo già in uso.\n\n"
        "## CONTESTO ATTUALE DEL SISTEMA NQ\n\n"
        f"### Master Strategy V3:\n{master}\n\n"
        f"### Strategie Codificate:\n{strategies}\n\n"
        f"### Regole Dinamiche (Backtest-Validated):\n{rules}\n\n"
        f"### Meccaniche AMT:\n{mechanics}\n\n"
        f"### Manuale Trading (estratto):\n{manual}\n\n"
        f"### Pipeline Video Esistente:\n{video_pipe}\n\n"
        f"### Linguaggio degli Agenti Correnti:\n{agent_prompts}\n\n"
    )

    if task == "strategy_extraction":
        base += (
            "\n---\n\n"
            "## ISTRUZIONI PER L'ANALISI VIDEO\n\n"
            "Analizza il contenuto fornito (trascrizione, descrizione, screenshot) e produci:\n"
            "1. **STRATEGIA ESTRATTA** – nome, strumento, timeframe, direzione, condizioni di entry, "
            "stop loss, take profit (esatto o formula), RR approssimativo.\n"
            "2. **FILTRI DI MERCATO** – regime target (trending/rotational/balance), indicatori chiave, "
            "time gate (es. 9:30–10:00 ET).\n"
            "3. **GUARDRAIL & MONEY MANAGEMENT** – max trade/giorno, max perdite consecutive, sizing, "
            "commissioni/slippage se menzionati.\n"
            "4. **NOTE CRITICHE** – ogni avvertimento, limite psicologico o meccanico menzionato dal presenter.\n"
            "5. **CONFRONTO CON SISTEMA ESISTENTE** – cosa è nuovo, cosa è in conflitto, cosa va integrato.\n\n"
            "Il JSON di output DEVE seguire questo schema (inglese keys, italiano values se utile):\n"
            '{\n'
            '  "strategy_name": string,\n'
            '  "instrument": string,\n'
            '  "timeframe": string,\n'
            '  "direction": "long|short|both",\n'
            '  "entry_conditions": [string],\n'
            '  "stop_loss": string,\n'
            '  "take_profit": string,\n'
            '  "risk_reward_approx": string,\n'
            '  "regime_filter": string,\n'
            '  "indicators": [string],\n'
            '  "guardrails": [string],\n'
            '  "critical_notes": [string],\n'
            '  "gaps_vs_system": [string],\n'
            '  "suggested_updates": [string],\n'
            '  "confidence_extraction": "alta|media|bassa",\n'
            '  "source_url": string\n'
            '}\n\n'
            "Se mancano dati usa stringhe vuote, mai inventare numeri non citati."
        )
    elif task == "knowledge_gap":
        base += (
            "\n---\n\n"
            "## GAP ANALYSIS\n\n"
            "Identifica concetti, regole o tecniche presenti nel video ma ASSENTI nel contesto sopra. "
            "Per ogni gap indica: gravità (alta/media/bassa), dove inserirlo (dynamic_rules,knowledge,prompt_agent), "
            "e una proposta di test/backtest."
        )
    else:
        base += (
            "\n---\n\n"
            "Usa il contenuto del video per rispondere alla richiesta nel modo più strutturato possibile, "
            "sempre facendo riferimento al contesto del sistema NQ quando pertinente."
        )

    return base
