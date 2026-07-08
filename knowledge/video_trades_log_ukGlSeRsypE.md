# Trade Log: BedroomTrader PVSRA Order Flow

**Video**: ukGlSeRsypE

---

# 📊 Estrazione Trade dal Video "BedroomTrader PVSRA Order Flow"

## ⚠️ Premessa Metodologica Cruciale

Prima di procedere, devo essere trasparente su un punto fondamentale emerso dall'analisi del documento:

> **Il video analizzato NON contiene trade live eseguiti in tempo reale.** Si tratta di contenuto **didattico/educazionale** (masterclass) in cui il trader **marca graficamente setup, livelli e piani operativi** su grafici (TradingView, Sierra Charts/ATAS, Coinglass), ma **non vengono mostrate esecuzioni reali con P&L**.

**Citazione diretta dal documento di analisi:**
> *"Tipologia: Pianificazione di setup con marcatura grafica (zone di entrata, stop, target) — nessuna esecuzione reale osservata in video"*

Quello che segue è quindi l'elenco dei **SETUP PIANIFICATI / POSIZIONI MARCATE** visibili sullo schermo, valutati come se fossero trade con le regole AMT attive.

---

## 📋 Tabella Riepilogativa Setup Pianificati

| # | Timestamp | Strumento | Direzione | Contesto | Entry (zona) | Stop | Target | Esito | Concetto Applicato |
|---|-----------|-----------|-----------|----------|--------------|------|--------|-------|---------------------|
| 1 | Sez. 2 (~prima metà) | ES 12-24 (Globex) | **Long** | Rifiuto del prezzo in supply zone con Big Trades rossi (assorbimento ribassista) | Zona di demand segnata con rettangolo verde (vicino HVN/Keltner inferiore) | Sotto il minimo della candela di rifiuto | Linea bianca tracciata verso HVN superiore / POC | ❌ Non eseguito — Setup teorico | PVSRA + Absorption/Response |
| 2 | Sez. 2 (~seconda metà) | ES 12-24 (Globex) | **Short** | Big Trades rossi in cima a rally esteso (distribuzione istituzionale) | Rettangolo rosso di posizione short disegnato sotto resistenza | Sopra il massimo della candela di inizio setup | Target linea bianca verso VAL/LVN inferiore | ❌ Non eseguito — Setup teorico | PVSRA + Initiative selling |
| 3 | Sez. 3 (~59s-96s) | BTCUSD (Binance) | **Short** | Daily Open + PDL come resistenza daily, prezzo in zona di premium sopra fair value | Etichetta "Short" visibile sul grafico daily/1h | Sopra il daily open / massimo relativo | Verso PDL o LVN inferiore identificati | ❌ Non eseguito — Setup teorico | Auction Market Theory + Daily Levels |
| 4 | Sez. 3 (~96s+) | BTCUSD (Binance) | **Long** | Pullback verso demand zone daily in zona $96k-$100k con alto volume di liquidazioni (Coinglass) | Non esplicitamente entry numerica — zona demand marcata | Sotto il minimo di swing daily | Verso $110k-$114k (HVN superiore) | ❌ Non eseguito — Setup teorico | Liquidation Heatmap + Value Area |

---

## 🔍 Narrativa Dettagliata per i Setup Significativi

### Setup #1 — ES Long su Assorbimento (Sezione 2)

**Contesto:** Il trader sta analizzando ES 12-24 in after-hours (Globex) su un grafico con footprint charts. Il prezzo arriva in una zona di supply superiore dove compaiono **Big Trades rossi di dimensione significativa** ma il prezzo non riesce a proseguire al rialzo (spread contenuto rispetto al volume → sforzo senza risultato = **assorbimento**).

**Piano operativo disegnato:**
- 🟢 Rettangolo verde di posizione long disegnato nella parte inferiore del range
- 📏 Linea bianca di proiezione verso l'alto (target HVN/POC)
- 📏 Trendline tracciata

**Valutazione con regole AMT attive:**

| Regola | Esito | Note |
|--------|-------|------|
| [AMT_NEW_61] Ignition Bar \|delta\|>=30 | ⏸️ Non verificabile | Il footprint mostra Big Trades ma il delta cumulativo della barra non è quantificato esplicitamente nel video |
| [AMT_NEW_62] No entry in balance/accumulation inside IB | ⚠️ Possibile violazione | Il setup è dentro una fase di consolidamento del Globex — rischio di balance |
| [AMT_NEW_63] Delta alignment | ✅ Coerente | Big Trades rossi sopra suggeriscono selling pressure esaurita; long dopo assorbimento è logicamente coerente |
| [AMT_NEW_64] Volume > media ultime 5 barre | ⏸️ Non verificabile | Manca confronto esplicito |
| [AMT_NEW_65] IB breakout retest | N/A | Non è un breakout IB in senso stretto, è un setup di mean reversion su assorbimento |

**Concetto AMT centrale:** Questo è un classico **RNI pattern (Response vs Initiative)**. I Big Trades rossi sono la "Response" (muro passivo di vendita). Per entrare long in modo sicuro, servirebbe attendere l'**"Initiative"** dei compratori (delta che gira aggressivamente positivo con sweep del book). Il setup mostrato è valido come **concetto** ma mancherebbe la conferma di iniziativa.

---

