# Analisi Completa: https://www.youtube.com/watch?v=gDeA8F1Fk3k

**Segmento**: 00:00 — fine

---

# 📘 MASTERCLASS DOCUMENT: Pattern W e M nel Trading
## Guida Operativa Completa basata sul Video "W e M Formations - Come trovarle, comprenderle, tradarle" — bedroomtrader

---

## 1. 🌍 OVERVIEW GENERALE

### 1.1 Chi Parla e Filosofia Generale

Il video analizzato è una **lezione didattica pre-registrata in italiano** del canale **"bedroomtrader"** (Trading, scalping, analisi di mercato), gestito da **Giuseppe D'Amato**, fondatore del canale. La filosofia didattica del relatore si articola su **tre livelli progressivi** che definiscono l'intero impianto formativo:

1. **TROVARE** (visual recognition) — Capacità geometrica di individuare i 4 punti cardinali del pattern
2. **COMPRENDERE** (microstruttura) — Interpretazione di cosa stanno faccendo compratori e venditori durante la formazione
3. **TRADARE** (execution) — Regole operative di entry, stop, target e gestione del rischio

Questa struttura triadica riflette un approccio **olistico al trading** che non si limita alla meccanica del segnale, ma integra la **lettura della psicologia di massa** e dell'**order flow** sottostante. Il relatore insiste sul fatto che le formazioni W e M non sono semplici "figure tecniche" bensì **manifestazioni grafiche di fenomeni psicologici ricorrenti** nei mercati.

### 1.2 Piattaforme Utilizzate

Il video fa riferimento a due piattaforme principali, entrambe mostrate in momenti diversi:

| Piattaforma | Contesto d'uso | Elementi caratteristici |
|-------------|----------------|-------------------------|
| **NinjaTrader** | Grafici con Heikin Ashi, VWAP multi-banda, Volume Profile orizzontale | Setup tipico per futures (NQ/ES/DAX) |
| **TradingView** | Analisi BTCUSDT su 1H con indicatori EMA, Volume Profile statico e dinamico | Interfaccia dark theme, strumenti crypto/indici |

### 1.3 Mercati Trattati

I mercati discussi e visualizzati nel video includono:

- **Indici futures:** NQ (Nasdaq), ES (S&P 500) — identificati per volatilità e struttura
- **Indici europei:** DAX, FTSEMIB (riferimento nel setup operativo consigliato)
- **Crypto:** BTCUSDT (Bitcoin) — analizzato specificamente su TradingView 1H a prezzi intorno ai 107.116 USD
- **Forex major:** Menzionati come applicabili ma non specificamente analizzati

### 1.4 Timeframe Operativi Consigliati

Il video stabilisce una chiara gerarchia di timeframe basata sullo stile di trading:

| Stile | Timeframe Formazione | Timeframe Execution |
|-------|---------------------|---------------------|
| **Position/Swing** | 1 Ora, 4 Ore | 15 minuti |
| **Intraday** | 15 minuti | 5 minuti |
| **Scalping** | 5 minuti | 1 minuto |

**Regola chiave:** *"Si verificano sui 15 min e 1 ora — Gli scalper devono usare i 5 min e 1 minuto per tradarle."*

### 1.5 Filosofia Operativa Complessiva

L'approccio del relatore si fonda su alcuni pilastri filosofici ricorrenti:

- **Pazienza come vantaggio competitivo:** Mai anticipare l'entry al punto 3 (la "trappola")
- **Aspettare la conferma:** Entry solo alla chiusura sopra/sotto la neckline (punto 4)
- **Rispettare la struttura:** Lo stop loss è definito dalla geometria del pattern, non da sensazioni
- **Risk management rigoroso:** R:R minimo 1:2, position sizing basato su stop definito
- **Timeframe multipli:** Setup su TF alti, esecuzione su TF bassi

---

## 2. 🛠️ STRUMENTI E CONFIGURAZIONE

### 2.1 Setup NinjaTrader (Sezione 1)

**Configurazione del chart per l'analisi dei pattern W/M:**

