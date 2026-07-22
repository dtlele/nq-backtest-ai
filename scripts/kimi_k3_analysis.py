"""
Kimi K3 Full System Analysis
============================
Raccoglie tutto il codebase + knowledge e lo manda a Kimi K3 via OpenRouter
per ottenere una analisi completa e suggerimenti di miglioramento al 100%.

Uso:
    python scripts/kimi_k3_analysis.py
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────
sys.path.append(str(Path(__file__).parent.parent))

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "REDACTED_KEY")
KIMI_MODEL = "moonshotai/kimi-k3"  # Kimi K3 su OpenRouter (rilasciato 16 luglio 2026)

# ── File da includere nel contesto ─────────────────────────────────────────
FILES_TO_INCLUDE = {
    # === CORE CODE ===
    "src/backtest_runner.py": "Core backtest engine (main loop, day processing)",
    "src/__init__.py": "Global config, constants, data classes",
    "src/candidate_detector.py": "Candidate detection (big trades + VP proximity)",
    "src/volume_profile.py": "Volume Profile computation (POC, VA, HVN, LVN)",
    "src/session_context.py": "Session context (IB, day_type, NY window)",
    "src/signal_context.py": "Signal context (AMT structural profile, trapped participants)",
    "src/trade_simulator.py": "Trade simulation (entry, stop, target, PnL)",
    "src/consensus.py": "Signal fusion (Fabio + Andrea consensus)",
    "src/bar_aggregator.py": "Bar aggregation (tick → 1min/5min)",
    "src/risk_manager.py": "Risk management (contract sizing)",
    "src/agents/fabio_agent.py": "Primary AI agent (Fabio - direction, confidence, setup)",
    "src/agents/andrea_agent.py": "Confirmation agent (Andrea - footprint, IBOB)",
    "src/agents/precision_entry.py": "Precision entry refinement (M1 context)",
    "src/agents/llm_client.py": "LLM client (OpenRouter integration)",
    "src/agents/dynamic_rules_manager.py": "Dynamic rules management",
    "src/agents/topic_router.py": "Topic routing for knowledge retrieval",
    
    # === SCRIPTS ===
    "scripts/run_unified_backtest_with_filters.py": "Unified backtest with filters (time sessions, ATR, mega levels)",
    "scripts/find_optimal_filters.py": "Optimal filter search (grid search on parameters)",
    "scripts/time_session_optimizer.py": "Time session optimizer",
    "scripts/regime_volatility_optimizer.py": "Regime/volatility optimizer",
    
    # === KNOWLEDGE ===
    "knowledge/master_trading_manual.md": "Master trading manual (core principles)",
    "knowledge/dynamic_rules.json": "Dynamic rules (active AMT rules with success/failure stats)",
    "knowledge/narrative_philosophy.md": "Narrative philosophy",
    "knowledge/pending_rules_update.md": "Pending rules updates",
    "knowledge/deep_book_dom_dynamics.md": "Deep book DOM dynamics",
    "knowledge/andrea_distilled.json": "Andrea distilled knowledge",
    "knowledge/fabio_distilled.json": "Fabio distilled knowledge",
    "knowledge/strategies.json": "Strategies definitions",
    
    # === CONFIG & DOCS ===
    "DASHBOARD_AND_ROADMAP.md": "Project roadmap and current state",
    "run_backtest.py": "Entry point",
    "requirements.txt": "Dependencies",
}

# File opzionali (grandi, includi solo se < MAX_FILE_SIZE bytes)
MAX_FILE_SIZE = 30_000  # 30KB


def read_file_safe(path: Path, max_size: int = None) -> str:
    """Legge un file, troncando se troppo grande."""
    try:
        size = path.stat().st_size
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if max_size and size > max_size:
            content = content[:max_size] + f"\n\n[... TRONCATO: file originale {size} bytes ...]"
        return content
    except Exception as e:
        return f"[ERRORE LETTURA: {e}]"


def collect_knowledge_rules_sample(base_dir: Path, max_rules: int = 20) -> str:
    """Campiona le regole dal trader_lessons_graph."""
    rules_dir = base_dir / "knowledge" / "trader_lessons_graph"
    if not rules_dir.exists():
        return ""
    
    rules = []
    # Leggi i file rule_* (più importanti dei node_*)
    for f in sorted(rules_dir.glob("rule_*.md"))[:max_rules]:
        content = read_file_safe(f, max_size=2000)
        rules.append(f"### {f.name}\n{content[:1500]}\n")
    
    return "\n".join(rules)


def collect_backtest_output_sample(base_dir: Path) -> str:
    """Raccoglie output e risultati backtest esistenti."""
    output_dir = base_dir / "output"
    result = ""
    
    # Cerca report markdown
    for f in sorted(output_dir.glob("*.md"))[:3]:
        content = read_file_safe(f, max_size=5000)
        result += f"\n\n### OUTPUT: {f.name}\n{content}\n"
    
    # Cerca JSON con risultati
    for f in sorted(output_dir.glob("*.json"))[:2]:
        content = read_file_safe(f, max_size=3000)
        result += f"\n\n### RESULTS: {f.name}\n{content}\n"
    
    # Controlla scripts/regime_volatility_optimizer_results.json
    regime_f = base_dir / "scripts" / "regime_volatility_optimizer_results.json"
    if regime_f.exists():
        content = read_file_safe(regime_f, max_size=5000)
        result += f"\n\n### REGIME OPTIMIZER RESULTS:\n{content}\n"
    
    return result


def build_context(base_dir: Path) -> str:
    """Costruisce il mega-contesto da mandare a Kimi K3."""
    sections = []
    
    sections.append("""# NQ FUTURES BACKTEST SYSTEM - COMPLETE CODEBASE FOR KIMI K3 ANALYSIS

