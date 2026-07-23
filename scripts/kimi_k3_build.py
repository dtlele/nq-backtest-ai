"""
Kimi K3 — NQ Backtest System: Analisi e Redesign Completo
==========================================================
Invia tutto il codebase + knowledge a Kimi K3 via OpenRouter.
Kimi K3 analizza e propone il sistema v2.0. Noi implementiamo esattamente quello che dice.

Uso:
    python scripts/kimi_k3_build.py

Output:
    output/kimi_k3_build_TIMESTAMP.md
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY",
    "REDACTED_USE_ENV_VAR"  # era una key di test, ora solo env var
)
KIMI_MODEL = "moonshotai/kimi-k3"
MAX_FILE_SIZE = 40_000  # 40KB per file — Kimi K3 ha contesto molto grande


# ── File da allegare ─────────────────────────────────────────────────────────
CONTEXT_FILES = {
    # Analisi precedente di Kimi K3 (già fatta)
    "output/kimi_k3_analysis_20260719_214545.md": "ANALISI PRECEDENTE — diagnosi bug già completata",

    # Codice esistente
    "src/__init__.py": "Config globale e dataclass",
    "src/backtest_runner.py": "Backtest engine principale",
    "src/candidate_detector.py": "Rilevamento candidati",
    "src/trade_simulator.py": "Simulatore trade",
    "src/risk_manager.py": "Risk management",
    "src/volume_profile.py": "Volume Profile",
    "src/session_context.py": "Contesto sessione",
    "src/signal_context.py": "Contesto segnale",
    "src/consensus.py": "Consensus Fabio+Andrea",
    "src/gex_manager.py": "GEX manager",
    "src/agents/fabio_agent.py": "FabioAgent — prompt attuale",
    "src/agents/andrea_agent.py": "AndreaAgent",
    "src/agents/llm_client.py": "LLM client",
    "src/agents/topic_router.py": "Topic router",

    # FONTE VERIFICATA: regole Fabio con citazioni dalle lezioni originali
    "knowledge/trader_lessons_graph/rule_fabio_aplus_setup.md":                        "[FABIO] A+ setup",
    "knowledge/trader_lessons_graph/rule_fabio_trend_vs_mean_reversion_model.md":      "[FABIO] Trend vs Mean Reversion — i due modelli",
    "knowledge/trader_lessons_graph/rule_fabio_failed_auction_is_the_setup.md":        "[FABIO] Failed Auction",
    "knowledge/trader_lessons_graph/rule_fabio_entry_mechanics.md":                    "[FABIO] Entry mechanics",
    "knowledge/trader_lessons_graph/rule_fabio_avoid_times.md":                        "[FABIO] Timing avoidance",
    "knowledge/trader_lessons_graph/rule_fabio_ib_definition.md":                      "[FABIO] IVB definition",
    "knowledge/trader_lessons_graph/rule_fabio_ivb_15_vs_30_minutes.md":               "[FABIO] IVB 15 vs 30 minuti",
    "knowledge/trader_lessons_graph/rule_fabio_ib_breakout_rules.md":                  "[FABIO] IB breakout rules",
    "knowledge/trader_lessons_graph/rule_fabio_ib_extension_targets.md":               "[FABIO] IB extension targets",
    "knowledge/trader_lessons_graph/rule_fabio_ib_bias.md":                            "[FABIO] IB bias",
    "knowledge/trader_lessons_graph/rule_fabio_ivb_protection_level.md":               "[FABIO] IVB protection level",
    "knowledge/trader_lessons_graph/rule_fabio_second_drive.md":                       "[FABIO] Second Drive",
    "knowledge/trader_lessons_graph/rule_fabio_trend_day_second_drive_confirmation.md":"[FABIO] Second drive su trend day",
    "knowledge/trader_lessons_graph/rule_fabio_squeeze_definition.md":                 "[FABIO] Squeeze definition",
    "knowledge/trader_lessons_graph/rule_fabio_squeeze_entry_trigger.md":              "[FABIO] Squeeze entry trigger",
    "knowledge/trader_lessons_graph/rule_fabio_squeeze_vs_failed_auction.md":          "[FABIO] Squeeze vs Failed Auction",
    "knowledge/trader_lessons_graph/rule_fabio_squeeze_vs_ivb_priority_balance.md":    "[FABIO] Squeeze vs IVB su balance day",
    "knowledge/trader_lessons_graph/rule_fabio_big_trades_filter.md":                  "[FABIO] Big trades filter",
    "knowledge/trader_lessons_graph/rule_fabio_participation_baseline.md":             "[FABIO] Participation baseline",
    "knowledge/trader_lessons_graph/rule_fabio_footprint_delta.md":                    "[FABIO] Footprint delta",
    "knowledge/trader_lessons_graph/rule_fabio_cvd_as_leading_indicator.md":           "[FABIO] CVD",
    "knowledge/trader_lessons_graph/rule_fabio_cvd_in_simplified_model.md":            "[FABIO] CVD modello semplificato",
    "knowledge/trader_lessons_graph/rule_fabio_trapped_buyers.md":                     "[FABIO] Trapped buyers",
    "knowledge/trader_lessons_graph/rule_fabio_trapped_sellers.md":                    "[FABIO] Trapped sellers",
    "knowledge/trader_lessons_graph/rule_fabio_punches_to_wall.md":                    "[FABIO] Punches to wall",
    "knowledge/trader_lessons_graph/rule_fabio_hvn_big_wall_rules.md":                 "[FABIO] HVN e wall rules",
    "knowledge/trader_lessons_graph/rule_fabio_effort_vs_result.md":                   "[FABIO] Effort vs result",
    "knowledge/trader_lessons_graph/rule_fabio_coherence_of_information.md":           "[FABIO] Coherence of information",
    "knowledge/trader_lessons_graph/rule_fabio_acceptance_definition_exact.md":        "[FABIO] Acceptance definition",
    "knowledge/trader_lessons_graph/rule_fabio_pre_explosion_pattern.md":              "[FABIO] Pre-explosion pattern",
    "knowledge/trader_lessons_graph/rule_fabio_repeated_level_test.md":                "[FABIO] Repeated level test",
    "knowledge/trader_lessons_graph/rule_fabio_stop_placement.md":                     "[FABIO] Stop placement",
    "knowledge/trader_lessons_graph/rule_fabio_target_selection_hierarchy.md":         "[FABIO] Target selection",
    "knowledge/trader_lessons_graph/rule_fabio_partial_exits.md":                      "[FABIO] Partial exits",
    "knowledge/trader_lessons_graph/rule_fabio_trailing_stop.md":                      "[FABIO] Trailing stop",
    "knowledge/trader_lessons_graph/rule_fabio_breakeven_rules.md":                    "[FABIO] Breakeven",
    "knowledge/trader_lessons_graph/rule_fabio_risk_per_trade.md":                     "[FABIO] Risk per trade",
    "knowledge/trader_lessons_graph/rule_fabio_max_daily_loss.md":                     "[FABIO] Max daily loss",
    "knowledge/trader_lessons_graph/rule_fabio_position_building.md":                  "[FABIO] Position building",
    "knowledge/trader_lessons_graph/rule_fabio_multi_timeframe.md":                    "[FABIO] Multi timeframe",
    "knowledge/trader_lessons_graph/rule_fabio_choppy_day_identification.md":          "[FABIO] Choppy day",
    "knowledge/trader_lessons_graph/rule_fabio_balance_vs_failed_auction.md":          "[FABIO] Balance vs failed auction",
    "knowledge/trader_lessons_graph/rule_fabio_balance_day_exceptions.md":             "[FABIO] Balance day exceptions",
    "knowledge/trader_lessons_graph/rule_fabio_counter_trend_rules.md":                "[FABIO] Counter-trend rules",
    "knowledge/trader_lessons_graph/rule_fabio_counter_trend_on_trend_day.md":         "[FABIO] Counter-trend su trend day",
    "knowledge/trader_lessons_graph/rule_fabio_conflict_resolution_pingpong.md":       "[FABIO] Conflict resolution",
    "knowledge/trader_lessons_graph/rule_fabio_session_schedule.md":                   "[FABIO] Session schedule",
    "knowledge/trader_lessons_graph/rule_fabio_setup_time_cutoff.md":                  "[FABIO] Setup time cutoff",
    "knowledge/trader_lessons_graph/rule_fabio_statistical_levels.md":                 "[FABIO] Statistical levels",
    "knowledge/trader_lessons_graph/rule_fabio_win_rate_by_setup.md":                  "[FABIO] Win rate by setup",
    "knowledge/trader_lessons_graph/rule_fabio_vp_session_scope.md":                   "[FABIO] VP session scope",
    "knowledge/trader_lessons_graph/rule_fabio_composite_vs_session_vp.md":            "[FABIO] Composite vs session VP",
    "knowledge/trader_lessons_graph/rule_fabio_vp_includes_overnight.md":              "[FABIO] VP includes overnight",
    "knowledge/trader_lessons_graph/rule_fabio_pre_market_levels_usage.md":            "[FABIO] Pre-market levels",
    "knowledge/trader_lessons_graph/rule_fabio_losing_trade_anatomy.md":               "[FABIO] Losing trade anatomy",
    "knowledge/trader_lessons_graph/rule_fabio_confidence_40_60_zone.md":              "[FABIO] Confidence 40-60 zone",
    "knowledge/trader_lessons_graph/rule_fabio_ivb_breakout_vs_false_balance_apr30.md":"[FABIO] Case study IVB vs false balance",

    # Framework AMT generale
    "knowledge/master_trading_manual.md": "Master Trading Manual (framework AMT)",

    # GEX data schema
    "src/gex_manager.py": "GEX manager attuale",
}


# ── Il prompt — minimalista, lascia decidere Kimi K3 ─────────────────────────
BUILD_PROMPT = """
Ti invio l'intero codebase di un sistema di backtest per NQ futures e tutta la knowledge base del trader Fabio Valentini.