| Elemento | Configurazione | Scopo |
|----------|---------------|-------|
| **Tipo candele** | Heikin Ashi con wick | Smoothing della price action, riduzione del noise |
| **VWAP** | Multi-banda (VWAP + deviazioni standard) | Supporto/resistenza dinamici intraday |
| **Volume Profile** | Sessione daily, orizzontale | Identificazione POC, VAL, VAH, HVN, LVN |
| **Media mobile** | EMA bianca (periodo non specificato) | Trend filter |
| **Scala** | Lineare | Precisione nei livelli |
| **Colori VP** | Verde (HVN sopra POC), Rosso/Blu (zone balance) | Visualizzazione istantanea delle aree di valore |
| **Sfondo** | Dark (nero/grigio scuro) | Contrasto ottimale per candele e indicatori |

**Layout tipico:**
- Grafico principale al centro con Heikin Ashi
- Volume Profile sul lato destro
- VWAP sovrapposto al price action
- Numerazione 1-2-3-4 disegnata manualmente sotto i punti chiave

### 2.2 Setup TradingView (Sezione 3)

**Configurazione specifica per BTCUSDT 1H:**

| Elemento | Valori/Configurazione | Note |
|----------|----------------------|------|
| **Simbolo** | BTCUSDT (BINANCE) | Mercato crypto spot |
| **Timeframe** | 1H | Indicato in header "Bitcoin / TetherUS · 1h · BINANCE" |
| **EMA** | 5, 10, 20, 50, 100, 200 | Multiple esponenziali per struttura di trend |
| **Volume Profile Statico** | 1D, 1W, 1M, 3M, 6M, 1Y, 5Y, 10Y, ALL | Fasce orizzontali di supporto/resistenza storici |
| **Volume Profile Dinamico** | Sessione daily | POC a ~107.116, VAH a ~111.000, VAL a ~105.500 |
| **Tema** | Dark | Standard TradingView |
| **Overlay testuale** | Testo bianco centrale con regole sintetiche | Cuore didattico del video |

### 2.3 Setup TradingView (Sezione 2)

**Configurazione per pattern multipli su timeframe bassi:**