## OBIETTIVO DI QUESTA ANALISI
Sei Kimi K3, il modello di ragionamento più avanzato al mondo. Hai il compito di:
1. Analizzare in profondità l'INTERO sistema di backtest per NQ (Nasdaq futures)
2. Identificare TUTTI i punti deboli, bug, inefficienze, e opportunità mancate
3. Proporre una NUOVA VERSIONE MIGLIORATA al 100% dell'intero sistema
4. Essere RADICALE: non fare piccole patch, ridisegna l'architettura dove necessario
5. Fare SCELTE AUTONOME su cosa tenere, cosa buttare, cosa aggiungere

## CONTESTO DEL PROGETTO
- **Mercato**: NQ (Nasdaq 100 E-mini futures), trading intraday
- **Strategia**: Basata su Auction Market Theory (AMT) con due trader esperti: Fabio (primario) e Andrea (conferma)
- **Dati**: DataBento tick-by-tick, poi aggregati in barre 1min/5min
- **Conto target**: FundedNext 50k CFD, max drawdown $2,500, rischio per trade 0.15%-0.25%
- **Best result finora**: Profit Factor=4.62, MaxDD=$525 (baseline time session optimizer)
- **LLM usato**: OpenRouter (DeepSeek, Claude, ora Kimi K3)

## STRUTTURA DEL SISTEMA
```
DataBento CSV → DataLoader → BarAggregator → VolumeProfile → SessionContext
             → CandidateDetector → FabioAgent (LLM) → AndreaAgent (LLM)
             → Consensus → PrecisionEntry → TradeSimulator → AgentMemory
```

---
""")

    # === FILE DEL CODEBASE ===
    sections.append("# CODEBASE COMPLETO\n")
    
    for rel_path, description in FILES_TO_INCLUDE.items():
        full_path = base_dir / rel_path
        if not full_path.exists():
            sections.append(f"\n## {rel_path}\n*[FILE NON TROVATO]*\n")
            continue
        
        content = read_file_safe(full_path, max_size=MAX_FILE_SIZE)
        ext = full_path.suffix.lower()
        lang = {"py": "python", ".json": "json", ".md": "markdown", ".txt": "text"}.get(ext.lstrip("."), "text")
        
        sections.append(f"""
## {rel_path}
**Descrizione**: {description}

```{lang}
{content}
```
""")

    # === KNOWLEDGE RULES SAMPLE ===
    sections.append("\n# SAMPLE REGOLE TRADING (trader_lessons_graph)\n")
    rules_sample = collect_knowledge_rules_sample(base_dir, max_rules=15)
    sections.append(rules_sample)
    
    # === OUTPUT / RISULTATI ===
    sections.append("\n# OUTPUT E RISULTATI BACKTEST ESISTENTI\n")
    output_sample = collect_backtest_output_sample(base_dir)
    sections.append(output_sample if output_sample else "*Nessun output trovato*")
    
    # === DOMANDA FINALE ===
    sections.append("""
---

# IL TUO COMPITO (Kimi K3)

Ora hai visto l'intero sistema. Analizza profondamente e produci:

## 1. DIAGNOSI CRITICA
Per ogni componente del sistema, identifica:
- **Bug/errori** nascosti nel codice
- **Inefficienze** computazionali o logiche
- **Limitazioni architetturali** che frenano le performance
- **Opportunità mancate** (tecniche di trading non implementate che sarebbero utili)

## 2. ANALISI DELLA STRATEGIA TRADING
- Le regole AMT sono implementate correttamente nel codice?
- Il prompt del FabioAgent è ottimale?
- Il sistema di confidence scoring è valido matematicamente?
- Il CandidateDetector cattura i setup giusti?
- Il TradeSimulator simula realisticamente il mercato?

## 3. PIANO DI MIGLIORAMENTO (versione 2.0)
Proponi la nuova architettura con:

### A) Miglioramenti immediati (codice da riscrivere)
Per ogni file da modificare, scrivi il NUOVO CODICE COMPLETO.

