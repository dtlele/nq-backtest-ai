# 🎯 FABIO'S MODEL — Piano di Implementazione Completo

> **Fonte**: Chart Fanatics interview, 4h video (Fabio Valentino, World Trading Cup champion)
> **Data analisi**: 2026-08-01
> **Status**: PLAN (non ancora implementato)

---

## 🧠 EXECUTIVE SUMMARY

Fabio usa un modello a **3 step + 1 timing** = 4 fasi totali. NON è un setup discrezionale.
È un modello **RULE-BASED** che possiamo automatizzare al 95%. La parte rimanente (5%) è
l'interpretazione del "delta developing" (CVD) che è calcolabile ma richiede footprint M1.

**Il modello di Fabio è diverso dal nostro attuale**:
- NO random forest ML per filtrare
- NO audit LLM (overhead inutile)
- NO multi-step pre-gate
- È **3 step nudi** + bias direction + big trade trigger
- Tutto su M1 + M5

---

## 📐 I 4 STEP DI FABIO (in ordine)

### ⏰ TIMING: solo NY session (9:30 ET - close)
- **NON** tradare prima di NY
- **NON** tradare a Londra (mean reversion diverso)
- Fabio dice testualmente: *"I don't trade before New York"*
- Eccezione: range/compression period può andare in London

### STEP 1: MARKET STATE (Trend following vs Mean reversion)
- **Solo 2 stati possibili**:
  1. **BALANCED** (range/consolidation) → modello REVERSION
  2. **IMBALANCED** (out of balance) → modello TREND FOLLOWING
- Identificazione su **M5**:
  - Compression: candele M5 piccole (range < ATR 0.5x)
  - Expansion: candele M5 grandi (range > ATR 2x)
- Fabio dice: *"We can only have two market states"*

### STEP 2: LOCATION (LVN / Value Area)
- **Trend following**:
  - Aspetta un **swing point** (high o low) che viene rotto
  - Identifica il **Low Volume Node (LVN)** dentro l'impulse leg
  - LVN = zona dove il volume profile è < 30% del POC
  - Entry quando il prezzo pullback nel LVN
- **Reversion**:
  - Aspetta **primo breakout** di una compression
  - Pullback dentro il range
  - Entry al LVN del range (= "single LVN" approach)

