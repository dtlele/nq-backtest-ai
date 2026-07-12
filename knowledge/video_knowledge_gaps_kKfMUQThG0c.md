# Knowledge Gaps: Order Flow: Spoofing And Large Orders.

**Video**: kKfMUQThG0c

---

## Concetti Estratti

# Estrazione Strutturata — Order Flow: Spoofing And Large Orders (SPECULATORSETH)

---

## 1. CONCETTI CHIAVE

### 1.1 SPOOFING
**Definizione operativa**: Manipolazione del book in cui un attore istituzionale inserisce un ordine limit di dimensione massiccia su un lato del DOM (Bid o Ask) con l'intenzione predefinita di **non eseguirlo mai**. Lo scopo è creare un'illusione di pressione/assorbimento per indurre i retail a reagire nella direzione opposta.

**Come si legge sul grafico/DOM**:
- Barra di size **enormemente sproporzionata** rispetto al contesto (es. muro blu di Ask da 2000+ contratti in un book dove la size media è 200-700).
- L'ordine appare **improvvisamente** (non cresce gradualmente) e scompare **prima che il prezzo lo raggiunga**.
- Visivamente: "blocco" statico di colore solido su Bookmap che si dissolve senza essere testato o che viene attraversato in millisecondi.

**Esempio dal video (19.4s–22.0s e 37.8s–38.3s)**:
- Muro blu (Ask/resistenza) che appare come barriera invalicabile → viene "tirato giù" senza esecuzione.
- Muro rosso (Bid/supporto) massiccio sulla sinistra che funge da "paper wall" (muro di carta).

---

### 1.2 PULLING
**Definizione operativa**: Atto di **ritirare un ordine passivo (limit) dal book** prima dell'esecuzione. È il "secondo atto" dello spoofing, ma può anche essere una pratica legittima di risk management.

**Differenziazione critica**:
| Tipo | Descrizione | Lettura |
|------|-------------|---------|
| **Pulling manipolativo** | Ordine inserito con intenzione predefinita di cancellarlo per creare percezione | Appare e scompare velocemente, size anomala |
| **Pulling legittimo** | Trader genuino che rivede la propria tesi e cancella l'ordine | Size coerente con il flusso, tempistica non "da manuale" |

**Come si legge sul grafico/DOM**:
- Una size significativa che era stabile nel DOM **si azzera istantaneamente** prima che il prezzo la raggiunga.
- Flickering rapidissimo (refresh ad alta frequenza) che evidenzia la scomparsa.
- Spesso accompagnato da un **immediato movimento violento nella direzione opposta** al muro appena ritirato (il mercato "corre" verso la liquidità che ora è scoperta).

---

### 1.3 ICEBERG ORDERS (Ordini Iceberg)
**Definizione operativa**: Ordine limit di grandi dimensioni suddiviso in "fette" (slice) più piccole visibili sul DOM, che vengono **automaticamente reintegrate** man mano che vengono eseguite. Solo una porzione minima (la "punta") è visibile; il resto è nascosto.

**Come si legge sul grafico/DOM**:
- Size piccola e costante a un determinato livello di prezzo che **non si esaurisce mai** nonostante ripetute esecuzioni.
- Su Bookmap: barra che resta "piena" o si rigenera continuamente nonostante le aggressioni del mercato.
- Pattern tipico: lo stesso livello continua ad assorbire volumi elevati senza che la size visibile cali sotto una certa soglia.

**Comportamento chiave** (coerente con [AMT_CORE_15]):
- Rappresenta **difesa istituzionale passiva genuina** (a differenza dello spoof).
- Crea "Effort vs No Result": ordini aggressivi colpiscono il livello ma il prezzo non progredisce.
- Mai tradare contro un iceberg confermato: cercare entry nella direzione della difesa dopo che il flusso aggressivo rallenta.

---

### 1.4 DISTINZIONE FONDAMENTALE: Iceberg vs Spoofing