### B) Nuovi componenti da aggiungere
Descrivi e codifica i nuovi moduli necessari.

### C) Miglioramenti alla strategia trading
Suggerimenti basati sulla teoria AMT e market microstructure.

### D) Ottimizzazioni LLM
Come migliorare i prompt e l'architettura degli agenti AI.

### E) Infrastructure & Pipeline
Come migliorare la pipeline di dati, il backtest engine, gli optimizer.

## 4. CODICE DELLA NUOVA VERSIONE
Scrivi il codice completo per le parti più critiche e impattanti.
Non fare pseudocodice: scrivi Python vero, funzionante, pronto per essere copiato.

## 5. PRIORITÀ E ROADMAP
Elenca le modifiche in ordine di impatto (dal più alto al più basso).
Per ogni modifica: stima l'impatto atteso sul Profit Factor e MaxDD.

---

Sii RADICALE, PRECISO, e COMPLETO. Non limitarti a suggerire piccoli fix.
Se vedi che l'architettura di un componente è sbagliata, ridisegnala completamente.
Il tuo output sarà la base per costruire la versione 2.0 del sistema.
""")

    return "\n".join(sections)


def call_kimi_k3(context: str, output_path: Path) -> dict:
    """Chiama Kimi K3 via OpenRouter con streaming."""
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/nq-backtest",
        "X-Title": "NQ Backtest Kimi K3 Analysis",
    }
    
    # Stima dimensione contesto
    context_size = len(context)
    print(f"📦 Dimensione contesto: {context_size:,} caratteri ({context_size//4:,} token stimati)")
    
    payload = {
        "model": KIMI_MODEL,
        "messages": [
            {
                "role": "user",
                "content": context,
            }
        ],
        "max_tokens": 32000,
        "temperature": 0.3,  # Bassa per ragionamento preciso
        "stream": True,
    }
    
    print(f"\n🚀 Inviando richiesta a {KIMI_MODEL} via OpenRouter...")
    print(f"⏳ Questa operazione può richiedere 5-15 minuti per la dimensione del contesto...\n")
    
    # Salva il contesto per debug
    context_path = output_path.parent / "kimi_k3_context.txt"
    with open(context_path, "w", encoding="utf-8") as f:
        f.write(context)
    print(f"💾 Contesto salvato in: {context_path}")
    
    full_response = ""
    start_time = time.time()
    
    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=600) as response:
            response.raise_for_status()
            
            print("✅ Connessione stabilita. Ricevendo risposta...\n")
            print("=" * 80)
            
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                print(content, end="", flush=True)
                                full_response += content
                        except json.JSONDecodeError:
                            pass
            
            print("\n" + "=" * 80)
            
    except requests.exceptions.Timeout:
        print("\n⚠️ Timeout! La risposta ha impiegato troppo tempo.")
        if full_response:
            print(f"💾 Salvando risposta parziale ({len(full_response)} caratteri)...")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Errore HTTP: {e}")
        raise
    
    elapsed = time.time() - start_time
    print(f"\n⏱️ Tempo totale: {elapsed:.1f}s")
    print(f"📝 Lunghezza risposta: {len(full_response):,} caratteri")
    
    # Salva la risposta
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# Kimi K3 Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Modello**: {KIMI_MODEL}\n")
        f.write(f"**Tempo elaborazione**: {elapsed:.1f}s\n")
        f.write(f"**Dimensione contesto**: {context_size:,} chars\n\n")
        f.write("---\n\n")
        f.write(full_response)
    
    print(f"\n✅ Analisi salvata in: {output_path}")
    
    return {
        "model": KIMI_MODEL,
        "elapsed": elapsed,
        "response_length": len(full_response),
        "output_path": str(output_path),
    }


def main():
    print("=" * 80)
    print("🤖 KIMI K3 - NQ BACKTEST FULL SYSTEM ANALYSIS")
    print("=" * 80)
    print(f"📂 Base directory: {BASE_DIR}")
    print(f"🔑 OpenRouter key: {OPENROUTER_API_KEY[:20]}...")
    print()
    
    # 1. Costruisci il contesto
    print("📖 Raccogliendo il codebase e la knowledge base...")
    context = build_context(BASE_DIR)
    
    # 2. Timestamp output
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"kimi_k3_analysis_{ts}.md"
    
    # 3. Chiama Kimi K3
    result = call_kimi_k3(context, output_path)
    
    print("\n" + "=" * 80)
    print("🎉 ANALISI COMPLETATA!")
    print(f"📄 Output: {result['output_path']}")
    print(f"⏱️ Tempo: {result['elapsed']:.1f}s")
    print(f"📊 Dimensione risposta: {result['response_length']:,} caratteri")
    print("=" * 80)


if __name__ == "__main__":
    # Carica .env se disponibile
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    
    main()
