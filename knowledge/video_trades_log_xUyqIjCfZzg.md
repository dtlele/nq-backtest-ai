# Trade Log: Live Trading con Fabio Valentini e Carmine Rosato

**Video**: xUyqIjCfZzg

---

# 📊 ESTRAZIONE TRADE LIVE — Live Trading con Fabio Valentini e Carmine Rosato

**Fonte video:** `https://www.youtube.com/watch?v=xUyqIjCfZzg`
**Durata:** 3h 49m 37s (23 chunk da ~10 min)
**Speaker:** Fabio Valentini (struttura/AMT) + Carmine Rosato (microstruttura/footprint)
**Strumenti operativi:** ES (E-mini S&P 500), BTC (Bitcoin Futures)
**Piattaforme:** Jigsaw Daytradr, Sierra Chart, Bookmap, TradingView

---

## 🔍 Metodologia di Estrazione

L'analisi fornita descrive **7 macro-setup** ricorrenti, spesso ripresi in più sezioni del video. Ho convertito i riferimenti "Sez. N" in **timestamp stimati** (chunk da 10 min) e separato chiaramente le istanze che paiono essere **trade effettivamente eseguiti** da quelle di **natura didattica/replay**.

> ⚠️ **Nota epistemologica**: il video mescola didattica, replay, backtest e live execution. Dove l'evidenza testuale non permette di stabilire con certezza se il setup sia stato *cliccato* in tempo reale, l'esito viene marcato come `Non determinabile` o `Didattico`.

---

## 📋 TABELLA MASTER — TUTTI I TRADE/SETUP OSSERVATI

| # | Timestamp (h:mm) | Sez. | Strumento | Direzione | Contesto Macro | Entry (livello) | Stop | Target | Esito | Concetto Applicato | Conf. Live? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **T1** | 01:50–02:00 | 12 | ES | Short | Trend ribassista, pullback verso offerta (riquadro giallo/HVN) | Pullback completato a VAH/HVN | Sotto massimo pullback + 25 ticks | VAL / nuovo minimo | ✅ Implicito win | Pullback to Value | 🟡 Didattico |
| **T2** | 02:00–02:10 | 13 | ES | Short | Idem T1, altra istanza di pullback in trend down | Trigger zone su HVN superiore | Buffer 20-25 ticks | Estensione trend | ✅ Win narrato | Pullback to Value + Trigger Zone | 🟡 Didattico |
| **T3** | 01:00–01:10 | 7 | ES | Long/Short | Test ripetuto di livello chiave, "muro" domanda vs offerta | Breakout con conferma delta | Sotto minimo test | Lato opposto del range | 🟡 Discussione | Domanda vs Offerta su LVN | ⚪ Osservazionale |
| **T4** | 01:10–01:20 | 8 | ES | Long | Buyer Absorption confermata su pullback, big trades sul T&S | ~mercato (zona pullback) | Sotto minimo pullback + 25 ticks | HVN superiore | ✅ Win | Buyer Absorption + Big Trades | 🟢 Live |
| **T5** | 01:10–01:20 | 8 | ES | Short | Pullback to Value (altra istanza) | Trigger su HVN | Sotto pullback high | VAL | ✅ Implicito | Pullback to Value | 🟡 Didattico |
| **T6** | 00:10–00:20 | 2 | ES | Short | Pullback to Value iniziale, apertura sessione | HVN/VAH | 20-25 ticks | VAL / estensione | ✅ Win narrato | Pullback to Value (apertura) | 🟡 Didattico |
| **T7** | 00:30–00:40 | 4 | ES | **Long** | Spring/Trap sotto minimo chiave in downtrend | **16.080–16.085** | **16.050** (25-35 tick buffer) | **16.100+ (VAH/IBH)** | ✅ Win (R/R > 3:1) | **Spring + Second Drive** | 🟢 **LIVE** |
| **T8** | 02:40–02:50 | 17 | ES | **Long** | Spring/Trap Long (seconda istanza, didattica) | Simile a T7 | Simile a T7 | VAH | ✅ Win | Spring + Delta Divergence | 🟡 Didattico |
| **T9** | 02:50–03:00 | 18 | ES | **Long** | Trend Day Up, pullback ad AVWAP come supporto dinamico | Consolidamento sopra AVWAP | Sotto AVWAP (20-30 ticks) | HVN / massimo sessione | ✅ Win | **AVWAP Pullback + Second Drive** | 🟢 **LIVE** |
| **T10** | 03:10–03:20 | 20 | ES | **Long → Exit** | **Imbalance Hunt con assorbimento** + inversione su target | Dopo conferma assorbimento + breakout mini-range | Sotto minimo "deceptive move" (35 tick buffer) | HVN superiore | ✅ **Win centrato**, poi **Failed Auction** sul target → flat | **Imbalance Hunting + RNI** | 🟢 **LIVE** |
| **T11** | 03:20–03:30 | 21 | ES | **Long ❌** | Breakout long senza conferma delta → **Failed Auction** | Breakout long su wick | Sotto livello (troppo stretto) | Nuovo massimo | ❌ **Loss** (post-mortem) | Errore: ingresso in Response, no Iniziativa | 🟢 **LIVE (failed)** |
| **T12** | 03:20–03:30 | 21 | ES | **Long** | Spring/Trap Long (terza istanza) | Su Second Drive | Sotto fake low | VAH | ✅ Win (concettuale) | Spring + Initiative candle | 🟡 Didattico |
| **T13** | 02:00–02:10 | 13 | BTC | Short/Long | Osservazione contesto crypto (bookmap) | n.d. | n.d. | n.d. | ⚪ Osservazionale | Contesto cross-market | ⚪ Contestuale |

