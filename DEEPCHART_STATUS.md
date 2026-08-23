# DEEPCHART STATUS — DeepPrint Pro v2.0

> Ultimo aggiornamento: sessione **"DEEPSEEK-FLASH"** (Task A + A.5 completati) — 2025-07-16

## ⚡ LIVE STATUS
- `ws_server.py` in esecuzione su **porta 8765** con dati mock (4 date da `cache_mock/`)
- `npm run dev` su **porta 5173** — frontend attivo e connesso
- Dati mock: 20250203, 20250812, 20250814, 20260109
- Per fermare i server: `taskkill //F //PID <PID>` 
- Server attuale PID: 20688

---

## ✅ COMPLETATO — Task A (Integrazione Clean Bridge)

### A1. `platform/ws_server.py`
- Importato `clean_bridge.py` via `importlib` (pattern esistente)
- Nuovi builder: `_build_trade_markers_message`, `_build_daily_roadmap_message`, `_build_memory_stats_message`, `_build_agent_signals_batch`
- In `_load_date_async`: broadcast dati clean dopo il caricamento delle barre
- In `_send_initial_state`: broadcast di tutti i dati clean per nuovi client
- Nuove action WS: `get_daily_roadmap`, `get_memory_stats`, `get_agent_signals`
- **Verificato**: 23 keys memory_stats, 1 trade, 96 signals, roadmap presente 🟢

### A2. `tradingStore.ts`
- Nuovi tipi: `TradeMarker`, `DailyRoadmap`, `AgentSignalExt`, `MemoryStat`
- Nuovo stato e setter: `tradeMarkers`, `dailyRoadmap`, `agentSignals`, `memoryStats`
- Nuovo toggle UI: `showCleanData` / `setShowCleanData`

### A3. `useWebSocket.ts`
- Nuovi case: `trade_markers`, `daily_roadmap`, `agent_signals_batch`, `memory_stats`
- Per `agent_signals_batch`: chiama `addAlert` per ogni segnale con `finalDecision === 'trade'`

### A4. Nuovi componenti
- **`RoadmapPanel.tsx`**: Card collassabile con contextAnalysis, bullish/bearish scenario, key levels. Versione inline opzionale.
- **`AgentSignalsPanel.tsx`**: Lista scrollabile candidati, click per espandere dettaglio Fabio/Andrea/contesto/risultato. Badge decisione colorato.
- **`TradeMarkersPanel.tsx`**: Tabella trade con entry/stop/target/exit, PnL colorato, stats (win rate, avg). Espansione dettaglio.
- Integrati in **`App.tsx`** in una sidebar destra "DEEP DATA" con toggle `Clean` nella toolbar.

### A5. Refactoring FootprintChart (canvas)
- **Canvas rendering** invece di DOM per il footprint grid (35K+ elementi → 1 canvas)
- **Candlestick + footprint** disegnati su canvas con colorazione delta
- **Trade Markers**: linee entry/stop/target/exit sul chart (dati CleanBridge)
- **Agent Signal arrows**: ▲/▼ sul chart per segnali trade
- **Big Trade bubbles**: glow + label dimensione
- **SVG overlay** mantenuto per linee VP/IB/GEX
- **Zoom controls**, pan con drag, auto-scroll replay

---

## 📊 STATO PIATTAFORMA

### Frontend (`deepchart-desktop/`)
- React 19 + Vite + Tailwind + Zustand — compila con `tsc --noEmit` ✅
- Componenti: FootprintChart (canvas), CVDChart, ReplayControls, SessionInfoBar, AlertPanel, VolumeProfileSidebar, RoadmapPanel, AgentSignalsPanel, TradeMarkersPanel, OrderBookDOM

### Backend (`platform/`)
- `ws_server.py`: replay barre M1 con footprint, VP progressivo, session context, comandi play/pause/step/speed/date/seek + CleanBridge dati agenti
- `clean_bridge.py`: bridge READ-ONLY verso nq-backtest-clean (434 candidati, 6 trade, 23 chiavi)
- `data_service.py`: caricamento CSV Databento + aggregazione M1/M5
- `config.py`: env `NQ_CACHE_OHLC_DIR`

---

## ⚠️ NOTE / PROBLEMI APERTI

1. **Performance caricamento dati**: 1.2M+ trades/giorno → caricamento lento (~30s+). DataService processa ogni trade in loop Python. Ottimizzazione necessaria.
2. **cache_ohlc/ dati OHLC**: 333 file in formato `timestamp,open,high,low,close` (NO Databento). DataService non compatibile con OHLC diretto — serve conversione.
3. **ws_server su Windows**: alcune chiamate `taskkill` non funzionano con forward slash. Usare `taskkill //F //PID N` su Git Bash.

---

## 🔜 PROSSIMI STEP

| # | Task | File | Priorità | Stato |
|---|---|---|---|---|
| A | Integrazione Clean Bridge WS + pannelli | vari | **ALTA** | **✅ COMPLETATO** |
| A.5 | Refactoring grafico FootprintChart | `FootprintChart.tsx` | **ALTA** | **✅ COMPLETATO** |
| B | Mock tick generator | `scripts/mock_tick_generator.py` | Priorità 1 | **✅ DONE (precedente)** |
| C | Download MBO Databento | `scripts/download_mbo_data.py` | Priorità 2 | **✅ CREATO** (utility futura, dati già in cache_ohlc/) |
| D | Dati reali → cache_ticks + DOM reale | `data_service.py`, `ws_server.py` | Priorità 3 | **⏳ DEFERRED** (futuro) |

---

## Vincoli attivi
- Dati mock SOLO per UI, mai per backtest/strategia
- Timestamp Databento: ns UTC → convertire in ET per il trading
- **nq-backtest-clean: READ-ONLY** (altro agente)
- Lavorare SOLO dentro `C:\Users\Mauro\Documents\nq-backtest`
