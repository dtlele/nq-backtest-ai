# 🤖 Continue Prompt — NQ Backtest AI (Sessione 24 luglio 2026)

Questo prompt serve per **riprendere il lavoro** sul progetto NQ Backtest AI in una sessione futura. Tutto il contesto necessario è qui sotto.

## 📂 Stato corrente del branch

**Branch attivo**: `feature/mechanical-trigger-m5` (10 commit, pushato su origin)
**Ultimo commit**: `008d45f` — "Risk management: daily loss limit (kill switch)"

### File chiave da conoscere
| File | Contenuto |
|---|---|
| `src/agents/fabio_agent.py` | Agente scalper + prompt + validatore narrativa + finalizzazione |
| `src/backtest_runner.py` | Loop di backtest, integrazione RF filter, AUDIT, gestione trade |
| `src/trade_simulator.py` | `step_trade()` con **close-based stop** (no wick hunting) + risk kill switch |
| `src/agents/institutional_bias.py` | Bias engine deterministico (drive/lean/rotational) |
| `src/agents/desk_gates.py` | Pre-gate HARD (TIME, PARTICIPATION, ANCHOR) |
| `src/agents/ml_filter.py` | **Random Forest pre-filter** (score 0-1) |
| `src/agents/daily_map.py` | Daily map LLM (1 call/giorno) |
| `src/agents/mechanical_trigger.py` | Detector pattern geometrici (pullback/squeeze/IVB) |
| `scripts/ml/build_features.py` | Estrae 26 features da 230 giorni di NQ |
| `scripts/ml/train_rf.py` | Addestra RF + TimeSeriesSplit evaluation |
| `data/ml/features_230d.csv` | 14.041 righe × 26 features (label WIN/LOSS) |
| `data/ml/rf_v1.pkl` | Modello RF addestrato (AUC 0.727) |
| `output/backups_2026-07-23/` | **Backup di tutti i 27 log run** (V1-V17) |

### Env vars importanti
| Var | Default | Scopo |
|---|---|---|
| `FABIO_MODE` | `scalper` | Modalità agente (scalper o experts) |
| `REFLEX_MODEL` | `z-ai/glm-5.2` | Modello per proposta long/short |
| `AUDIT_MODEL` | `z-ai/glm-5.2` | Modello per devil's advocate |
| `OPENROUTER_MODEL` | (fallback) | Modello di default se REFLEX/AUDIT non settati |
| `OPENROUTER_API_KEY` | (env) | API key OpenRouter |
| `M5_ONLY` | `0` | Se `1`, salta M1 candidates injection |
| `ML_PRE_FILTER` | `1` | Se `1`, applica RF filter pre-LLM |
| `ML_SCORE_THRESHOLD` | `0.6` | Soglia RF score per passare all'LLM |
| `M5_DEAD_BAR_FILTER` | `1` | Skip candele M5 morte (vol/range/wall) |
| `M5_STREAK_SKIP` | `1` | Skip se 3+ SKIP consecutivi |
| `ENABLE_PARTIAL_TP` | `0` | Se `0`, NO partial TP a 1R (default V16+) |
| `DAILY_LOSS_LIMIT` | `100` | Kill switch: ferma trading se loss giornaliero >= limit |

## 🏆 Risultati dei run passati

| Run | Modalità | Periodo | Trade | Win | Loss | Net P&L |
|---|---|---|---|---|---|---|
| V8b | M1+M5, GLM-5.2 | 04-11/02 | 3 | 1 | 2 | **+$666** ⭐ |
| V14 | close-stop | 10/02 | 1 | 0 | 1 | -$50 |
| V15 | ML filter 0.6 | 10-15/02 | 18 | 0 | 6 | -$300 |
| V16 | no partial TP | 10-24/02 | 9 | ? | 3 | -$150 (6 live) |
| V17 | risk kill | 10/02 | 0 | 0 | 0 | (killato) |

### V8b best run (la baseline da battere)
- SHORT 21555 → -$50 (stop)
- LONG 21781.75 → parzial BE
- **LONG 21867.50 → +$766 (TP hit)** 🎯
- 3 audit tutti confermati, 1 daily stop

## 🎯 Architettura del sistema

```
1. Candidate detector (M5 + M1)         [deterministico]
        ↓
2. Pre-gate HARD (TIME/PARTICIPATION/ANCHOR)  [meccanico]
        ↓
3. ML PRE-FILTER (Random Forest)        [statistico, AUC 0.73]
   - score < 0.6 → SKIP (no LLM call)
        ↓
4. LLM REFLEX (M2.5 / GLM-5.2)         [LLM rapido]
   - decide long/short con conf 0-100
        ↓
5. LLM AUDIT (Devil's Advocate)        [GLM-5.2 con CoT]
   - cerca invalidazione (1 su ~5 reject)
        ↓
6. TRADE OPEN + M1 EXECUTION
   - entry su close M5
   - trailing Donchian 20-bar
   - stop close-based (no wick hunting)
   - APM LLM per gestione attiva
        ↓
7. EXIT (target / trailing stop / close-based stop)
   - kill switch se loss >= $100/giorno
```

## 🐛 Bug noti da fixare in futuro