> **Legenda:** 🟢 Live trade eseguito • 🟡 Didattico/replay • ⚪ Osservazionale • ❌ Loss • ✅ Win

---

## 🏆 NARRATIVE DEI TRADE PIÙ SIGNIFICATIVI

### 🎯 TRADE T10 — Imbalance Hunt con Assorbimento e Uscita su Failed Auction *(Sez. 20, ~03:10)*

**Setup completo (probabilmente il trade cardine del video):**

1. **Contesto strutturale**: Calo brusco del prezzo (move impulsivo, "deceptive move") seguito da una **risalita immediata** che configura un classico *Imbalance Hunting* sotto un minimo relativo. Il volume profile mostra assorbimento evidente — forti volumi sul lato vendite senza progresso del prezzo (delta divergente).

2. **Trigger d'ingresso Long**:
   - Footprint mostra **stacked imbalances verdi** (3+ livelli consecutivi con sbilancio 3:1 a favore degli acquirenti)
   - Breakout della prima candela di **Initiative** con delta fortemente positivo
   - Conferma Big Trades sul Time & Sales

3. **Gestione della posizione**:
   - **Entry**: zona di breakout del mini-range post-assorbimento
   - **Stop**: sotto il minimo della "deceptive move" con buffer di **35 tick** (in linea con AMT_RULE_318 e AMT_RULE_322)
   - **Target**: HVN superiore (riquadro verde) — centrato con precisione

4. **Uscita (punto cruciale)**: Sul target compaiono **stacked imbalances rosse aggressive** con wick superiore pronunciato → classica **Failed Auction** in formazione. Fabio e Carmine **liquidano immediatamente** senza esitazione. Il rispetto del principio *"non opporsi al delta quando flippa"* previene una reversal avversa.

5. **Lezione operativa**:
   > Il target viene colpito con successo, ma la presenza di offerta aggressiva sul livello obbliga a **prendere profitto prima della potenziale inversione**. È esattamente l'applicazione del pattern **RNI**: l'ingresso era in *Initiative* (long dopo *Response* dei venditori), l'uscita è in *Response* (i compratori assorbono sul target) → segnale di cessione del controllo.

**Verdetto AMT Rules:**
- ✅ Stop dietro livello strutturale con buffer ≥35 tick → conforme a **AMT_RULE_297, 303, 318, 322**
- ✅ Non opposto alla zona di assorbimento (delta coerente) → conforme a **AMT_RULE_305**
- ✅ Trade con momentum/delta allineati fino al target → nessun early exit (anti-**AMT_RULE_298**)
- ⚠️ Verificare se orario di ingresso cade nella kill zone 10:15-10:30 ET (**AMT_RULE_323**)

