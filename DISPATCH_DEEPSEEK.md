# DISPATCH per deepseek-v4-flash — DeepPrint Pro v2.0

> Preparato dall'agente di analisi (sessione FE). Esegui i task in ordine.
> Lavora SOLO dentro `C:\Users\Mauro\Documents\nq-backtest`.
> `C:\Users\Mauro\Documents\nq-backtest-clean` è **READ-ONLY** (mai scriverci).

---

## Contesto essenziale (già verificato, non riesplorare da zero)

- Frontend: `deepchart-desktop/src/` — `hooks/useWebSocket.ts` gestisce già i tipi:
  `candle_update`, `history_batch`, `volume_profile_update`, `session_context`,
  `dom_update`, `replay_status`, `available_dates`, `agent_signal`, `session_end`, `error`, `pong`.
- Store: `deepchart-desktop/src/store/tradingStore.ts` (Zustand). Ha già `domData`, `setDomData`,
  `addAlert`, `addCandle`, ecc. Tipi TS: `FootprintCandle`, `VolumeProfileData`, `SessionContextData`,
  `DOMData`, `Alert` (righe 9-100 di tradingStore.ts).
- Backend WS: `platform/ws_server.py` — classe `DeepPrintServer`. Punti di innesto:
  - `_load_date_async(date)` → dopo il caricamento, inviare anche i dati clean del giorno
  - `_handle_client_message` → aggiungere action `get_memory_stats`, `get_daily_roadmap`
  - builder esistenti: `_build_candle_message`, `_build_vp_message`, ecc.
- Bridge già pronto: **`platform/clean_bridge.py`** — NON riscriverlo.
  API: `get_bridge().get_agent_signals(date)`, `.get_trade_markers(date)`,
  `.get_daily_roadmap(date)`, `.get_memory_stats()`, `.available_dates()`.
- Import in ws_server: usa `importlib.util.spec_from_file_location` (vedi pattern esistente
  per config.py e data_service.py) per evitare il conflitto col built-in `platform`.

---

## TASK A — Integrazione clean → WS → frontend

### A1. `platform/ws_server.py`
1. Importa clean_bridge con il pattern importlib:
   ```python
   _cb_path = PROJECT_ROOT / "platform" / "clean_bridge.py"
   _spec3 = importlib.util.spec_from_file_location("clean_bridge", _cb_path)
   _cb_mod = importlib.util.module_from_spec(_spec3)
   _spec3.loader.exec_module(_cb_mod)
   get_bridge = _cb_mod.get_bridge
   ```
2. Nuovi builder di messaggi:
   ```python
   def _build_trade_markers_message(date):  # {'type':'trade_markers','data':{'date':date,'trades':[...]}}
   def _build_daily_roadmap_message(date):  # {'type':'daily_roadmap','data':{...} o None}
   def _build_memory_stats_message():       # {'type':'memory_stats','data':{'stats':[...]}}
   def _build_agent_signals_batch(date):    # {'type':'agent_signals_batch','data':{'date':date,'signals':[...]}}
   ```
3. In `_load_date_async`, dopo il broadcast di `replay_status`: invia in broadcast
   `trade_markers`, `daily_roadmap`, `agent_signals_batch` per la data caricata.
   Carica i dati clean in executor (sono I/O su file): `loop.run_in_executor(None, ...)`.
4. Nuove action in `_handle_client_message`: `get_daily_roadmap` (con `date` nel msg),
   `get_memory_stats`, `get_agent_signals` (con `date`).
5. ⚠️ Le date di cache_ohlc (333 giorni) e quelle di clean (poche) non coincidono sempre:
   se non ci sono dati clean per una data, invia messaggi con liste vuote, NON errori.

### A2. Frontend — `tradingStore.ts`
Aggiungi tipi e stato:
```ts
export interface TradeMarker { entryTime: string; exitTime: string; direction: string;
  entry: number; stop: number; target: number; exitPrice: number; exitReason: string;
  pnlUsd: number; pnlTicks: number; setupType: string; confidence: number; contracts: number; }
export interface DailyRoadmap { date: string; contextAnalysis: string;
  bullish: { trigger_description?: string; target_level?: number };
  bearish: { trigger_description?: string; target_level?: number }; }
export interface AgentSignalExt { barTimeEt: string; direction: string; confidence: number;
  setupType: string; finalDecision: string; noTradeReason: string; reasoning: string; detail: any; }
export interface MemoryStat { key: string; regime: string; setup: string; wall: string;
  seen: number; wins: number; losses: number; winRate: number; totalPnlUsd: number; }
```
Stato: `tradeMarkers: TradeMarker[]`, `dailyRoadmap: DailyRoadmap | null`,
`agentSignals: AgentSignalExt[]`, `memoryStats: MemoryStat[]` + relativi setter.

### A3. Frontend — `useWebSocket.ts`
Aggiungi case: `trade_markers`, `daily_roadmap`, `agent_signals_batch`, `memory_stats`.
Per `agent_signals_batch`: salva nello store E, per ogni signal con `finalDecision==='trade'`,
chiama anche `addAlert` (formato già esistente nel case `agent_signal`).

### A4. Frontend — nuovi componenti (in `src/components/`)
1. **`RoadmapPanel.tsx`**: card collassabile con contextAnalysis (testo), scenario bullish
   (verde) e bearish (rosso) con trigger_description e target_level. Se `dailyRoadmap` null → "Nessuna roadmap per questa data".
2. **`AgentSignalsPanel.tsx`**: lista scrollabile dei candidati del giorno. Ogni riga:
   ora ET, badge decisione (verde=trade/rosso=no_trade), direction, confidence, setup.
   Click → espande `detail` (reasoning Fabio, conferma Andrea, contesto VP/IB/GEX, risultato pnl).