### Setup #2 — ES Short su Distribuzione (Sezione 2)

**Contesto:** Setup speculare al #1. Il prezzo rallya verso una zona di resistenza e il trader disegna un **rettangolo rosso di short position**. Il razionale sarebbe la presenza di big sellers istituzionali che distribuiscono in zona premium.

**Piano operativo disegnato:**
- 🔴 Rettangolo rosso short
- 📏 Target verso LVN/VAL inferiore

**Valutazione con regole AMT attive:**

| Regola | Esito | Note |
|--------|-------|------|
| [AMT_NEW_63] Delta alignment | ⏸️ Da verificare | Per uno short serve delta negativo confermato sulla barra di entrata — non esplicitamente mostrato |
| [AMT_NEW_65] IB breakout retest | N/A | Anche questo è mean reversion, non breakout |

**Concetto AMT:** Difesa istituzionale a HVN/POC (regola 5 del glossario). Le istituzioni tendono a difendere posizioni a prezzi scontati piuttosto che inseguire estremi — quindi short in zona premium con target VAL è coerente con AMT.

---

### Setup #3 — BTC Short su Daily Open (Sezione 3)

**Contesto:** Analisi su BTCUSD daily/1h. Il trader marca esplicitamente **"Short"** sul grafico. Il livello di resistenza è il **Daily Open** + **PDL (Previous Day Low)**. Il prezzo si trova in zona di "premium" sopra la fair value (POC daily).

**Valutazione con regole AMT attive:**

| Regola | Esito | Note |
|--------|-------|------|
| [AMT_NEW_61] Ignition Bar | ❓ Non applicabile (daily) | Su daily il concetto si adatta: serve una candela daily con range ampio e volume superiore alla media |
| [AMT_NEW_62] No entry in balance | ✅ Coerente | L'entry è ai bordi del range (Daily Open come resistenza), non dentro balance |
| [AMT_NEW_65] IB breakout retest | ✅ Concettualmente applicabile | Daily Open = breakout level; attendere retest con chiusura sotto sarebbe più prudente |

**Concetto AMT:** Short in zona premium (sopra POC/VAL) verso discount. Questo rispetta il principio di **"sell premium, buy discount"** dell'AMT.

---

### Setup #4 — BTC Long su Liquidazione Cluster (Sezione 3)

**Contesto:** Il trader consulta la **Coinglass Liquidation Heatmap** mostrando cluster di liquidazioni long nella zona **$96k-$100k** (leverage 473.99K a $100,906). La tesi operativa: il prezzo scenderà a "cacciare" questa liquidità (stop hunt dei long), poi risalirà verso $110k-$114k.

**Questo è un setup complesso e controverso:**

**Valutazione con regole AMT attive:**

| Regola | Esito | Note |
|--------|-------|------|
| [AMT_NEW_61] Ignition Bar | ❓ Serve una barra daily con delta confermato sulla gamba di risalita |
| [AMT_NEW_63] Delta alignment | ✅ Logica: entrare long dopo che il mercato ha "spazzato" i long deboli |
| [AMT_NEW_64] Volume | ✅ Lo sweep di liquidità genera volume anomalo — coerente |

**Concetto AMT:** Questo è un **liquidity raid + reclaim** — simile al "Second Drive" del glossario (punto 3). Il primo drive (discesa) probe la liquidità, il secondo drive (rimbalzo) offre entry più sicura. Tuttavia, dipende fortemente dal **contesto macro e dalla struttura daily**.

---

## 🚨 Criticità Emerse vs Best Practice AMT

| Aspetto | Cosa manca nel video | Cosa servirebbe |
|---------|---------------------|-----------------|
| **Entry numerica esplicita** | ❌ Entry solo "zone", non prezzi precisi | Prezzo di entrata con invalidazione chiara |
| **Risk:Reward calcolato** | ❌ Non mostrato | R:R minimo 2:1 documentato |
| **Size positioning** | ❌ Nessuna menzione | Numero contratti/percentuale capitale |
| **Conferma Delta** | ⚠️ Big Trades visibili ma delta cumulativo non quantificato | Footprint con delta confermato per ogni barra di entrata |
| **Backtest del setup** | ❌ Assente | Statistiche storiche di win rate per setup simili |
| **Gestione post-entry** | ❌ Non mostrata | Regole di trailing stop, breakeven, partials |

---

## ✅ Conclusione Operativa

Il video è un'ottima **introduzione visiva ai concetti PVSRA e AMT**, ma **non costituisce evidenza di edge live verificabile**. I setup mostrati sono:

1. **Concettualmente coerenti** con l'Auction Market Theory
2. **Graficamente ben strutturati** (livelli chiari, zone definite)
3. **Ma non eseguiti** — quindi non testabili come strategia

**Raccomandazione:** Prima di replicare uno qualsiasi di questi setup con capitale reale, servirebbe:
- ✅ Validare con backtest su almeno 100 trade (come indicato nel glossario: "we need at least 100 trades before creating hard rules")
- ✅ Aggiungere le 5 conferme delle regole dinamiche attive (ignition bar, no balance entry, delta alignment, volume confirmation, IB retest)
- ✅ Codificare entry numeriche esatte, stop loss chirurgici (nel "belly" del profilo, non sopra il wick), e target basati su HVN/LVN adiacenti