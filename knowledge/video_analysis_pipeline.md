# Video Analysis Pipeline --- Memoria di Sessione

## Obiettivo Generale
Analizzare video di trading (Fabio Valentini, Carmine Rosato, e altri) usando MiniMax M3 via OpenRouter,
con lo scopo di:
1. Estrarre i concetti di formazione spiegati (order flow, AMT, footprint, ecc.)
2. Osservare e documentare i trade live (entry, exit, ragionamento, grafico)
3. Identificare GAP di conoscenza rispetto al nostro sistema attuale
4. Aggiornare i prompt e le regole del sistema di backtest NQ in base a quanto imparato

## Video Analizzati

### COMPLETATO: Fabio Valentini & Carmine Rosato --- Live Trading
- URL: https://www.youtube.com/watch?v=xUyqIjCfZzg
- Durata: 3h 49m 37s
- Chunk: 23 da 10 minuti
- File sintesi: output/fabio_carmine_full_analysis.md
- File chunk: output/chunks/chunk_NN_*.md
- Status: COMPLETATO

### COMPLETATO: Deep Book DOM Dynamics (Spoofing & Icebergs)
- URL 1: https://www.youtube.com/watch?v=kKfMUQThG0c (Jigsaw - Spoofing And Large Orders)
- URL 2: https://www.youtube.com/watch?v=DZSpKqx7vuI (Bookmap - Iceberg Indicator Guide)
- File sintesi Jigsaw: output/analysis_kKfMUQThG0c.md
- File sintesi Bookmap: output/analysis_DZSpKqx7vuI.md
- File knowledge base: knowledge/deep_book_dom_dynamics.md
- Status: COMPLETATO

## Pipeline Tecnica

### Script Principale
scripts/analyze_youtube.py

Parametri chiave:
- chunk-minutes 10 (stabile con MiniMax)
- Compressione SOLO sulla risoluzione (144p), FPS invariato (MiniMax rifiuta < 1 FPS)
- Ogni chunk ~5MB dopo compressione (limite sicuro < 14MB)
- Cache SHA256 per chunk: rilanciare il comando riprende automaticamente

### Cache Sistema
- File: agent_memory/llm_cache.json
- Chiave: SHA256(system_prompt_con_dynamic_rules + user_msg + video_path)
- NOTA: cache key include dynamic_rules -> se cambiano, entries diventano stale

### Estrazione Chunk dalla Cache (ordine inserimento)
all_keys = list(cache.keys())
video_keys = [k for k in all_keys if ... Fabio/Jigsaw/footprint ...]
chunk_keys = video_keys[-24:-1]  # ultime 24 meno merge finale

## OpenRouter - Note Pratiche
- Modello: minimax/minimax-m3 (video + audio)
- Saldo minimo: 1.00 USD per richieste video (402 error se < 1 USD)
- Payload max: ~14MB per chunk (502 se supera ~50MB)
- Costo per video 4h: ~0.27 USD
- FPS troppo basso (0.5) -> API error, usare FPS originale

## Prossimi Obiettivi
1. Analizzare altri video di Fabio/Carmine con scripts/analyze_youtube.py
2. Per ogni video: estrarre concetti formativi + trade live osservati
3. Confrontare con prompt/regole correnti del sistema NQ
4. Aggiornare knowledge/dynamic_rules.json e i prompt degli agenti

## Script Knowledge Extraction
scripts/extract_video_knowledge.py
Estrae da ogni analisi video:
- Concetti insegnati (con definizioni operazionali)
- Trade live: timestamp, strumento, direction, entry, stop, target, esito
- Gap di conoscenza vs sistema corrente
- Suggerimenti per dynamic_rules