3. **`TradeMarkersPanel.tsx`** (o tabella semplice): trade del giorno con entry/stop/target,
   exitReason, pnlUsd (verde/rosso). Totale P&L giornata in testa.
4. Integra i pannelli in `App.tsx` nella colonna destra sotto AlertPanel (o in un sistema a tab).
   Stile: Tailwind, coerente con AlertPanel.tsx esistente (leggilo prima).

### A5. Test Task A
```bash
cd C:/Users/Mauro/Documents/nq-backtest
python -c "import importlib.util; s=importlib.util.spec_from_file_location('cb','platform/clean_bridge.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); b=m.get_bridge(); print(b.available_dates()); print(len(b.get_agent_signals(b.available_dates()[-1])))"
python platform/ws_server.py   # in un terminale
cd deepchart-desktop && npm run dev   # in un altro
```
Verifica nel browser (http://localhost:5173): caricando una data presente in
`bridge.available_dates()` compaiono roadmap, candidati e trade.

---

## TASK B — Priorità 1: `scripts/mock_tick_generator.py`

Scopo: tick sintetici per test UI/latenza. **MAI per backtest.**

1. Input: `cache_ohlc/YYYYMMDD.csv` (`timestamp,open,high,low,close`, tz UTC, NO volume).
2. Per ogni minuto genera tick virtuali:
   - Volume stimato: `base 400 + (high-low)*120 + rumore ±30%`, moltiplicatore ×2.5
     fra 13:30-16:00 UTC (orario NY), min 50 contratti/min.
   - Path intrabar: random walk open→close vincolato in [low, high], step di 0.25 (tick NQ).
   - Ogni tick: size 1-5 (distribuzione: 60% size 1, 25% size 2, 10% 3-5, 5% 6-10).
   - Side: candela rialzista (close>open) → 65% 'A' (buy) / 35% 'B'; ribassista invertito;
     doji 50/50.
   - Big trade: con probabilità ~3% al minuto, un tick size 30-150 (soglia big = 30) sul
     lato dominante della candela, prezzo random in [low, high].
   - Timestamp: nanosecondi UTC spalmati nel minuto, monotoni crescenti.
3. Output: `cache_mock/YYYYMMDD.csv` con colonne `ts_event,action,side,price,size`
   (action='T', ts_event ISO 8601 UTC) — **identiche a quelle attese da
   `platform/data_service._load_csv_raw`**, così il ws_server esistente può leggerle.
4. CLI:
   ```
   python scripts/mock_tick_generator.py --date 2025-01-02            # un giorno
   python scripts/mock_tick_generator.py --all                        # tutti i file in cache_ohlc
   python scripts/mock_tick_generator.py --date 2025-01-02 --out cache_mock
   ```
   Con `--seed` per riproducibilità. Stampa stats: tick generati, volume totale, n big trades.
5. Test: `DataService(cache_dir=Path('cache_mock')).load_date('2025-01-02')` deve tornare
   barre M1 con `_fp_levels` non vuoti e big_trades. Confronta OHLC aggregato dai tick con
   l'OHLC sorgente: deve coincidere entro il tick size (il path vincolato lo garantisce:
   il primo tick = open, l'ultimo = close, max/min toccati — forza almeno un tick su high e uno su low).

---

## TASK C — Priorità 2: `scripts/download_mbo_data.py`

1. Databento Python client (`databento` package, API key da env `DATABENTO_API_KEY` —
   controlla se esiste già in nq-backtest-clean/config o .env, READ-ONLY).
2. Schema `tbbo` (trades + BBO), simbolo NQ front-month (es. `NQ.c.0` continuous),
   20-30 giorni di cache_ohlc a scelta (default: i 20 più recenti).
3. Salva in `cache_ticks/YYYYMMDD.parquet` con colonne: `ts_event` (ns UTC, int64 o
   datetime64[ns, UTC]), `action`, `side`, `price` (float), `size` (int).
4. Validazione incrociata: per ogni giorno, aggrega M1 (resample 1min: price ohlc, size sum)
   e confronta con `cache_ohlc/YYYYMMDD.csv`. Report: max diff su open/high/low/close in tick.
   Scrivi report in `cache_ticks/_validation_report.md`. Tolleranza: ±2 tick su H/L
   (i CSV OHLC potrebbero essere di un fornitore diverso).
5. ⚠️ Costo API: scarica UN giorno prima, valida, poi procedi col batch (flag `--confirm-batch`).

---

## TASK D — Priorità 3: integrazione dati reali + DOM

1. `platform/data_service.py`: aggiungi `DataService(cache_dir=...)` con fallback:
   se esiste `cache_ticks/YYYYMMDD.parquet` per la data → usa quello (pd.read_parquet,
   stessa logica di `_load_csv_raw`), altrimenti CSV. Mantieni retrocompatibilità.
2. DOM reale: schema TBBO dà bid/ask L1. In `ws_server._emit_bar`, costruisci e broadcast
   un messaggio `dom_update` coerente col tipo `DOMData` del frontend (LEGGI prima
   `tradingStore.ts` righe 87-99 e il componente OrderBookDOM in App.tsx per il formato esatto).
   Per L2+ servirà schema MBP-10 (task futuro, segnalalo nello status).
3. In App.tsx sostituisci la generazione del DOM simulato con `domData` dallo store
   (fallback al simulato se `domData` null, con badge "SIMULATO").
4. QA: replay visivo di 1 giorno con dati reali, screenshot footprint vs price action.

---

## Al termine di OGNI task
Aggiorna `DEEPCHART_STATUS.md` (sezione TODO → spunta, note di esito, eventuali problemi).
Non modificare questo file di dispatch.
