# Trade Log: Bookmap's Iceberg Indicator - How to Guide

**Video**: DZSpKqx7vuI

---

# Analisi Video: "Bookmap's Iceberg Indicator - How to Guide"

## ⚠️ Premessa Fondamentale: Nessun Trade Live Eseguito

Il video analizzato (`DZSpKqx7vuI`, durata ~18 secondi utili) **non contiene sessioni di trading live né trade effettivamente eseguiti**. Si tratta di un **micro-tutorial educativo** sulla piattaforma Bookmap, strutturato in tre segmenti puramente didattici:

| Segmento | Contenuto | Tipo |
|----------|-----------|------|
| 0:00–4.3s | Definizione teorica di Iceberg Order (whiteboard) | Teoria |
| 4.3s–10.1s | Setup interfaccia Bookmap + 3 criteri di validazione | Istruzione |
| 10.1s–17.6s | Esempi visivi di assorbimento e stop run su replay | Esempio illustrativo |

---

## Tabella dei Setup *DISCUSSI* (non eseguiti)

| # | Timestamp | Strumento | Direzione | Contesto | Entry (illustrativa) | Stop (illustrativo) | Target (illustrativo) | Esito | Concetto Applicato |
|---|-----------|-----------|-----------|----------|----------------------|---------------------|----------------------|-------|---------------------|
| 1 | ~10:10–14:30 | ES Futures | **LONG** | Assorbimento massivo di iceberg verdi (ask) dopo sequenza di bolle rosse. Prezzo intorno a **5359.25**. "Effort vs No Result" delle vendite aggressive. | Reazione rialzista confermata dopo l'assorbimento | Sotto il minimo del cluster rosso (sweep) | Opposta estremità / HVN superiore | **Non eseguito** — Setup illustrativo | Spring invertito / Failed Auction / Iceberg Absorption |
| 2 | ~14:50–16:30 | ES Futures | — | Filtro macro: trendline discendente su TF superiore | Setup filtrato se contro trend | — | — | **Non eseguito** | Trend filter (contesto) |
| 3 | ~16:50–17:60 | ES Futures | **LONG** post-sweep | Stop run (cluster rosso a sinistra) seguito da assorbimento verde. Classica liquidity sweep istituzionale. | Dopo conferma assorbimento verde | Sotto i minimi del cluster rosso | Rientro nel value / VAH | **Non eseguito** — Setup illustrativo | Liquidity Sweep + Iceberg Accumulation |

---

## Narrativa dei Setup Illustrati

### 🔹 Setup 1 — Iceberg Absorption su Ask (Spring Invertito)

**Contesto visivo**: Una raffica di **bolle rosse** (vendite aggressive) viene completamente assorbita da **iceberg verdi** (acquisti passivi massivi) che si riformano continuamente allo stesso livello (~5359.25). Il prezzo tenta di scendere ma non ci riesce — classico **"Effort vs No Result"**.

**Direzione suggerita**: LONG, una volta che il prezzo inizia a reagire al rialzo dopo l'assorbimento.

**Valutazione AMT (regole attive)**:

| Regola | Verdetto | Note |
|--------|----------|------|
| **[AMT_CORE_01]** Market State | ⚠️ **Da verificare** | Il setup sembra mostrare transizione da tentativo di estensione (imbalance) a fallimento (potenziale balance). Senza VP visibile non si può confermare. |
| **[AMT_CORE_03]** Second Drive | ❌ **Violazione** | Il video NON mostra l'attesa di un Second Drive. Suggerisce l'ingresso alla "prima reazione" dopo lo sweep. Nella pratica live, attendere il re-test sarebbe più prudente. |
| **[AMT_CORE_07]** Absorption Filter | ✅ **Allineato** | Il setup *sfrutta* l'assorbimento, non lo combatte. Corretto. |
| **[AMT_CORE_14]** Failed Auction Confirmation | ⚠️ **Incompleto** | Manca la conferma esplicita di delta flip o volume exhaustion sul Second Drive. |
| **[AMT_CORE_15]** DOM Iceberg Filter | ✅ **Cuore del setup** | Esattamente ciò che il tutorial insegna: identificare il muro passivo e cavalcare l'iniziativa nella direzione opposta. |