| # | Bug | Severità | File |
|---|---|---|---|
| 1 | **Audit 100% confirm** — GLM-5.2 con M2.5 conferma sempre, mai rifiuta | 🔴 Critico | `backtest_runner.py` prompt audit |
| 2 | **ML filter 0 skip anche a 0.75** — score alti a candele che poi perdono | 🟠 Alto | `ml_filter.py` features |
| 3 | **Fabio APM chiama LLM troppo spesso** durante gestione trade | 🟡 Medio | `manage_active_trade` |
| 4 | **Run V17 bloccato su startup** — V17.log 57MB pieno di GEX WARNING | 🟡 Basso | log noise |
| 5 | **Quota API esaurita di frequente** ($23/15) | 🟠 Alto | topico gestione |

## 🔬 Numeri chiave del ML model (rf_v1.pkl)

- **AUC CV**: 0.727 ± 0.026 (5-fold time series)
- **Test AUC**: 0.731
- **Test Accuracy**: 71%
- **Win rate base** (no filter): 63%
- **Win rate con filtro th=0.6**: 77.4% (+14.4% edge)
- **Win rate con filtro th=0.7**: 79.6% (+16.6% edge)
- **Win rate con filtro th=0.75**: 82.8% (+19.8% edge)

### Top 5 features (importance)
1. `tod` (time of day) — 32.5%
2. `dist_poc_pct` (distanza da POC) — 12.2%
3. `dist_ib_high` (distanza da IB high) — 5.6%
4. `cv_vol_30m` (volume cumulato 30min) — 5.1%
5. `dist_vwap_pct` (distanza da VWAP) — 4.7%

## 📝 Prompt per continuare in una nuova sessione

Copia-incolla questo per chiedere di continuare il lavoro:

```
Continua il lavoro sul progetto NQ Backtest AI. Il branch attivo è 
`feature/mechanical-trigger-m5` con 10 commit pushati.

CONTESTO: Abbiamo costruito un sistema di trading NQ completo con:
- Bias engine deterministico (drive/lean/rotational)
- Pre-gate HARD (time/participation/anchor)
- Random Forest pre-filter (AUC 0.73)
- Modello LLM ibrido (M2.5 reflex + GLM-5.2 audit)
- Close-based stop (no wick hunting)
- Risk kill switch (DAILY_LOSS_LIMIT)

V8b (run migliore): +$666 con 3 trade su 04-11/02/2025
LONG 21867.50 → +$766 (drive_up + Big Trade 165)

VEDE PRIMA: Leggi docs/CONTINUE_PROMPT.md per lo stato completo.

PROBLEMI NOTI:
1. Audit 100% confirm (GLM-5.2 non rifiuta mai)
2. ML filter 0 skip (troppo permissivo anche a 0.75)
3. Quota API spesso esaurita

PROSSIMI STEP SUGGERITI (scegli uno):
A) Fix audit prompt: renderlo più scettico, target 60-70% confirm
B) Migliorare features ML: aggiungere M1 footprint, bid/ask imbalance
C) Walk-forward serio su 230 giorni per misurare Sharpe/max DD
D) Pivotare a backtester/dashboard (no trading)

PRIORITÀ: Voglio migliorare il run V8b. La baseline da battere è +$666.
```

## 🛠️ Comandi utili per riprendere

```bash
# Setup ambiente
cd C:\Users\Mauro\Documents\nq-backtest-clean
git checkout feature/mechanical-trigger-m5

# Verificare stato
git log --oneline | head -15
git status

# Controllare se run è attivo
ps -ef | grep "run_backtest" | grep -v grep

# Verificare quota API
python -X utf8 -c "
import os, requests
key = os.environ.get('OPENROUTER_API_KEY', '')
r = requests.get('https://openrouter.ai/api/v1/auth/key', 
                 headers={'Authorization': f'Bearer {key}'}, timeout=10)
d = r.json().get('data', {})
print(f'Quota: \${d.get(\"usage\"):.2f} / \${d.get(\"limit\")} -> remaining \${d.get(\"limit\", 0) - d.get(\"usage\", 0):.2f}')
"

# Run V8b replica (best run, M1+M5, GLM-5.2 puro)
REFLEX_MODEL="z-ai/glm-5.2" AUDIT_MODEL="z-ai/glm-5.2" \
  python run_backtest.py --start-date 20250204 --end-date 20250211 \
  --fabio-only --quiet --reset-equity \
  > output/week_v8b_replica.log 2>&1 &

# Run con ML filter (V16-style)
REFLEX_MODEL="minimax/minimax-m2.5" AUDIT_MODEL="z-ai/glm-5.2" \
ML_SCORE_THRESHOLD=0.75 ENABLE_PARTIAL_TP=0 DAILY_LOSS_LIMIT=100 \
  python run_backtest.py --start-date 20250210 --fabio-only --quiet --reset-equity \
  > output/week_v18.log 2>&1 &
```

## 📊 Decisioni da prendere (lasciate in sospeso)

1. **Audit prompt**: renderlo più scettico (es. "rejection rate target 30%")?
2. **ML features**: aggiungere M1 footprint e bid/ask imbalance?
3. **Backtest length**: 1 settimana vs 1 mese vs walk-forward 6 mesi?
4. **Risk management**: $100/giorno kill switch, è abbastanza aggressivo?
5. **Modello production**: GLM-5.2 o M2.5 o ensemble?

## 🔗 Link utili

- Repo: https://github.com/dtlele/nq-backtest-ai
- Branch: `feature/mechanical-trigger-m5`
- Run migliore: `output/week_glm52_scalper_v8b.log`

---

**Data creazione**: 2026-07-24
**Ultima sessione**: V8b → V17 (17 run totali)
**Stato**: codice committato e pushato, edge statistico costruito (AUC 0.73), ma sistema non ancora profittevole
**Prossimo**: decidere direzione (fix audit / walk-forward / pivotare)