---

### 🎯 TRADE T7 — Spring/Trap Long ad Alta Probabilità *(Sez. 4, ~00:30)*

**Setup completo (uno dei più didattici del video):**

1. **Contesto strutturale**: Trend ribassista ben definito (*day type down*). Il prezzo viola un minimo relativo chiave con **wick** (non chiusura netta) → primo segnale di **trap** degli stop loss dei long.

2. **Costruzione del setup (Steidlmayer-style)**:
   - **First Drive**: rottura del minimo, raccolta di liquidità passiva
   - **Pullback**: il prezzo ritorna sopra il livello violato
   - **Second Drive**: nuovo test del livello da sopra, con **candela di Initiative** a delta fortemente positivo e **stacked imbalances** all'interno

3. **Parametri operativi (livelli ES espliciti)**:
   | Variabile | Livello | Note |
   |---|---|---|
   | Entry | **16.080–16.085** | Breakout prima candela Initiative |
   | Stop | **16.050** | Sotto il fake low + 30-35 tick buffer |
   | Target 1 | **16.100+** | VAH (Value Area High) |
   | Target 2 | **16.110** | IBH (Initial Balance High) |
   | R/R | **> 3:1** | Setup di livello qualitativo superiore |

4. **Conferme order flow**:
   - **Delta divergence** sul minimo (prezzo scende, delta positivo) → Buyer Absorption
   - **Initiative candle** con volumi aggressivi sul lato ask
   - **Big Trades** >500 contratti sul T&S durante la risalita

5. **Insight didattico chiave**:
   > *"Prima Drive è la probe, Second Drive è la conferma"* — citano Steidlmayer/Cox. L'entry sul Second Drive offre il miglior R/R perché il "trapped short" fornisce fuel direzionale, e chi è short sul minimo violato deve ricoprire alimentando il movimento.

**Verdetto AMT Rules:**
- ✅ Stop dietro minimo strutturale con buffer 30-35 tick → conforme a **AMT_RULE_297, 303, 307, 318**
- ⚠️ Long in downtrend day_type: serve **conferma di reversal con alto delta** (è esattamente il caso qui) → conforme a **AMT_RULE_312** solo grazie alla conferma
- ✅ Stops **non** a numeri tondi rotondi né all'estremo del wick → conforme a **AMT_RULE_304**
- ✅ Setup con confluenza multipla (struttura + delta + big trades) → confidence >50 → conforme a **AMT_RULE_300, 316, 320**

---

### 🎯 TRADE T11 — Long Fallito: Post-Mortem Didattico *(Sez. 21, ~03:20)*

**Setup (errore esplicito analizzato dai due trader):**

1. **Contesto**: Livello tecnico violato al rialzo, ingresso long sul breakout meccanico.

2. **Errore commesso**:
   - **Mancata lettura del footprint** sul tentativo di breakout: il delta resta **negativo/divergente** sul wick superiore
   - Classico **assorbimento venditore** non riconosciuto: grossi volumi ask colpiscono un muro di limit orders passivi
   - Ingresso in piena **fase di Response** (venditori che difendono), non in **Initiative** (compratori che spazzano)

3. **Dinamica del fallimento**:
   - Wick superiore pronunciato con volumi alti ma delta negativo
   - Prezzo torna violentemente sotto il livello → **Failed Auction** confermato
   - Stop colpito, trade chiuso in loss