Ho due richieste:

**1. Analisi critica**
Leggi tutto il codice e tutti i file `rule_fabio_*.md`. Dimmi:
- Cosa non va (bug, lookahead bias, errori di causalità nel simulatore)
- Dove il codice NON implementa quello che Fabio insegna davvero
- Quali regole nel prompt LLM attuale sono state inventate da LLM precedenti e non rispecchiano i file verificati
- Cosa manca completamente (setup non implementati, dati non usati)

**2. Sistema v2.0 completo**
Proponi e scrivi il sistema v2.0. Sei libero di scegliere tu:
- L'architettura
- I moduli
- Come strutturare il prompt per Fabio (basandoti SOLO sui file rule_fabio_*.md, non sul codice attuale)
- Come gestire GEX/Gamma come filtro e modificatore
- Come eliminare tutti i bias causali
- Come validare i risultati

Scrivi codice Python reale e funzionante, non pseudocodice.
Decidi tu ogni scelta architetturale — non chiedere conferma.

**Contesto importante:**
- Mercato: NQ futures, sessione NY, conto FundedNext 50k ($2.500 max DD)
- Dati: barre 1min con footprint bid/ask, CVD, big trades filtrati
- GEX: disponibile in data/gex_data.json (regime, gamma flip, call wall, put wall)
- Il sistema attuale ha un Profit Factor stimato di 4.62 ma probabilmente overfitting senza walk-forward
"""


# ── Funzioni ──────────────────────────────────────────────────────────────────
def read_file_safe(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        if len(content) > MAX_FILE_SIZE:
            content = content[:MAX_FILE_SIZE] + f"\n\n[... TRONCATO: {len(content)} chars totali ...]"
        return content
    except Exception as e:
        return f"[ERRORE LETTURA: {e}]"


def build_full_prompt(base_dir: Path) -> str:
    parts = [BUILD_PROMPT]
    parts.append("\n\n---\n\n# CODEBASE E KNOWLEDGE ALLEGATI\n\n")

    for rel_path, description in CONTEXT_FILES.items():
        full_path = base_dir / rel_path
        if not full_path.exists():
            parts.append(f"\n## {rel_path}\n*[FILE NON TROVATO]*\n")
            continue
        content = read_file_safe(full_path)
        ext = full_path.suffix.lower().lstrip(".")
        lang = {"py": "python", "json": "json", "md": "markdown"}.get(ext, "text")
        parts.append(f"\n## {rel_path}\n_{description}_\n\n```{lang}\n{content}\n```\n")

    return "\n".join(parts)


def call_kimi_k3(prompt: str, output_path: Path) -> None:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/nq-backtest",
        "X-Title": "NQ Backtest Redesign",
    }

    size = len(prompt)
    print(f"Prompt: {size:,} caratteri (~{size//4:,} token stimati)")
    print(f"Modello: {KIMI_MODEL}")
    print(f"Output: {output_path}")
    print(f"\nAttenzione: risposta attesa in 10-25 minuti.\n{'='*60}\n")

    # Salva prompt raw per debug
    (output_path.parent / "kimi_k3_last_prompt.txt").write_text(prompt, encoding="utf-8")

    payload = {
        "model": KIMI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 64000,
        "temperature": 0.1,  # bassa — vogliamo codice preciso, non creativo
        "stream": True,
    }

    full_response = ""
    start = time.time()

    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=1800) as resp:
            resp.raise_for_status()
            print("Connessione ok. Streaming risposta...\n")
            for line in resp.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    text = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if text:
                        print(text, end="", flush=True)
                        full_response += text
                except json.JSONDecodeError:
                    pass
    except requests.exceptions.Timeout:
        print("\n[TIMEOUT] Salvando risposta parziale...")
    except requests.exceptions.RequestException as e:
        print(f"\n[ERRORE] {e}")
        raise

    elapsed = time.time() - start
    print(f"\n\n{'='*60}")
    print(f"Completato in {elapsed:.0f}s | {len(full_response):,} caratteri di risposta")

    ts_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = (
        f"# Kimi K3 — NQ Backtest Redesign\n\n"
        f"**Data**: {ts_str} | **Modello**: {KIMI_MODEL} | "
        f"**Tempo**: {elapsed:.0f}s | **Risposta**: {len(full_response):,} chars\n\n---\n\n"
    )
    output_path.write_text(header + full_response, encoding="utf-8")
    print(f"Salvato: {output_path}")


def main():
    print("=" * 60)
    print("KIMI K3 — NQ BACKTEST REDESIGN")
    print("=" * 60)

    # Carica .env se presente
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    print("Costruendo prompt (allego codebase + knowledge)...")
    prompt = build_full_prompt(BASE_DIR)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"kimi_k3_build_{ts}.md"

    call_kimi_k3(prompt, output_path)
    print(f"\nFatto! Leggi la risposta di Kimi K3 in:\n{output_path}")


if __name__ == "__main__":
    main()