| Caratteristica | Spoofing | Iceberg |
|----------------|----------|---------|
| **Intento** | Ingannevole (ritirare prima dell'esecuzione) | Genuino (eseguire gradualmente) |
| **Comportamento** | Appare e scompare senza essere testato | Resta presente e si rigenera dopo ogni test |
| **Reazione al test del prezzo** | Sparisce prima del contatto | Assorbe e continua a difendere |
| **Effetto sul mercato** | Genera movimento violento al "pull" | Blocca il movimento (assorbimento) |
| **Implicazione operativa** | Setup di breakout/continuation dopo il pull | Setup di mean reversion/bounce al livello |

---

## 2. REGOLE OPERATIVE ESPLICITE

### 2.1 Regole sullo Spoofing
1. **"Non fidarti mai di ciò che vedi staticamente sul DOM"** — la size esposta non è evidenza di intenzione reale.
2. **"La verità sta nel movimento"** — solo l'azione dinamica (pull/esecuzione) rivela le vere intenzioni.
3. **Non posizionare MAI stop loss dietro ai muri fittizi** (coerente con [AMT_CORE_04]) — questi livelli sono target primari per il pulling e generano stop hunt sistematici.
4. **Se uno spoof viene confermato (ordine ritirato), prepararsi per un movimento violento nella direzione opposta al muro**.
5. **Osservare tre elementi dinamici**: (a) velocità di apparizione, (b) durata della permanenza, (c) scomparsa prima del test.

### 2.2 Regole sul Pulling
6. **Un muro che scompare senza essere testato è un segnale direzionale forte** — la liquidità è stata "rimossa", il mercato può ora muoversi in quella direzione.
7. **Dopo il pulling, attendere la conferma del movimento** (delta aggressivo nella nuova direzione) prima di entrare — non anticipare ciecamente.

### 2.3 Regole sugli Iceberg
8. **Mai tradare contro un iceberg confermato** (coerente con [AMT_CORE_15]) — è una difesa istituzionale genuina.
9. **Iceberg = "Effort vs No Result"** — se vedi volumi aggressivi che non producono progresso del prezzo, c'è probabilmente un iceberg che assorbe.
10. **L'iceberg è un livello di supporto/resistenza "vivo"** — più affidabile di una linea statica tracciata sul grafico.

### 2.4 Timing e Contesto
11. **Massima cautela durante l'asta di apertura** (RTH open) — momento di massima manipolazione del book, volatilità estrema della liquidità passiva.
12. **Maggior efficacia dello spoof in mercati con elevata partecipazione retail** — la manipolazione psicologica funziona solo se c'è chi reagisce alla size visibile.

---

## 3. SETUP

### 3.1 SETUP "SPOOF REVERSAL" (dopo pulling confermato)

| Fase | Dettaglio |
|------|-----------|
| **Contesto** | Book in prossimità di livelli tecnici chiave; partecipazione retail elevata; mercato in stato di Balance ([AMT_CORE_01]) o in early-stage di esplorazione |
| **Trigger** | Muro massiccio (Ask se si cerca long, Bid se si cerca short) che **appare improvvisamente** e poi **scompare prima che il prezzo lo raggiunga** |
| **Conferma** | (a) Movimento aggressivo del prezzo nella direzione opposta al muro ritirato; (b) Delta flip coerente (positivo dopo pulling di Ask wall, negativo dopo pulling di Bid wall); (c) Follow-through su 2-3 candele |
| **Entry** | Sul pullback dopo il "pull" iniziale, oppure sul break della struttura short-term post-pulling (non inseguire il primo spike) |
| **Stop** | **Strutturale, NON dietro al massimo/minimo del wick** ([AMT_CORE_04]) — dietro al cluster HVN successivo o alla POC, nella "pancia" del volume profile |
| **Target 1** | [AMT_CORE_06] — bordo opposto del Value Area o POC, con uscita 50% |
| **Target 2** | Estremo opposto della sessione / prossimo HVN ledge |
| **Sizing** | [AMT_CORE_05] — ridurre i contratti proporzionalmente alla distanza dello stop |

---

### 3.2 SETUP "ICEBERG BOUNCE" (trading con l'assorbimento istituzionale)

| Fase | Dettaglio |
|------|-----------|
| **Contesto** | Prezzo si avvicina a un livello chiave (IBH/IBL, VAH/VAL, session high/low) con size insolitamente persistente e costante a quel livello |
| **Trigger** | Ripetute esecuzioni contro il livello senza che la size visibile si esaurisca + delta aggressivo che non produce progresso (Effort vs No Result) |
| **Conferma** | (a) Second drive al livello con volume ma senza breakout ([AMT_CORE_03], [AMT_CORE_14]); (b) Delta flip al secondo test; (c) Rejection signature sulla candela (wick significativo, [AMT_CORE_10]) |
| **Entry** | Sul Second Drive rejection, dopo conferma delta |
| **Stop** | **Dietro il livello difeso dall'iceberg, ma con buffer strutturale** ([AMT_CORE_12]) — non esattamente sullo spike estremo |
| **Target 1** | Opposite Value Area border o mid-range POC ([AMT_CORE_06]) |
| **Target 2** | Estremo opposto della sessione |

---

### 3.3 SETUP "OPEN AUCTION SPOOF DETECTION"

| Fase | Dettaglio |
|------|-----------|
| **Contesto** | Primi minuti del RTH (09:30–09:45 EST) — massima instabilità del book |
| **Trigger** | Muri massicci su entrambi i lati del DOM che cambiano dimensione e posizione rapidamente, senza coerenza con il flusso aggressivo |
| **Filtro** | [AMT_CORE_01] — saltare se il mercato è in stato misto/transition; [AMT_CORE_02] — non operare su wick breakouts dell'IB senza conferma body + delta |
| **Azione** | Osservazione pura (no trade): identificare quale lato "svuota" prima → direzione probabile del primo impulso |

---

## 4. STRUMENTI E CONFIGURAZIONE

### 4.1 Piattaforme
- **Bookmap** (o equivalente Heatmap/DOM visualizer) — piattaforma principale per la lettura dello spoofing, pulling e iceberg
- **Piattaforma secondaria**: grafici a candele tradizionali con indicatori tecnici (oscillatori, medie) su setup multi-monitor
- **Picture-in-Picture**: finestra sovrapposta per la webcam del trader durante la spiegazione

### 4.2 Configurazione del DOM

| Componente | Setup |
|------------|-------|
| **Lato Rosso (sinistra)** | Offerte Bid (limit buy orders) |
| **Centro** | Scala prezzi (Ladder) |
| **Lato Blu (destra)** | Offerte Ask (limit sell orders) |
| **Colonne size** | Contratti a ogni livello di prezzo |
| **Visualizzazione** | Barre orizzontali con lunghezza/spessore proporzionale alla size |
| **Refresh** | Alta frequenza (flickering rapidissimo dei numeri) |
| **Range size visibili** | Da poche unità a migliaia (es. 237, 705, 2076) |

### 4.3 Configurazione Multi-Monitor
- Monitor 1: Bookmap / Heatmap con DOM
- Monitor 2: Grafico a candele del future/strumento con indicatori
- Monitor 3 (opzionale): DOM ladder classico per confronto numerico

### 4.4 Strumenti di Mercato Implicati
- **E-mini S&P 500 (ES) o NQ Nasdaq** o **YM Dow Futures** (range prezzi 29520–29522 coerente con YM marzo 2020 o strumenti simili)
- Contesto futures americani (RTH + ETH)

### 4.5 Differenziazione Visiva Critica

```
ICEBERG                          SPOOFING
────────                         ─────────
Size costante al livello         Size sproporzionata che appare/scompare
Si rigenera dopo i test          Sparisce al primo contatto
Assorbe volumi                   Non esegue mai
Difende il livello               Inganna sulla direzione
→ Bounce setup                   → Breakout/continuation setup dopo pull
```

---

## NOTE DI COLLEGAMENTO CON LE REGOLE AMT ATTIVE

| Regola Attiva | Applicazione al video |
|---------------|----------------------|
| [AMT_CORE_01] Market State Filter | Lo spoofing è più efficace in stati misti/transition; evitare di operare in questi contesti |
| [AMT_CORE_02] IBOB Breakout Validation | Wick oltre IB senza body close = possibile spoof sweep, attendere delta confirmation |
| [AMT_CORE_03/14] Second Drive | Conferma operativa: dopo lo spoof e il pull, attendere il secondo drive per entry |
| [AMT_CORE_04/12] Stop Placement | Stop mai dietro a wick estremi di spoof sweep; nascondere in HVN/POC |
| [AMT_CORE_05] Dynamic Sizing | Stop più ampio (a causa di volatilità da open) → meno contratti |
| [AMT_CORE_06] Scale Out | Target 1 a VAH/VAL/POC con 50% e BE sul resto |
| [AMT_CORE_07/15] Absorption Filter | Iceberg = absorption genuina; spoof ≠ absorption (è illusione) |
| [AMT_CORE_11] Failed Auction | Lo spoof ritirato vicino a estremi chiave genera Failed Auction reversal |

---

## Gap vs Sistema Corrente

# 📊 Analisi Comparativa: Video "Spoofing and Large Orders" vs Sistema Corrente

---

## 1️⃣ CONCETTI DEL VIDEO NON PRESENTI (o sotto-rappresentati) NEL SISTEMA

| # | Concetto Video | Presente nel Sistema? | Gap Critico |
|---|----------------|----------------------|-------------|
| 1 | **SPOOFING** come categoria distinta con definizione operativa precisa | ❌ **ASSENTE** — il sistema parla di "paper wall" solo nel glossario suggerimenti, senza regola attiva | 🔴 **ALTO** |
| 2 | **PULLING** manipolativo vs legittimo (distinzione operativa) | ❌ **ASSENTE** — nessuna euristica per distinguere i due casi | 🔴 **ALTO** |
| 3 | **ICEBERG ORDERS** con criteri di detection specifici (size costante, auto-replenishment) | ⚠️ **PARZIALE** — [AMT_CORE_15] menziona iceberg ma solo in forma generica, senza criteri di detection (size ratio, refresh rate, persistence) | 🟡 **MEDIO** |
| 4 | **Matrice di distinzione Spoofing vs Iceberg** (intento + comportamento + persistenza) | ❌ **ASSENTE** — non c'è framework decisionale | 🔴 **ALTO** |
| 5 | **Criteri visivi di Bookmap** (bar colorate, flickering, scomparsa improvvisa) | ❌ **ASSENTE** — il sistema non ha un vocabolario visivo per il DOM | 🟡 **MEDIO** |
| 6 | **Reazione post-pulling** (il mercato "corre" verso la liquidità scoperta) | ⚠️ **PARZIALE** — coperto indirettamente da "liquidity void" ma senza trigger esplicito | 🟡 **MEDIO** |

---

## 2️⃣ REGOLE OPERATIVE SUGGERITE (candidate per `dynamic_rules.json`)

### 🟥 PRIORITÀ ALTA

#### **[AMT_CORE_16] Spoofing Detection Filter**
```
TOPIC: Spoofing Detection & Contrarian Reaction
CONDIZIONE: Quando sul DOM appare un muro di size anomala (≥ 3x la size media 
del livello adiacente) che si dissolve PRIMA che il prezzo lo raggiunga 
(sopravvivenza < 30 secondi o cancellazione al primo approccio), 
classificare come SPOOF.
AZIONE: 
  - NON prendere trade nella direzione in cui il muro "spingeva" (è una trappola)
  - Preparare entry CONTRARIAN verso la direzione opposta quando:
      (a) il muro viene ritirato E
      (b) appare flusso aggressivo (delta) nella direzione opposta
  - Stop loss strutturale oltre l'estremo del wick lasciato dallo spoof
PRIORITY: ALTA — lo spoofing è una delle manipolazioni più redditizie da 
identificare per il retail.
```

#### **[AMT_CORE_17] Pulling Classification & Reaction**
```
TOPIC: Manipulative Pulling vs Legitimate Pulling
CONDIZIONE: Differenziare i due tipi di pulling:
  - MANIPOLATIVO: size > 3x media + durata < 60s + scomparsa al primo test + 
    movimento violento immediato nella direzione opposta
  - LEGITTIMO: size coerente + durata variabile + cancellazione graduale + 
    nessun "scatto" violento post-cancellazione
AZIONE:
  - Su pulling manipolativo confermato: cercare entry nella direzione del 
    movimento post-pull (il mercato corre verso la liquidità scoperta)
  - Target: prossimo HVN / VAH-VAL / estremo di sessione
  - Stop: dietro il livello dello spoof ritirato + 5-10 tick di buffer
PRIORITY: ALTA — il pulling manipolativo è un segnale direzionale forte.
```

#### **[AMT_CORE_18] Iceberg Absorption vs Spoofing Disambiguation**
```
TOPIC: Iceberg vs Spoof Real-Time Classification
CONDIZIONE: Per classificare un muro DOM come ICEBERG (difesa genuina) 
invece che SPOOF (manipolazione):
  (a) La size visibile rimane COSTANTE nonostante esecuzioni ripetute
  (b) Il volume eseguito totale al livello è ≥ 5x la size visibile iniziale
  (c) La size visibile si REINTEGRA automaticamente (refresh < 2s)
  (d) Il prezzo NON riesce a progredire attraverso il livello (effort vs result)
AZIONE:
  - Se ≥ 3/4 condizioni soddisfatte: trattare come ICEBERG CONFIRMED
  - [Coerente con AMT_CORE_15]: MAI tradare contro l'iceberg
  - Entry: solo nella direzione della difesa (bounce) dopo che il flusso 
    aggressivo rallenta (delta flip + volume decline)
  - Stop: strutturale oltre l'iceberg + HVN dietro
PRIORITY: ALTA — previene i false breakout contro le difese istituzionali reali.
```

---

### 🟧 PRIORITÀ MEDIA

#### **[AMT_CORE_19] DOM Anomaly Context Filter**
```
TOPIC: DOM Size Anomaly Detection
CONDIZIONE: Calcolare la size media del book al livello corrente. 
Se appare una size > 3x la media, MARCARLA come potenziale anomalia 
(spoof, iceberg, o wall istituzionale).
AZIONE: 
  - Sospensione momentanea del trading (no nuovi entry) finché l'anomalia 
    non è classificata (spoof/iceberg/legitimate)
  - Riduzione del 50% della size standard per evitare di essere colpiti da 
    manipolazioni durante la classificazione
PRIORITY: MEDIA — agisce come meta-regola di risk management.
```

#### **[AMT_CORE_20] Post-Pull Vacuum Trade**
```
TOPIC: Liquidity Vacuum After Spoof Withdrawal
CONDIZIONE: Dopo la conferma di un pulling manipolativo (muro ritirato), 
misurare il delta aggressivo nei successivi 3-5 secondi.
AZIONE:
  - Se delta è fortemente direzionale (|cumulative_delta| > 2x media) 
    nella direzione opposta al muro ritirato: confermato "vacuum effect"
  - Entry in direzione del delta con target al prossimo HVN/VAB
  - Time stop: 30 secondi massimi per vedere il movimento, altrimenti exit
PRIORITY: MEDIA — sfrutta la reazione istituzionale post-spoof.
```

---

## 3️⃣ AGGIORNAMENTI CONCRETI AI PROMPT

### 📄 Aggiornamento `andrea_agent.py` (Knowledge Base)

Aggiungere una nuova sezione al knowledge dict:

```python
# Sezione Order Flow Anomalies (da video SPECULATORSETH)
ORDER_FLOW_KNOWLEDGE = {
    "spoofing": {
        "definition": "Massive limit order placed with NO intent to execute, "
                     "to create illusion of pressure and induce retail to react opposite.",
        "dom_signature": "Size ≥ 3x adjacent levels, appears suddenly, "
                        "disappears before price reaches it (survival < 30s).",
        "trading_implication": "CONTRARIAN signal. Trade opposite to spoof direction "
                              "once it's pulled and aggressive flow confirms."
    },
    "pulling": {
        "manipulative": "Size anomaly + short duration + violent move after cancel.",
        "legitimate": "Size consistent + variable duration + gradual cancel + no spike.",
        "trading_implication": "Manipulative pull = strong directional signal in "
                              "the direction of post-cancel move."
    },
    "iceberg": {
        "definition": "Large order split into small visible slices that auto-refill.",
        "dom_signature": "Constant visible size despite executions, auto-refresh < 2s, "
                        "total executed volume ≥ 5x visible size, no price progress.",
        "trading_implication": "Genuine institutional defense. NEVER trade against. "
                              "Bounce in defense direction only after aggressive flow slows."
    },
    "spoof_vs_iceberg_matrix": {
        "intent": {"spoof": "deceptive", "iceberg": "genuine execution"},
        "persistence": {"spoof": "cancels before test", "iceberg": "absorbs repeatedly"},
        "size_behavior": {"spoof": "size stays full then vanishes", 
                         "iceberg": "size refills continuously"},
        "price_response": {"spoof": "price explodes through once pulled", 
                          "iceberg": "price stalls/dies at level"}
    }
}
```

### 📄 Aggiornamento `audit_agent.py` (Payload Schema)

Aggiungere questi campi al prompt payload per Gemini:

```python
prompt_payload = {
    # ... campi esistenti ...
    "dom_anomaly_events": [
        {
            "timestamp": "...",
            "type": "spoof | iceberg | pulling_manipulative | pulling_legitimate",
            "side": "bid | ask",
            "size_ratio": 3.5,  # size vs book average
            "survival_seconds": 15,
            "post_event_delta": -1200,  # cumulative delta after event
            "price_reaction": "violent_break | stalled | reversed"
        }
    ],
    "dom_anomaly_classification_accuracy": 0.0,  # 0-1 score
    "iceberg_respect_rate": 0.0,  # % of icebergs we did NOT trade against
    "spoof_contrarian_winrate": 0.0,  # % of contrarian post-spoof trades won
}
```

Aggiungere inoltre all'output JSON atteso una nuova sezione:

```json
{
  "new_rule_proposal": {
    "id": "AMT_CORE_XX",
    "topic": "DOM Spoofing Detection",
    "condition": "...",
    "action": "skip_trade | require_delta_confirmation | adjust_stop_placement | reduce_contracts",
    "priority": "ALTA | MEDIA | BASSA",
    "rationale": "...",
    "supporting_trades": 0,
    "needs_more_data": true
  }
}
```

### 📄 Aggiornamento `dynamic_rules_manager.py` (Validator)

Estendere `validate_dynamic_rule()` per accettare il nuovo `action` type e validare la coerenza:

```python
VALID_ACTIONS = {
    "skip_trade",
    "require_delta_confirmation", 
    "adjust_stop_placement_beyond_nearest_absorption",
    "reduce_contracts_or_skip",
    # NUOVI per il contesto DOM:
    "contrarian_entry_on_pull",      # post-spoof
    "bounce_entry_on_iceberg_defense", # dopo conferma iceberg
    "size_reduction_pending_classification"  # anomalia non classificata
}

VALID_TOPICS = {
    "Market State Filter", "IBOB Breakout Validation", "Failed Auction & Reversals",
    "Surgical Stop Placement", "Dynamic Position Sizing", "Scale Out & Trade Management",
    "Institutional Absorption Filter", "Volume Profile Ledge Pullbacks",
    "Stop Placement in Trending Markets", "Pullback Rejection Confirmation",
    "Failed Auction Reversal from Big Trades", "Stop Placement in Strong Trends",
    "AVWAP Pullback in Trend Day", "Failed Auction Second Drive Confirmation",
    "DOM Iceberg and Absorption Filter",
    # NUOVI:
    "DOM Spoofing Detection",
    "DOM Pulling Classification",
    "DOM Iceberg vs Spoof Disambiguation",
    "DOM Anomaly Context Filter",
    "Post-Pull Vacuum Trade"
}
```

---

## 4️⃣ GAP ANALYSIS — COSA MANCA ANCORA DA IMPARARE

### 🎯 Prossimi Video da Cercare (in ordine di priorità)

| # | Argomento Mancante | Perché è Critico | Query di Ricerca Suggerita |
|---|---------------------|------------------|----------------------------|
| 1 | **Stacked Imbalances & Delta Divergence** | Il sistema ha delta ma non ha regole formali su divergenze (prezzo↑ + delta↓) | `"order flow delta divergence trading bookmap"` |
| 2 | **Absorption vs Exhaustion real-time** | [AMT_CORE_07] parla di absorption ma servono criteri quantitativi (delta rate, volume rate, price velocity) | `"absorption vs exhaustion order flow tutorial"` |
| 3 | **Footprint Charts & Bar Order Flow** | Il sistema non parla di footprint (bid/ask volume per singola barra) | `"footprint chart bid ask volume analysis"` |
| 4 | **Tape Reading & Speed of Tape** | Manca lettura del tempo/esecuzione (es. 100 contratti in 200ms = aggressione) | `"tape reading speed of tape day trading"` |
| 5 | **Volume Profile TPO (Time Price Opportunity)** | Il sistema ha solo Volume Profile classico; il TPO aggiunge la componente tempo | `"TPO market profile trading tutorial"` |
| 6 | **Composite Man Theory (ICT-style)** | Per capire la *narrative* istituzionale che il sistema potrebbe non cogliere | `"composite man ICT smart money concepts"` |
| 7 | **Liquidity Sweeps vs Stop Hunts (distinzione)** | [AMT_CORE_03] tratta i sweep ma non distingue tipologie | `"liquidity sweep vs stop hunt order flow"` |
| 8 | **Opening Range (OR) vs Initial Balance (IB)** | Il sistema ha IB ma non OR (5min/15min opening range) | `"opening range breakout vs initial balance"` |
| 9 | **Volume Weighted Average Price (VWAP) Strategies** | AVWAP c'è ([AMT_CORE_13]) ma VWAP standard manca | `"VWAP day trading strategies institutional"` |
| 10 | **News & Economic Data Order Flow** | C'è solo il suggerimento generico su 09:45/10:00, manca framework reattivo | `"FOMC news order flow reaction trading"` |

### 🧠 Aree Concettuali da Approfondire

```
┌─────────────────────────────────────────────────────────────┐
│  ATTUALE (buona copertura):                                 │
│  ✓ Auction Market Theory (Balance/Imbalance)                │
│  ✓ Volume Profile (POC, VA, HVN, LVN)                       │
│  ✓ Initial Balance (IB)                                     │
│  ✓ Delta & Absorption (base)                                │
│  ✓ AVWAP per trend day                                      │
│  ✓ DOM Iceberg (parziale)                                   │
│                                                              │
│  MANCANTE (gap da colmare):                                  │
│  ✗ Spoofing & Pulling detection                              │
│  ✗ Footprint Charts / Bar Order Flow                         │
│  ✗ TPO Market Profile                                        │
│  ✗ Divergenze price/delta sistematiche                       │
│  ✗ Speed of Tape / Execution analytics                       │
│  ✗ Composite Man narrative (ICT)                             │
│  ✗ Differenziazione Sweep vs Stop Hunt                       │
│  ✗ Opening Range (OR) come alternativa a IB                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 RIEPILOGO ESECUTIVO

| Categoria | Intervento | Priorità | Effort Stimato |
|-----------|------------|----------|----------------|
| **Nuove Regole Dynamic** | [AMT_CORE_16] Spoofing, [AMT_CORE_17] Pulling, [AMT_CORE_18] Iceberg/Spoof Disambiguation | 🔴 ALTA | 2-3 ore |
| **Knowledge Base Update** | Aggiungere `ORDER_FLOW_KNOWLEDGE` dict in `andrea_agent.py` | 🔴 ALTA | 1 ora |
| **Audit Schema** | Estendere `audit_agent.py` payload con `dom_anomaly_events` | 🟡 MEDIA | 1 ora |
| **Validator Update** | Aggiungere nuovi `actions` e `topics` in `dynamic_rules_manager.py` | 🟡 MEDIA | 30 min |
| **Backtesting** | Creare dataset sintetico di eventi DOM (spoof/iceberg) per validare le regole | 🟡 MEDIA | 4-6 ore |
| **Prossimo Studio** | Video su **Delta Divergence** e **Footprint Charts** | 🟡 MEDIA | Ongoing |

> **💡 Raccomandazione chiave**: Prima di codificare le nuove regole, accumulare almeno 20-30 trade con logging degli eventi DOM reali (anche manualmente) per validare che i criteri proposti (size_ratio ≥ 3x, survival < 30s, refresh < 2s) siano statisticamente significativi nel mercato che effettivamente tradate (ES, NQ, CL, ecc.). Le regole "ALTA priorità" sopra proposte sono *ipotesi operative* da validare, non assiomi.