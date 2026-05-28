# Stato attuale e recap

## Stato attuale
- **Codice**: tutti i file sorgente sono aggiornati nella cartella `c:\Users\Mauro\Documents\nq-backtest`.
- **Fix**: è stato implementato il fix di causalità per `step_trade` (stop‑loss non più attivato su low pre‑entry).
- **Log**: `trades_log.jsonl` mostra 0 trade per il 4‑Feb perché la run corrente non ha generato candidati; il problema è legato alla **classificazione del giorno** e alle **regole AMT rigide**.
- **Cron**: il cron che controlla il backtest è stato fermato.
- **Artefatti**: è stato creato `implementation_plan.md` con tutti i punti da implementare.

## Cosa dobbiamo implementare (riassunto del piano)
1. **Day‑type dinamico**
   - Aggiungere `update_day_type` in `src/session_context.py`.
   - Chiamare la funzione ad ogni nuova barra M5 in `src/backtest_runner.py`.
   - Memorizzare la cronologia del tipo di giorno in `SessionContext`.
2. **Ammorbidire la regola AMT 001**
   - Sostituire il blocco hard‑coded con una verifica di `candidate.market_state == "imbalance"` e `candidate.excess_tail`.
   - Aggiungere flag `exhaustion_signal` in `detect_candidates`.
3. **Gestione delle dynamic‑rules**
   - Nuovo modulo `src/agents/dynamic_rules_manager.py` con limite a 3 regole attive.
   - Funzione `validate_dynamic_rule` in `audit_agent.py` (≥5 giorni, +2 % win‑rate).
   - Aggiornare lo schema `knowledge/dynamic_rules.json` con statistiche di performance.
4. **Espansione della visione di Fabio**
   - Aggiornare `fabio_system_prompt.txt` con la sezione **EXHAUSTION SETUPS**.
   - Aggiornare lo schema JSON di `light_analyze` per includere `exhaustion_signal` (+15 punti).
   - Aggiornare `fabio_agent.analyze` per includere il nuovo campo.
5. **Test e verifica**
   - Unit‑test per `update_day_type`.
   - Unit‑test per `exhaustion_signal`.
   - Test di integrazione su dataset Feb 2025 (controllare win‑rate, profit factor, max‑drawdown).
   - Aggiornare `walkthrough.md` con i risultati.

## Prossimi passi consigliati
- **Conferma** il piano (eventuali domande o modifiche).
- **Avviare** un branch di lavoro (es. `feature/dynamic‑day‑type`).
- **Implementare** i punti 1‑4 in ordine, eseguendo i test dopo ciascuna modifica.
- **Eseguire** una backtest completa su Feb 2025 per verificare che i trade del 4‑Feb ora escano per target.
- **Push** i commit su un repository remoto (GitHub) una volta completata la fase di testing.

---
*Questo file è stato salvato come `implementation_summary.md` nella radice del progetto.*
