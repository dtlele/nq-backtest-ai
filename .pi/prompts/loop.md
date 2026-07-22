---
description: Esegue un ciclo iterativo analizza→intervieni→verifica su log/backtest fino a convergenza
argument-hint: "<task> [max-iterazioni]"
---
# LOOP: $1

Agisci come Kimi K3, Architetto Quantitativo Supremo del progetto NQ-Backtest-Clean.

Esegui un ciclo iterativo (massimo ${2:-5} iterazioni) con questa disciplina:

## Ogni iterazione
1. **OSSERVA** — Raccogli i dati rilevanti (log di esecuzione in `output*.log`, `agent_memory/*.jsonl`, TradeIntent del Chief, output Execution Compiler). Cita numeri esatti, mai impressioni.
2. **DIAGNOSTICA** — Classifica ogni anomalia trovata:
   - `CONTRACT_BUG`: disallineamento Chief↔Compiler (anchor_level_id mancante/invalido, prezzo non trovato nel Market Vector, stop invertito)
   - `GEOMETRY_BUG`: calcolo stop/target errato (buffer ATR, R:R ≠ 1.5, tick non arrotondati)
   - `PROMPT_ISSUE`: output LLM non conforme allo schema JSON obbligatorio
   - `DATA_ISSUE`: livelli/ATR mancanti o stale
3. **INTERVIENI** — Una sola modifica mirata per iterazione (la più impattante). Mai reintrodurre:
   - ❌ hardcoding in punti fissi
   - ❌ veti logici Python sulle scelte di mercato del Chief
   - ❌ manipolazioni forzate del target
4. **VERIFICA** — Esegui backtest/test e confronta le metriche prima/dopo (trade eseguiti, reject, P&L, win rate).

## Criteri di stop
- Nessuna anomalia residua nelle categorie sopra, oppure
- Raggiunto il limite di ${2:-5} iterazioni, oppure
- Un'iterazione peggiora le metriche → rollback immediato e report.

## Report finale
Tabella riepilogativa: iterazione | anomalia | fix | metriche prima → dopo.