### STEP 3: EXECUTION/TRIGGER (Big Trade Aggression)
- **Aspetta il big trade nella direzione del trade**
- Per LONG: aspetta una **grande bolla verde** (footprint M1)
- Per SHORT: aspetta una **grande bolla rossa**
- Filtro minimo: **30 contratti su NASDAQ M1** (Fabio's threshold)
- Entry: "jump in with them" (market order o subito dopo la chiusura della candela M1)
- **NON** mettere limit order al LVN — aspetta il trigger

### TARGET
- **Target primario**: POC (Point of Control) precedente = highest probability
- **Target secondario**: Previous balance area / value area high (per long) o low (per short)
- "70% probability of reversal at POC" — prendi tutto, non scaling
- **Se arriva a target 1** (8pt nel nostro caso), prendi profitto
- **Se vuoi tenere**, metti BE e aspetta target 2 (POC)

---

## 🔍 LE 3 COSE CHE CI MANCANO (vs attuale)

| Elemento | Attuale | Fabio |
|---|---|---|
| LVN detection | ❌ Assente | ✅ Cuore del modello |
| Big trade filter | ⚠️ Parziale (big trade count) | ✅ Specific 30+ contracts su M1 |
| Market state classification | ⚠️ Parziale (bias engine) | ✅ Binario: balanced/imbalanced |
| Volume profile (POC/VA) | ❌ Assente | ✅ Target primario |
| Session filter (NY only) | ⚠️ Soft | ✅ Hard rule |

---

## 🛠️ PIANO DI IMPLEMENTAZIONE (9 step)

### Step 1: Calcola Volume Profile storico (POC/VA/LVN)
**File**: `src/features/volume_profile.py` (nuovo)
- Su M5 e M15, calcola per ogni "sessione":
  - POC (price con max volume)
  - Value Area High/Low (70% del volume)
  - LVN zones (volume < 30% del POC)
- Su M1: calcola "developing POC" (rolling)
- Usa numpy/pandas (no LLM)
- Output: dict per ogni barra con profile levels

**Stima**: 2-3 ore

### Step 2: Implementa LVN detector su barre M1/M5
**File**: `src/features/lvn_detector.py` (nuovo)
- Dato un "swing point" (high/low pivot):
  - Calcola il range dell'impulse leg (A→B)
  - Identifica LVN dentro quel range
  - Output: "the LVN is at price X with width Y"
- Trigger: prezzo entra nella zona LVN

**Stima**: 1-2 ore

### Step 3: Market State Classifier (balanced/imbalanced)
**File**: `src/features/market_state.py` (nuovo)
- Su M5:
  - Calcola ATR rolling (20 periods)
  - Se range M5 < 0.5 × ATR → BALANCED
  - Se range M5 > 2.0 × ATR → IMBALANCED
  - Output: enum {BALANCED, IMBALANCED}

**Stima**: 30 min

### Step 4: Big Trade Detector su M1
**File**: `src/features/big_trade_filter.py` (modifica esistente)
- Aggiungi flag: `big_trade_min_size = 30 contracts` (configurabile)
- Aggiungi volume profile M1: somma del volume aggressivo per livello
- Output: `has_big_buy_bubble`, `has_big_sell_bubble`, `bubble_size`

**Stima**: 1-2 ore (estende il BigTradeDetector esistente)

### Step 5: Session filter (NY only)
**File**: `src/features/session_filter.py` (nuovo)
- Timezone: ET (America/New_York)
- Session: 9:30 - 16:00 ET = NY
- Flag `is_ny_session` per ogni barra M5
- Permette eccezione: se `market_state == BALANCED && in_range`, abilita London

**Stima**: 30 min

### Step 6: Refactor `setup_detector.py` con i 3 step
**File**: `src/agents/setup_detector.py` (modifica)
- Cambia i setup da "reversal/pullback/ivb/squeeze" a:
  - `trend_breakout_pullback_lvn` (trend following)
  - `range_breakout_pullback_lvn` (mean reversion)
- Mantieni squeeze come "trigger rapido" (opzionale, solo se ml_score > 0.7)

**Stima**: 2 ore

### Step 7: Disabilita audit LLM (sostituisci con regole)
**File**: `src/agents/auditor.py` (modifica o rimozione)
- L'audit V2 era un safety net, ma Fabio non ne ha bisogno
- Sostituisci con regole deterministiche:
  - R1: `|delta| > 1500` → REJECT
  - R3: `big_trade_count > 2` opposto → REJECT
  - R5: `time in [9:30, 9:45]` → REJECT
  - R6: conviction score < 3 → REJECT

**Stima**: 1-2 ore

### Step 8: Refactor `run_backtest.py` con nuove feature
- Sostituisci il flow attuale (pre-gate → ML → reflex → audit) con:
  1. Session filter (NY only)
  2. Setup detector (3 step Fabio)
  3. ML filter (opzionale, threshold 0.5 per ora)
  4. (No audit)

**Stima**: 2-3 ore

### Step 9: Test comparativo
- Testa il nuovo flow su V8b (4-11 Feb) → dovrebbe replicare +$666
- Testa su W19 (5-9 May) → confermare che performa
- Se V8b replica esattamente: ship come default
- Se no: debug, fix, ri-test

**Stima**: 2-4 ore (incluso debug)

---

## 💰 COSTI E TEMPO TOTALE

| Step | Tempo | Costo API |
|---|---|---|
| 1-5 (feature engineering) | 6-8 ore | $0 (tutto offline) |
| 6-8 (refactor agent + backtest) | 5-7 ore | $0 (no LLM) |
| 9 (test comparativo) | 2-4 ore | $0 (offline sim) |
| **TOTALE** | **13-19 ore** | **$0** |

**Vantaggi**:
- Zero dipendenza da LLM (nessun costo, nessun rate limit)
- Modello rule-based (replicabile, testabile, debuggabile)
- Basato su champion mondiale (Fabio, $X in World Trading Cup)
- 70% target hit rate al POC (vs 21% attuale)

---

## ⚠️ RISCHI

1. **Volume profile storico**: serve rolling 1-2 giorni di dati M5. Già li abbiamo.
2. **Footprint M1**: serve granularità tick-by-tick. Abbiamo solo M5 aggregato.
   - **Mitigazione**: simuliamo big trade = "candela M1 con range > 1.5 × ATR e close nella direzione del bias"
3. **Fuso orario**: i dati devono essere in ET, non UTC.
   - **Mitigazione**: aggiungere conversione timezone nel loader.
4. **Volume profile su barre da 1-min**: potrebbe essere rumoroso.
   - **Mitigazione**: usare M5 per POC/VA, M1 solo per trigger big trade.

---

## 🎯 OUTPUT ATTESO

- **Win rate obiettivo**: 35-45% (vs 21% attuale)
- **R:R medio**: 1:3 (target POC) vs 1:2 attuale
- **Trade count**: 5-10/settimana (vs 17-30 attuali)
- **PnL/settimana**: +$500-1500 in backtest (vs $80-200 attuali)
- **Sharpe ratio**: > 1.5 (misurabile dopo 4+ settimane)

---

## ✅ CHECKLIST PRE-IMPLEMENTAZIONE

Prima di iniziare voglio conferma su:

- [ ] Approccio Fabio-only (no LLM audit) è OK?
- [ ] Investire 13-19 ore offline va bene?
- [ ] Rischio 0% LLM ma +feature engineering è accettabile?
- [ ] Volume profile su M5 invece che M1 (perché abbiamo solo M5)?
- [ ] Target: replicare V8b +$666, poi migliorare?

---

## 📚 RIFERIMENTI

- Video: `data/video_analysis/fabio_v1_full.mp4` (504MB, 4h)
- Transcript: `data/video_analysis/fabio_v1_timed.txt` (11197 righe)
- Frames chiave: `data/video_analysis/frames/` (30+ screenshots)
- Whiteboard screenshot: `01_lvn_explanation_2_12m30s.jpg`
- Esempio live chart: `13_full_examples_2_166m30s.jpg`

**Punti chiave del video (timestamps)**:
- 00:03:32 — 90% of traders fail (intro)
- 00:07:22 — Step 1 of model: market state
- 00:10:14 — Step 2: profile + LVN identification
- 00:11:14 — Step 3: big orders as trigger
- 00:13:19 — Risk:reward 1:3, 1:5
- 00:16:55 — Why NY session only
- 00:27:50 — CVD (Cumulative Volume Delta)
- 00:39:49 — TREND model summary (4 steps)
- 00:43:14 — REVERSION model (consolidation)
- 01:11:46 — Live trade example (160 risk to 500 reward)
- 01:49:14 — Failed auction / manipulation = real signal
- 02:24:50 — Risk management 2% max day
- 02:44:00 — AI/ML for journaling