**Concetto chiave**: Questo è un **Failed Auction long**. I venditori aggressivi vengono "trapped" sotto il livello di assorbimento istituzionale. L'entry ottimale sarebbe su un Second Drive rialzista con delta flip confermato, non sulla prima reazione.

---

### 🔹 Setup 3 — Stop Run + Iceberg Accumulation (Trappola Istituzionale)

**Contesto visivo**: Sequenza temporale:
1. **Cluster rosso enorme** a sinistra → sweep di stop loss retail (liquidity grab).
2. **Assorbimento verde massivo** immediatamente dopo → le istituzioni usano la svendita per riempire long a prezzi scontati.
3. **Prezzo risale** → i venditori retail sono intrappolati (trapped shorts).

**Direzione suggerita**: LONG, con stop sotto i minimi del cluster rosso.

**Valutazione AMT (regole attive)**:

| Regola | Verdetto | Note |
|--------|----------|------|
| **[AMT_CORE_04]** Surgical Stop | ✅ **Suggerito correttamente** | Lo stop va sotto i minimi del cluster (nella "pancia" del volume rosso), non sopra il primo wick. |
| **[AMT_CORE_11]** Failed Auction Reversal | ✅ **Allineato** | Corrisponde esattamente: effort vs no result, contrarian entry, stop dietro il wick fallito. |
| **[AMT_CORE_08]** Volume Profile Ledge | ⚠️ **Menzionato ma non mostrato** | Il video cita l'importanza del contesto VP ma non ne mostra uno nella finestra di analisi. |
| **[AMT_CORE_10]** Pullback Rejection | ❌ **Non discusso** | Nessuna menzione di attendere una candela di rejection (wick ratio ≥ 0.35) prima dell'entry. |

**Concetto chiave**: Questo è **l'archetipo perfetto del Failed Auction + Spring di Wyckoff**: le istituzioni creano artificialmente pressione di vendita per alimentare i propri iceberg di acquisto, per poi invertire. È esattamente il setup che le regole AMT_CORE_11 e AMT_CORE_14 sono progettate per catturare.

---

## Gap Identificati nel Tutorial

| Gap | Impatto Operativo | Regola AMT di Riferimento |
|-----|-------------------|---------------------------|
| Nessun **Second Drive** menzionato come filtro di conferma | Rischio di ingresso sulla prima reazione (First Drive = liquidity probe) | AMT_CORE_03, AMT_CORE_14 |
| Nessun **delta flip esplicito** richiesto per la conferma | Rischio di operare su assorbimento "morto" senza initiative phase | AMT_CORE_07, AMT_CORE_15 |
| Nessuna menzione di **wick ratio / rejection signature** | Possibili falsi segnali su candele che chiudono nella direzione sbagliata | AMT_CORE_10 |
| Stop placement "sotto il cluster rosso" è corretto, ma non viene distinto tra **belly** vs **extreme** | Esposizione a sweep secondari se stop piazzato sul wick estremo | AMT_CORE_04, AMT_CORE_09 |
| Nessun **position sizing dinamico** discusso | Rischio di rischio % fisso su stop di distanze variabili | AMT_CORE_05 |

---

## Conclusione Operativa

Il video è un **ottimo punto di partenza visivo** per imparare a riconoscere gli Iceberg su Bookmap, ma **non è sufficiente come sistema di trading live**. Per operare in modo disciplinato, i setup illustrati andrebbero filtrati attraverso:

1. ✅ **Conferma VP**: verificare se il livello coincide con VAL/VAH/POC/HVN.
2. ✅ **Second Drive obbligatorio**: mai entrare sulla prima reazione post-sweep.
3. ✅ **Delta flip confermato**: la fase di "initiative" deve seguire la "response".
4. ✅ **Stop strutturale**: nella pancia del volume, non sui wick estremi.
5. ✅ **Scale-out 50% al primo target HVN/POC**, poi BE sul resto.

**Raccomandazione**: classificare questo video come **materiale didattico di pattern recognition**, non come sessione di trading actionable. Per estrarne valore operativo, occorre integrarlo con un workflow AMT completo che includa le 15 regole attive.