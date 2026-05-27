# NQ Backtest — Dashboard & Roadmap

## Dashboard (live now)

```
python dashboard.py   ->   http://localhost:8050
```

### Cosa mostra

| Pannello | Contenuto |
|----------|-----------|
| **KPI row** | Candidati totali, giorni analizzati, trade eseguiti, P&L ($), win rate, confidence media |
| **Candidates Per Day** | Bar chart per data, colorata per decisione (rosso=no_trade, verde=trade) |
| **Cumulative P&L** | Curva dei profitti cumulativi per trade |
| **Day Type** | Torta balance/trend_up/trend_down per caratterizzare ogni sessione |
| **VP Level Proximity** | Quali livelli (POC, VA, IB, HVN, LVN) vengono "toccati" piu spesso |
| **IB Range** | Range dell'Initial Balance giorno per giorno |
| **Confidence Gauge** | Gauge della confidence media Fabio con soglia a 65 |
| **Confidence Histogram** | Distribuzione score Fabio, linea threshold gialla |
| **Setup Types** | Quali setup (squeeze, ivb_breakout, ecc) vengono rilevati |
| **Delta vs Confidence scatter** | Relazione tra delta di barra e confidence, colorato per livello VP |
| **Candidate Log Table** | Tabella filtrabile/ordinabile con tutti i candidati e le decisioni |

---

## Cosa abbiamo costruito finora

### Pipeline completa
```
DataBento CSV  ->  DataLoader (symbol filter, front-month)
                ->  BarAggregator (1min per VP/IB, 5min per agents)
                ->  VolumeProfile (POC, VAH, VAL, HVN, LVN)
                ->  SessionContext (IB, day_type, is_fabio_active)
                ->  CandidateDetector (big trades + VP proximity)
                ->  FabioAgent (claude -p, confidence >= 65 -> trade)
                ->  AndreaAgent (conferma footprint IBOB/squeeze)
                ->  Consensus
                ->  TradeSimulator (entry/stop/target/PnL)
                ->  AgentMemory (reasoning_log.jsonl, trades_log.jsonl)
                ->  Dashboard (Dash + Plotly)
```

### Metriche matematiche validate
- **POC**: argmax dei bucket di volume — corretto
- **VA expansion**: greedy dal POC, prende sempre il lato con piu volume — standard CME/TPO
- **VA 70%**: `VALUE_AREA_PCT = 0.70`
- **IB**: prima `IB_DURATION_MIN = 15` minuti della sessione NY (09:30-09:45 ET)
- **Tick bucket**: `TICK_BUCKET_SIZE = 0.25` (NQ tick size)
- **Big trade**: soglia `NQ_BIG_TRADE_THRESHOLD` contratti per singola transazione

### Dati loggati per ogni candidato
```json
{
  "date", "bar_time_et", "bar_open/high/low/close/volume/delta",
  "wall_level", "wall_side", "wall_max_size", "wall_trade_count",
  "proximity_to", "proximity_level",
  "ib_high", "ib_low", "ib_range", "poc", "va_high", "va_low", "day_type",
  "fabio_direction", "fabio_confidence", "fabio_setup", "fabio_reasoning",
  "andrea_confirmation", "andrea_confidence", "andrea_setup", "andrea_reasoning",
  "final_confidence", "decision", "no_trade_reason",
  "trade_direction", "trade_entry", "trade_stop", "trade_target"
}
```

---

## Cosa possiamo fare ora