| Elemento | Configurazione | Scopo |
|----------|---------------|-------|
| **Candele** | OHLC classiche (verde up, rosso down, bordi bianchi/grigi) | Price action standard |
| **EMA Ribbon** | Bande viola con gradient (più scuro al centro) | Zona dinamica di valore |
| **Zone background** | Verde semitrasparente (bullish), Rosso semitrasparente (bearish) | Aree di accumulazione/distribuzione |
| **Trend lines** | Bianche/gialle manuali | Collegamento swing points |
| **Curve** | Gialle (archi Fibonacci/proiezioni pattern) | Target zones |
| **Sfondo** | Nero (#000000) | Massimo contrasto |

### 2.4 Setup Operativo Consigliato dal Relatore

```yaml
Piattaforma_primaria: "NinjaTrader o TradingView"
Strumenti_default:
  - Indici: NQ, ES
  - Europei: DAX, FTSEMIB
  - Forex: Major pairs
Timeframe_formazione: "15 min, 1 H"
Timeframe_execution: "5 min, 1 min"
Risk_per_trade: "1-2% del capitale"
Sessione_preferita: "RTH, evitare primi 30 min"
Indicatori_minimi:
  - VWAP
  - Volume Profile
  - EMA 20/50
Filtri_sessione: "No pattern durante noise iniziale (primi 30 min RTH)"
```

---

## 3. 📚 CONCETTI DI ORDER FLOW E AUCTION MARKET THEORY INSEGNATI

### 3.1 La Formazione W come "Failed Auction" del Lato Short

**Definizione completa:**
La W è interpretata dal relatore come un classico pattern di **Failed Auction** sul lato short (venditori). Quando il mercato scende, scende, e poi scende ancora al secondo tentativo (Leg 3), i venditori hanno apparentemente "vinto". Tuttavia, se il prezzo non riesce a mantenere la discesa e torna sopra la neckline (massimo del pullback intermedio), l'asta è **fallita** dal lato short.

**Come si legge sul grafico:**
- Due minimi consecutivi (Leg 1 e Leg 3)
- Un massimo intermedio (Leg 2) che NON viene superato nella terza gamba rialzista
- Una neckline orizzontale che collega il massimo del Leg 2
- Il breakout della neckline con chiusura di candela = segnale di continuazione rialzista

**Quando entra in gioco:**
- Fine di un trend ribassista
- Inizio di una fase di accumulazione
- Dopo un "panic sell" o spike di volatilità

**Esempio concreto dal video:**
Nel grafico NinjaTrader con VWAP, si osserva come il **VWAP funga da supporto dinamico** durante la formazione della W. Il **Volume Profile mostra un b-shape** con POC centrale e VAL più basso. Il **breakout (punto 4) avviene con una candela impulsiva** che attraversa il VWAP, e la zona target è rappresentata dal **rettangolo verde sopra** (area di value alta).

**Regola operativa derivante:**
> "Quando il punto 3 forma un higher low rispetto al punto 2, abbiamo la conferma che i venditori stanno perdendo forza. L'entry avviene quando il prezzo supera (close sopra) il massimo del punto 1."

### 3.2 La Formazione M come "Failed Auction" del Lato Long

**Definizione completa:**
La M è lo specchio della W: un **Failed Auction** sul lato long. I compratori spingono il prezzo in alto due volte (Leg 1 e Leg 3), ma nella seconda spinta (Leg 3) non riescono a superare il massimo precedente (lower high). Quando il prezzo chiude sotto il minimo del Leg 1, l'asta long è fallita e il mercato è pronto a scendere.

**Come si legge sul grafico:**
- Due massimi consecutivi (Leg 1 e Leg 3)
- Un minimo intermedio (Leg 2)
- Neckline orizzontale che collega il minimo del Leg 2
- Breakdown della neckline con chiusura di candela = segnale short

**Quando entra in gioco:**
- Fine di un trend rialzista
- Inizio di una fase di distribuzione
- Dopo un "bull trap" o spike di volatilità verso l'alto

**Esempio concreto dal video:**
Formazione a "testa e spalle semplificata" con lower high. Il breakdown avviene con **delta negativo** (visibile nel footprint). Lo stop è posizionato sopra il massimo del punto 3, e il target è nel **LVN sottostante** (Low Volume Node).

**Regola operativa derivante:**
> "Quando il punto 3 è un lower high, significa che i compratori si stanno esaurendo. Entry short quando il prezzo chiude sotto il minimo del punto 1."

### 3.3 Il Concetto del "Trick" (Trappola) nella Parte 3

**Definizione completa:**
Questo è il concetto operativo **più importante** dell'intero video. Nella formazione di qualsiasi W o M, la **parte 3** (il secondo tentativo di minimo per la W, o di massimo per la M) è progettata per **ingannare i trader retail**. I market maker utilizzano questa fase per:

1. **Raccogliere liquidità** (stop hunt)
2. **Innescare posizioni retail** nella direzione sbagliata
3. **Creare l'apparenza di una continuazione** prima del reversal

**Come si legge sul grafico:**

- **Nella W:** il secondo minimo (Leg 3) va **leggermente sotto** il primo minimo (Leg 1), creando un "panic sell". I trader retail che avevano comprato sul rimbalzo del Leg 2 vedono i loro stop innescati. Il mercato poi reverse.

- **Nella M:** il secondo massimo (Leg 3) va **leggermente sopra** il primo massimo (Leg 1), creando un "breakout falso" o "bull trap". I trader retail entrano long qui convinti del breakout, ma il mercato reverse.

**Quando entra in gioco:**
- SEMPRE nella parte 3 di ogni pattern W o M
- In concomitanza con livelli tecnici chiave (neckline, supporti/resistenze)
- Spesso in prossimità di round number psicologici

**Citazione diretta dal video:**
> **"Cercheranno di fregarvi nella parte 3 di entrambe"** / **"Cercheranno di fregarvi nella parte 3"**

**Regola operativa derivante:**
> **MAI** entrare al secondo minimo/massimo (zona di "frega"). **SEMPRE** aspettare la **chiusura della candela sopra/sotto la neckline**.

### 3.4 Assorbimento (W) vs Esaurimento (M)

**Definizione completa di Assorbimento nella W:**
L'assorbimento si verifica quando c'è un'**aggressione significativa di delta negativo** (heavy selling) ma il prezzo **non riesce a scendere** in modo proporzionale. Questo indica che una **passive limit-order wall** sta assorbendo tutta la pressione venditrice senza permettere al prezzo di muoversi. È il segnale che i venditori stanno perdendo forza al secondo test.

**Definizione completa di Esaurimento nella M:**
L'esaurimento si verifica quando c'è **delta positivo** (buying pressure) ma il prezzo **non riesce a salire**. La "coda" di delta positivo viene "esaurita" dalla resistenza passiva, indicando che i compratori hanno finito la benzina.

**Come si legge sul grafico:**
- Assorbimento: candele rosse con wick inferiore lungo (selling pressure assorbita)
- Esaurimento: candele verdi con wick superiore lungo (buying pressure esaurita)

**Quando entra in gioco:**
- Nel punto 3 del pattern (la "frega")
- In concomitanza con la formazione di un higher low (W) o lower high (M)

**Regola operativa derivante:**
- Nella W: cercare candele con **wick inferiore lungo** e **delta negativo** al punto 3 = conferma di assorbimento
- Nella M: cercare candele con **wick superiore lungo** e **delta positivo** al punto 3 = conferma di esaurimento

### 3.5 RNI (Response vs Initiative) Pattern

**Definizione completa:**
Nel contesto AMT, il pattern RNI distingue tra:
- **Response (Risposta):** fase passiva in cui il mercato reagisce a un'iniziativa altrui (es. assorbimento di vendite da parte di un limit wall)
- **Initiative (Iniziativa):** fase aggressiva in cui il mercato prende il controllo (es.# 📘 MASTERCLASS DOCUMENT: Pattern W e M nel Trading
## Guida Operativa Completa basata sul Video "W e M Formations - Come trovarle, comprenderle, tradarle" — bedroomtrader

---

## 1. 🌍 OVERVIEW GENERALE

### 1.1 Chi Parla e Filosofia Generale

Il video analizzato è una **lezione didattica pre-registrata in italiano** del canale **"bedroomtrader"** (Trading, scalping, analisi di mercato), gestito da **Giuseppe D'Amato**, fondatore del canale. La filosofia didattica del relatore si articola su **tre livelli progressivi** che definiscono l'intero impianto formativo:

1. **TROVARE** (visual recognition) — Capacità geometrica di individuare i 4 punti cardinali del pattern
2. **COMPRENDERE** (microstruttura) — Interpretazione di cosa stanno faccendo compratori e venditori durante la formazione
3. **TRADARE** (execution) — Regole operative di entry, stop, target e gestione del rischio

Questa struttura triadica riflette un approccio **olistico al trading** che non si limita alla meccanica del segnale, ma integra la **lettura della psicologia di massa** e dell'**order flow** sottostante. Il relatore insiste sul fatto che le formazioni W e M non sono semplici "figure tecniche" bensì **manifestazioni grafiche di fenomeni psicologici ricorrenti** nei mercati.

### 1.2 Piattaforme Utilizzate

Il video fa riferimento a due piattaforme principali, entrambe mostrate in momenti diversi:

| Piattaforma | Contesto d'uso | Elementi caratteristici |
|-------------|----------------|-------------------------|
| **NinjaTrader** | Grafici con Heikin Ashi, VWAP multi-banda, Volume Profile orizzontale | Setup tipico per futures (NQ/ES/DAX) |
| **TradingView** | Analisi BTCUSDT su 1H con indicatori EMA, Volume Profile statico e dinamico | Interfaccia dark theme, strumenti crypto/indici |

### 1.3 Mercati Trattati

I mercati discussi e visualizzati nel video includono:

- **Indici futures:** NQ (Nasdaq), ES (S&P 500) — identificati per volatilità e struttura
- **Indici europei:** DAX, FTSEMIB (riferimento nel setup operativo consigliato)
- **Crypto:** BTCUSDT (Bitcoin) — analizzato specificamente su TradingView 1H a prezzi intorno ai 107.116 USD
- **Forex major:** Menzionati come applicabili ma non specificamente analizzati

### 1.4 Timeframe Operativi Consigliati

Il video stabilisce una chiara gerarchia di timeframe basata sullo stile di trading:

| Stile | Timeframe Formazione | Timeframe Execution |
|-------|---------------------|---------------------|
| **Position/Swing** | 1 Ora, 4 Ore | 15 minuti |
| **Intraday** | 15 minuti | 5 minuti |
| **Scalping** | 5 minuti | 1 minuto |

**Regola chiave:** *"Si verificano sui 15 min e 1 ora — Gli scalper devono usare i 5 min e 1 minuto per tradarle."*

### 1.5 Filosofia Operativa Complessiva

L'approccio del relatore si fonda su alcuni pilastri filosofici ricorrenti:

- **Pazienza come vantaggio competitivo:** Mai anticipare l'entry al punto 3 (la "trappola")
- **Aspettare la conferma:** Entry solo alla chiusura sopra/sotto la neckline (punto 4)
- **Rispettare la struttura:** Lo stop loss è definito dalla geometria del pattern, non da sensazioni
- **Risk management rigoroso:** R:R minimo 1:2, position sizing basato su stop definito
- **Timeframe multipli:** Setup su TF alti, esecuzione su TF bassi

---

## 2. 🛠️ STRUMENTI E CONFIGURAZIONE

### 2.1 Setup NinjaTrader (Sezione 1)

**Configurazione del chart per l'analisi dei pattern W/M:**

| Elemento | Configurazione | Scopo |
|----------|---------------|-------|
| **Tipo candele** | Heikin Ashi con wick | Smoothing della price action, riduzione del noise |
| **VWAP** | Multi-banda (VWAP + deviazioni standard) | Supporto/resistenza dinamici intraday |
| **Volume Profile** | Sessione daily, orizzontale | Identificazione POC, VAL, VAH, HVN, LVN |
| **Media mobile** | EMA bianca (periodo non specificato) | Trend filter |
| **Scala** | Lineare | Precisione nei livelli |
| **Colori VP** | Verde (HVN sopra POC), Rosso/Blu (zone balance) | Visualizzazione istantanea delle aree di valore |
| **Sfondo** | Dark (nero/grigio scuro) | Contrasto ottimale per candele e indicatori |

**Layout tipico:**
- Grafico principale al centro con Heikin Ashi
- Volume Profile sul lato destro
- VWAP sovrapposto al price action
- Numerazione 1-2-3-4 disegnata manualmente sotto i punti chiave

### 2.2 Setup TradingView (Sezione 3)

**Configurazione specifica per BTCUSDT 1H:**

| Elemento | Valori/Configurazione | Note |
|----------|----------------------|------|
| **Simbolo** | BTCUSDT (BINANCE) | Mercato crypto spot |
| **Timeframe** | 1H | Indicato in header "Bitcoin / TetherUS · 1h · BINANCE" |
| **EMA** | 5, 10, 20, 50, 100, 200 | Multiple esponenziali per struttura di trend |
| **Volume Profile Statico** | 1D, 1W, 1M, 3M, 6M, 1Y, 5Y, 10Y, ALL | Fasce orizzontali di supporto/resistenza storici |
| **Volume Profile Dinamico** | Sessione daily | POC a ~107.116, VAH a ~111.000, VAL a ~105.500 |
| **Tema** | Dark | Standard TradingView |
| **Overlay testuale** | Testo bianco centrale con regole sintetiche | Cuore didattico del video |

### 2.3 Setup TradingView (Sezione 2)

**Configurazione per pattern multipli su timeframe bassi:**

| Elemento | Configurazione | Scopo |
|----------|---------------|-------|
| **Candele** | OHLC classiche (verde up, rosso down, bordi bianchi/grigi) | Price action standard |
| **EMA Ribbon** | Bande viola con gradient (più scuro al centro) | Zona dinamica di valore |
| **Zone background** | Verde semitrasparente (bullish), Rosso semitrasparente (bearish) | Aree di accumulazione/distribuzione |
| **Trend lines** | Bianche/gialle manuali | Collegamento swing points |
| **Curve** | Gialle (archi Fibonacci/proiezioni pattern) | Target zones |
| **Sfondo** | Nero (#000000) | Massimo contrasto |

### 2.4 Setup Operativo Consigliato dal Relatore

```yaml
Piattaforma_primaria: "NinjaTrader o TradingView"
Strumenti_default:
  - Indici: NQ, ES
  - Europei: DAX, FTSEMIB
  - Forex: Major pairs
Timeframe_formazione: "15 min, 1 H"
Timeframe_execution: "5 min, 1 min"
Risk_per_trade: "1-2% del capitale"
Sessione_preferita: "RTH, evitare primi 30 min"
Indicatori_minimi:
  - VWAP
  - Volume Profile
  - EMA 20/50
Filtri_sessione: "No pattern durante noise iniziale (primi 30 min RTH)"
```

---

## 3. 📚 CONCETTI DI ORDER FLOW E AUCTION MARKET THEORY INSEGNATI

### 3.1 La Formazione W come "Failed Auction" del Lato Short

**Definizione completa:**
La W è interpretata dal relatore come un classico pattern di **Failed Auction** sul lato short (venditori). Quando il mercato scende, scende, e poi scende ancora al secondo tentativo (Leg 3), i venditori hanno apparentemente "vinto". Tuttavia, se il prezzo non riesce a mantenere la discesa e torna sopra la neckline (massimo del pullback intermedio), l'asta è **fallita** dal lato short.

**Come si legge sul grafico:**
- Due minimi consecutivi (Leg 1 e Leg 3)
- Un massimo intermedio (Leg 2) che NON viene superato nella terza gamba rialzista
- Una neckline orizzontale che collega il massimo del Leg 2
- Il breakout della neckline con chiusura di candela = segnale di continuazione rialzista

**Quando entra in gioco:**
- Fine di un trend ribassista
- Inizio di una fase di accumulazione
- Dopo un "panic sell" o spike di volatilità

**Esempio concreto dal video:**
Nel grafico NinjaTrader con VWAP, si osserva come il **VWAP funga da supporto dinamico** durante la formazione della W. Il **Volume Profile mostra un b-shape** con POC centrale e VAL più basso. Il **breakout (punto 4) avviene con una candela impulsiva** che attraversa il VWAP, e la zona target è rappresentata dal **rettangolo verde sopra** (area di value alta).

**Regola operativa derivante:**
> "Quando il punto 3 forma un higher low rispetto al punto 2, abbiamo la conferma che i venditori stanno perdendo forza. L'entry avviene quando il prezzo supera (close sopra) il massimo del punto 1."

### 3.2 La Formazione M come "Failed Auction" del Lato Long

**Definizione completa:**
La M è lo specchio della W: un **Failed Auction** sul lato long. I compratori spingono il prezzo in alto due volte (Leg 1 e Leg 3), ma nella seconda spinta (Leg 3) non riescono a superare il massimo precedente (lower high). Quando il prezzo chiude sotto il minimo del Leg 1, l'asta long è fallita e il mercato è pronto a scendere.

**Come si legge sul grafico:**
- Due massimi consecutivi (Leg 1 e Leg 3)
- Un minimo intermedio (Leg 2)
- Neckline orizzontale che collega il minimo del Leg 2
- Breakdown della neckline con chiusura di candela = segnale short

**Quando entra in gioco:**
- Fine di un trend rialzista
- Inizio di una fase di distribuzione
- Dopo un "bull trap" o spike di volatilità verso l'alto

**Esempio concreto dal video:**
Formazione a "testa e spalle semplificata" con lower high. Il breakdown avviene con **delta negativo** (visibile nel footprint). Lo stop è posizionato sopra il massimo del punto 3, e il target è nel **LVN sottostante** (Low Volume Node).

**Regola operativa derivante:**
> "Quando il punto 3 è un lower high, significa che i compratori si stanno esaurendo. Entry short quando il prezzo chiude sotto il minimo del punto 1."

### 3.3 Il Concetto del "Trick" (Trappola) nella Parte 3

**Definizione completa:**
Questo è il concetto operativo **più importante** dell'intero video. Nella formazione di qualsiasi W o M, la **parte 3** (il secondo tentativo di minimo per la W, o di massimo per la M) è progettata per **ingannare i trader retail**. I market maker utilizzano questa fase per:

1. **Raccogliere liquidità** (stop hunt)
2. **Innescare posizioni retail** nella direzione sbagliata
3. **Creare l'apparenza di una continuazione** prima del reversal

**Come si legge sul grafico:**

- **Nella W:** il secondo minimo (Leg 3) va **leggermente sotto** il primo minimo (Leg 1), creando un "panic sell". I trader retail che avevano comprato sul rimbalzo del Leg 2 vedono i loro stop innescati. Il mercato poi reverse.

- **Nella M:** il secondo massimo (Leg 3) va **leggermente sopra** il primo massimo (Leg 1), creando un "breakout falso" o "bull trap". I trader retail entrano long qui convinti del breakout, ma il mercato reverse.

**Quando entra in gioco:**
- SEMPRE nella parte 3 di ogni pattern W o M
- In concomitanza con livelli tecnici chiave (neckline, supporti/resistenze)
- Spesso in prossimità di round number psicologici

**Citazione diretta dal video:**
> **"Cercheranno di fregarvi nella parte 3 di entrambe"** / **"Cercheranno di fregarvi nella parte 3"**

**Regola operativa derivante:**
> **MAI** entrare al secondo minimo/massimo (zona di "frega"). **SEMPRE** aspettare la **chiusura della candela sopra/sotto la neckline**.

### 3.4 Assorbimento (W) vs Esaurimento (M)

**Definizione completa di Assorbimento nella W:**
L'assorbimento si verifica quando c'è un'**aggressione significativa di delta negativo** (heavy selling) ma il prezzo **non riesce a scendere** in modo proporzionale. Questo indica che una **passive limit-order wall** sta assorbendo tutta la pressione venditrice senza permettere al prezzo di muoversi. È il segnale che i venditori stanno perdendo forza al secondo test.

**Definizione completa di Esaurimento nella M:**
L'esaurimento si verifica quando c'è **delta positivo** (buying pressure) ma il prezzo **non riesce a salire**. La "coda" di delta positivo viene "esaurita" dalla resistenza passiva, indicando che i compratori hanno finito la benzina.

**Come si legge sul grafico:**
- Assorbimento: candele rosse con wick inferiore lungo (selling pressure assorbita)
- Esaurimento: candele verdi con wick superiore lungo (buying pressure esaurita)

**Quando entra in gioco:**
- Nel punto 3 del pattern (la "frega")
- In concomitanza con la formazione di un higher low (W) o lower high (M)

**Regola operativa derivante:**
- Nella W: cercare candele con **wick inferiore lungo** e **delta negativo** al punto 3 = conferma di assorbimento
- Nella M: cercare candele con **wick superiore lungo** e **delta positivo** al punto 3 = conferma di esaurimento

### 3.5 RNI (Response vs Initiative) Pattern

**Definizione completa:**
Nel contesto AMT, il pattern RNI distingue tra:
- **Response (Risposta):** fase passiva in cui il mercato reagisce a un'iniziativa altrui (es. assorbimento di vendite da parte di un limit wall)
- **Initiative (Iniziativa):** fase aggressiva in cui il mercato prende il controllo (es.