4. **Lezione articolata**:
   > *"Un breakout del prezzo non basta: serve order flow aggressivo e sostenuto. Senza la conferma del delta, stai entrando con i venditori, non contro di loro."*
   
   Differenza concettuale con T10 (dove l'ingresso era legittimo): in T10 il delta *precedeva* il movimento, in T11 il movimento *precedeva* la conferma.

**Verdetto AMT Rules:**
- ❌ **Viola AMT_RULE_298** (momentum/delta non confermato → entry in Response, no Initiative)
- ❌ **Viola AMT_RULE_305** (long contro zona di assorbimento confermata)
- ❌ **Viola AMT_RULE_312** (long in downtrend senza chiara conferma reversal)
- ❌ Stop presumibilmente troppo stretto (wick hunting) → **Viola AMT_RULE_304, 307**
- 🟡 Utile come **caso studio** per il sistema di filtri

---

### 🎯 TRADE T9 — AVWAP Pullback in Trend Day Up *(Sez. 18, ~02:50)*

**Setup completo:**

1. **Contesto**: Trend Day rialzista forte (*day_type up* consolidato). Prezzo opera stabilmente sopra l'AVWAP ancorata al minimo della sessione.

2. **Trigger**: Pullback che riporta il prezzo a testare l'AVWAP come supporto dinamico, seguito da:
   - **Consolidamento** sopra l'AVWAP
   - **Cluster verdi** nel footprint confermano pressione compratrice
   - **Second Drive** esplicito (pullback + ripresa)

3. **Gestione**:
   - **Entry**: sui minimi del consolidamento sopra AVWAP
   - **Stop**: sotto l'AVWAP (20-30 tick buffer) — *non* a contatto diretto
   - **Target**: HVN superiore / massimo di sessione

4. **Insight chiave**:
   > L'AVWAP funziona come "ancora magnetica" del prezzo in trend days. Il pattern *pullback to AVWAP + Second Drive* è una variante moderna del classico *pullback to value in trend*, con il vantaggio di ancorarsi alla *narrative istituzionale* (VWAP = prezzo medio degli istituzionali).

**Verdetto AMT Rules:**
- ✅ Long allineato al day_type up → conforme a **AMT_RULE_306, 312**
- ✅ Stop con buffer 20-30 tick adeguato al contesto (bassa/media volatilità) → conforme a **AMT_RULE_307**
- ✅ Trend chiaro + confluenza AVWAP/Second Drive → confidence elevata → conforme a **AMT_RULE_300, 316**
- ⚠️ In alta volatilità, buffer dovrebbe salire a 40+ tick (**AMT_RULE_313, 319, 321, 325, 326**)

---

## 🛡️ COMPLIANCE MATRIX — TRADE vs AMT RULES

| Trade | R297 (stop 35t) | R298 (no early exit) | R300 (conf ≥50) | R304 (no round nr) | R305 (no vs absorption) | R306 (no vs trend) | R312 (no long in down) | R323 (no 10:15-10:30) |
|---|---|---|---|---|---|---|---|---|
| **T1** (Short PB) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | n/a | ⚠️ check |
| **T4** (Long Abs) | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ | ✅ | ⚠️ check |
| **T6** (Short PB) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | n/a | ⚠️ check |
| **T7** (Spring L) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅*con delta | ⚠️ check |
| **T9** (AVWAP L) | ⚠️ 20-30t | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ check |
| **T10** (Imb Hunt) | ✅ 35t | ✅ | ✅ | ✅ | ✅ | ✅ | n/a | ⚠️ check |
| **T11** (❌ Long) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ check |
| **T12** (Spring L) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅*con delta | ⚠️ check |

> ⚠️ **AMT_RULE_323 (kill zone 10:15-10:30 ET, WR 18%)**: non posso verificare l'orario esatto dal materiale, ma va **sempre** controllato pre-entry. Per ES futures, l'orario italiano 16:15-16:30 corrisponde a ~10:15-10:30 ET (estate) o 11:15-11:30 ET (inverno con DST asimmetrico).

---

## 🔑 KEY TAKEAWAY DIDATTICI

### 1. La Gerarchia dei Concetti
Il video stabilisce una chiara gerarchia operativa:
```
[MACRO] Day Type / IB / Trend
   ↓
[STRUTTURA] Volume Profile / HVN / LVN / VAH / VAL / POC
   ↓
[MICRO] Footprint / Delta / RNI Pattern
   ↓
[TRIGGER] Stacked Imbalances / Big Trades / Initiative Candle
```
Ogni layer filtra il successivo: non si scende al micro se la macro è incerta (cfr. **AMT_RULE_314**).

### 2. La Differenza Cruciale: Response vs Initiative
È il singolo concetto più ripetuto. La regola operativa:
- **Vietato** entrare in *Response* (assorbimento in corso)
- **Obbligatorio** aspettare l'*Initiative* (candela aggressiva, delta coerente, volumi)
- T11 (loss) è esattamente la violazione di questa regola

### 3. Il Second Drive come Filtro di Conferma
Quasi tutti i trade vincenti del video (T7, T9, T10) mostrano la struttura:
- **First Drive** → probe di liquidità
- **Pullback** → consolidamento
- **Second Drive** → entry ad alta probabilità

Questo concetto riduce drasticamente i falsi breakout (i "breakout and reverse" che hanno generato T11).

### 4. La Questione degli Stop — Insight Controverso
Il video **critica esplicitamente** il piazzamento dello stop:
- ❌ "Stupido" stop sopra/sotto il massimo/minimo della wick (esposizione al *retail liquidity pool*)
- ✅ Stop "nascosto" nel belly del P-shape/b-shape o dietro un muro strutturale con **buffer 25-35 tick**

Questo posiziona gli stop in zone dove le istituzioni non hanno interesse a spazzare, riducendo le stop-out premature.

### 5. L'AVWAP come "Narrative Istituzionale"
L'Anchored VWAP ancorata al minimo/massimo della sessione rappresenta il **prezzo medio degli istituzionali** che hanno costruito il trend. I pullback su AVWAP in trend days sono setup a basso rischio perché istituzionalmente *dovrebbero* difendere quel livello (coerente con la teoria del *defense at discount*).

### 6. Il Post-Mortem come Asset Didattico
T11 (il trade fallito) è trattato con la stessa enfasi dei trade vincenti. L'errore — *entrare in Response senza aspettare Initiative* — diventa un caso-studio che permane nella memoria operativa molto più di un win generico. **Cultura del loss come feedback, non come fallimento.**

---

## 📊 RIEPILOGO STATISTICO DEI TRADE ESTRATTI

| Metrica | Valore |
|---|---|
| Trade totali identificati | **13** (13 setups, di cui ~4-5 *live*) |
| Trade vincenti (✅) | 10-11 (maggior parte didattici/replay) |
| Trade perdenti (❌) | 1 (T11 — post-mortem) |
| Win rate osservato | ~85-90% (fortemente selezionato: solo i setup "puliti" vengono presentati) |
| Setup più frequente | **Spring/Trap Long** (T7, T8, T12) — segnale che è il *core setup* della metodologia |
| Setup con R/R migliore | T7, T10 (entrambi >3:1) |
| Errore chiave identificato | Entry in Response senza aspettare Initiative (T11) |
| Concetto più citato | **RNI Pattern** (Response vs Initiative) |
| Concetto più "contro-intuitivo" | Stop nel belly del profilo, non all'estremo della wick |

---

## 🎓 RACCOMANDAZIONI PER IL SISTEMA

1. **Codificare l'RNI Pattern come filtro pre-entry obbligatorio** — sarebbe probabilmente la singola regola con il miglior rapporto *impatto/complessità*. Riduce T11 e i falsi breakout.

2. **Aggiungere filtro orario AMT_RULE_323** esplicitamente — il video non lo cita, ma la regola dinamica del 18% WR nella kill zone 10:15-10:30 ET è critica.

3. **Differenziare i buffer di stop per contesto di volatilità** — il video parla di 25-35 tick generici, ma le regole dinamiche spingono a **40-50 tick in alta volatilità**. Serve un indicatore di regime (ATR-based o realized vol) per automatizzare.

4. **Tracciare il "Second Drive Score"** — quanti Second Drive confermano prima dell'entry? Maggiore è il numero, maggiore è la confidence. Setup con 0 Second Drive → skip (anti-T11).

5. **Integrare l'AVWAP come confluence aggiuntiva** — non come segnale autonomo, ma come booster di confidence su setup già validati da RNI + delta.

> 💡 **Insight finale**: il video è essenzialmente un **corso accelerato di Steidlmayer/Cox applicato all'order flow moderno**. I setup mostrati (Spring, Pullback to Value, Imbalance Hunting, AVWAP Pullback) sono i 4 "mattoni fondamentali" di AMT operativa. Un sistema di trading che codifichi questi 4 pattern con i giusti filtri (RNI, delta, orario, volatilità) avrebbe un edge robusto su ES futures in RTH.