### 1. Backtest completo (106 giorni)
Abbiamo solo 5 giorni di dati. Col full run si ottengono:
- Statistiche robuste (win rate, avg R, max drawdown)
- Distribuzione reale dei setup per condizione di mercato
- Calibrazione delle soglie (65 e' giusta? 60? 70?)

```bash
python run_backtest.py --days 0   # tutti i file disponibili
```

### 2. Ottimizzazione soglie agenti
Il parametro piu critico e' `FABIO_MIN_CONFIDENCE = 65`.
Con il log strutturato possiamo fare grid search:
- Provare 50, 55, 60, 65, 70, 75
- Misurare win rate e profit factor per ogni soglia
- Trovare il punto ottimo tra troppi trade (noise) e troppo pochi

### 3. Re-autenticazione NotebookLM
```bash
python -m notebooklm login
```
Poi ri-runnare il backtest: Fabio e Andrea riceveranno anche il contesto
del knowledge base NLM (materiale Valentini, Brookfield, ecc).

### 4. Calibrazione day_type
Il classificatore attuale e' semplice (slope/spread ratio > 0.6).
Possiamo migliorarlo con:
- ATR del giorno precedente come normalizzatore
- Classificazione basata sul VP migration (POC migration < 4 ticks = balance)

### 5. Exit logic avanzata
Attualmente il TradeSimulator usa solo stop/target fissi.
Possiamo aggiungere:
- Trailing stop basato su VP levels (aggiorna target quando HVN viene raggiunto)
- Time stop (chiudi dopo N barre se non si muove)
- Partial exits (50% a target1, 50% a target2)

### 6. Dashboard avanzata
Con piu dati il dashboard puo mostrare:
- Equity curve con drawdown
- Heatmap confidence x setup_type x day_type
- Calendar view (verde/rosso per giorno)
- Per-setup performance breakdown
- Grafico VP levels vs prezzo (candlestick + livelli)

### 7. Ruflo integration (youtube_pipeline)
Ruflo v3.5.75 e' installato in `C:\Users\Mauro\Desktop\youtube_pipeline`.
Cosa offre:
- **100+ agenti specializzati** (coder, tester, reviewer, architect, security)
- **Memoria auto-learn**: il router Q-Learning impara dalle sessioni precedenti
- **Cost optimization**: salta le LLM call per operazioni semplici via WASM (<1ms)
- **Swarm coordination**: piu agenti in parallelo su task indipendenti
- **310+ MCP tools**: integrazione con GitHub, Slack, Linear, ecc.

Per attivarlo in youtube_pipeline:
```bash
cd C:\Users\Mauro\Desktop\youtube_pipeline
npx ruflo@latest init --wizard    # setup guidato
npx ruflo@latest doctor           # diagnostica
claude mcp list                   # verifica ruflo Connected
```

Poi usare Claude Code normalmente: Ruflo agisce in background attraverso
il sistema di hooks, instradando i task agli agenti giusti.

---

## File chiave del progetto

| File | Ruolo |
|------|-------|
| `run_backtest.py` | Entry point, argparse, stampa risultati |
| `src/backtest_runner.py` | Loop principale per giorno e candidato |
| `src/data_loader.py` | Legge CSV DataBento, filtra simbolo front-month |
| `src/bar_aggregator.py` | Aggrega tick in barre 1min/5min |
| `src/volume_profile.py` | POC, VAH, VAL, HVN, LVN |
| `src/session_context.py` | IB, day_type, finestre temporali NY |
| `src/candidate_detector.py` | Big trades + proximity VP levels |
| `src/agents/fabio_agent.py` | Agente primario (direzione, confidence, setup) |
| `src/agents/andrea_agent.py` | Agente di conferma (footprint IBOB) |
| `src/agents/claude_client.py` | Wrapper `claude -p` (no API key) |
| `src/agents/nlm_client.py` | Client NotebookLM (con fallback se auth scaduta) |
| `src/consensus.py` | Fusione segnali Fabio+Andrea |
| `src/trade_simulator.py` | Apre/chiude trade, calcola PnL |
| `src/agent_memory.py` | Log JSON strutturato per candidati e trade |
| `dashboard.py` | Dashboard Dash + Plotly |
| `agent_memory/reasoning_log.jsonl` | Log candidati (1 riga = 1 candidato) |
| `agent_memory/trades_log.jsonl` | Log trade chiusi con PnL |
| `output/week_log.txt` | Log testuale dell'ultima run |

---

## Prossimo passo consigliato

```bash
# 1. Ri-autentica NLM
python -m notebooklm login

# 2. Backtest full (tutti i giorni disponibili)
python run_backtest.py --days 0 > output/full_run.txt 2>&1

# 3. Apri il dashboard
python dashboard.py
# -> http://localhost:8050
```
