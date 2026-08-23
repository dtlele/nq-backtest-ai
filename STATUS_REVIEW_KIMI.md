# Resoconto Lavori Piattaforma Volumetrica per Kimi K3

## 1. Cosa è stato implementato (Fase 1 e 2 completate)
Abbiamo seguito il PRD e completato sia il Backend (WebSocket) che il Frontend (React/Zustand):

### Backend (Python)
1. **`platform/config.py`**: File di configurazione centralizzato (porte, tick size, orari sessioni).
2. **`platform/data_service.py`**: Modulo che carica i file CSV da `cache_ohlc/` e raggruppa i dati in barre M1/M5. Abbiamo implementato la logica per ricostruire il *Footprint* (Bid/Ask per livello di prezzo) e le "bolle" per i Big Trades.
3. **`platform/ws_server.py`**: Server WebSocket asincrono (`websockets` v16) che gestisce il replay storico, ricalcola il Volume Profile progressivo e invia i messaggi (candle, VP, context) al client.
4. **`run_server.py`**: Launcher root per risolvere i conflitti di modulo (il built-in `platform` di Python andava in conflitto).

### Frontend (TypeScript / React / Zustand)
1. **`src/store/tradingStore.ts`**: Store globale con Zustand per gestire lo stato della piattaforma (candele, WS status, Volume Profile, DOM).
2. **`src/hooks/useWebSocket.ts`**: Hook React per auto-riconnessione e dispatch dei messaggi WebSocket allo store.
3. **`src/components/FootprintChart.tsx`**: Riscritto completamente (v2.0) con Canvas/CSS Transform per Pan & Zoom, Bid×Ask footprint per livello (heatmap imbalance), overlay del Volume Profile (VAH, VAL, POC), IB Box e GEX Lines.
4. **`src/components/CVDChart.tsx`**: Grafico CVD (Cumulative Volume Delta) tramite Canvas HTML5, sincronizzato orizzontalmente col footprint.
5. **`src/components/VolumeProfileSidebar.tsx`**: Istogramma verticale per il Volume Profile dell'intera sessione.
6. **`src/components/ReplayControls.tsx`**: Barra di trasporto in basso per Play/Pausa, Step e controllo velocità (da 1x a MAX).
7. **`src/components/SessionInfoBar.tsx`**: Header per mostrare lo stato di Initial Balance, GEX e Day Type.
8. **`src/App.tsx`**: Integrati tutti i componenti in un layout in stile terminale di trading professionale. Il codice compila senza errori TypeScript.

## 2. Il Blocco Rilevato (Attenzione Kimi!)
Nel testare il caricamento dei dati, è emerso un limite **strutturale critico** nei dati storici attuali:
- Il PRD e il codice assumono che i CSV in `cache_ohlc/` contengano dati *tick-by-tick* (o MBO) con colonne: `ts_event, action, side, price, size`.
- Leggendo effettivamente un file (es. `cache_ohlc/20260618.csv`), ho scoperto che **i dati salvati sono semplici candele OHLCV a 1 minuto**:
  `timestamp, open, high, low, close` (senza volumi separati bid/ask, senza size dei singoli trade).

**Domanda per Kimi K3:**
Dato che non abbiamo i dati tick-by-tick nella cache per generare un vero grafico Footprint (non possiamo separare Bid e Ask o calcolare i Big Trades dal semplice OHLCV):
1. Dobbiamo simulare/inferire i volumi Bid/Ask all'interno della barra per scopi di sviluppo/test visivo della piattaforma?
2. O dobbiamo implementare uno script che riscarica i dati MBO/tick reali da Databento per i giorni che vogliamo visualizzare nel Replay?

## 3. Prossimi Passi (Domani)
- Risolvere con Kimi la gestione dei dati (Simulazione vs Download Databento MBO).
- Avviare il backtest unificato per il primo giorno (`scripts/run_unified_backtest_with_filters.py`) come richiesto.
- Correggere eventuali bug che emergeranno durante l'esecuzione del backtest.
