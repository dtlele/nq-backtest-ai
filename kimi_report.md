# Audit Completo delle Regole Dinamiche — Sistema AMT/NQ

## 1. Regole obsolete o ridondanti

### Duplicati letterali
| Coppia | Problema |
|---|---|
| **205 = 217** | Topic e descrizione identici parola per parola. La 217 (0 successi, probation) è un duplicato esatto della 205 (51 successi). Da eliminare. |
| **210 = 216** | Descrizione identica parola per parola, solo topic diverso ("Entry Timing" vs "Stop Run Avoidance"). Stessa regola registrata due volte con nomi diversi — sintomo di deriva tassonomica. |

### Ridondanze parziali (sovrapposizioni)
- **218 ⊂ 205/217**: è la variante IH della stessa regola di exit management. Tre regole per un concetto solo.
- **219 ⊂ 215**: la 215 richiede già "delta alignment e volume spikes"; la 219 ("solo con volume spike") è un sottoinsieme. Inoltre ha **0 successi** e zero evidenza.
- **207 / 212 / 214**: tre regole di frequency control con trigger diversi (fase di imbalance / mancanza di pullback / 2 SL consecutivi) ma stesso scopo. Nessuna precedenza definita → andrebbero fuse in un unico circuit breaker.
- **209 / 213**: entrambe trattano lo stop in IH (buffer dietro muro strutturale / allargare per volatilità). Concetto unico, due regole.
- **178**: ridondante *per costruzione*. La regola è stata appresa dalle decisioni `light_skip` del sistema con `conf <= 50` — cioè deriva da un gate che l'execution layer applica già. È una regola circolare: non aggiunge vincoli, ribadisce un filtro esistente. Appartiene all'execution layer, non al layer di reasoning.

**Bilancio: 17 regole attive → ~9 concetti unici effettivi.**

---

## 2. Errori logici (con focus NQ)

### AMT_RULE_206 — contraddizione interna
- "**Small expected loss (R-Ratio <= 2)**": se R-Ratio = reward/risk, un valore ≤ 2 indica un setup *mediocre*, non una "perdita attesa piccola". Premessa e metrica non corrispondono.
- "**widening stops**" per setup con perdita piccola: allargare lo stop **aumenta** la perdita attesa, contraddicendo la premessa della regola stessa. Inoltre, se lo stop era su un livello di invalidazione strutturale, allargarlo oltre quel livello cambia la tesi del trade.

### AMT_RULE_213 — titolo vs corpo
Il topic dice "**Stop Reduction**", la descrizione dice "**widen stops**". Contraddizione diretta (stesso difetto della 206: "reduction" di cosa — distanza o frequenza di stop-out?).

### AMT_RULE_210/216 — teoricamente discutibile in AMT
Uno stop run assorbito è il **classico segnale di ingresso** in Auction Market Theory (failed auction / liquidity sweep / spring). Il vostro stesso glossario ("Second Drive") indica il re-test dopo uno sweep come setup ad alta probabilità. Un divieto blanket di entrare dopo uno stop run fa perdere sistematicamente gli ingressi con il miglior R-multiplo su NQ, dove gli sweep su M1 sono la norma, non l'eccezione. La regola ha senso solo per ingressi *momentum continuation* contro lo sweep, non come divieto generalizzato.

### AMT_RULE_191 — rischio di "chasing" su NQ
Attendere la fase di Initiative (flip aggressivo del delta) su NQ M1 significa entrare **dopo** che il movimento è già avvenuto. Su uno strumento con questa velocità, il costo di conferma è slippage strutturale e ingresso a prezzi peggiori. La regola andrebbe quantificata (es. "flip del delta entro N tick dal livello"), altrimenti seleziona sistematicamente ingressi in ritardo.

### Problema metodologico trasversale — le metriche non sono falsificabili
- I "successi" delle regole di tipo `skip_trade` sono **controfattuali non verificabili**: non si può sapere cosa sarebbe successo entrando. "Successes: 30" su una regola di skip è un numero senza significato statistico.
- **0 fallimenti su 17 regole**: nessuna regola ha mai fallito → non esiste un meccanismo di falsificazione → le regole si accumulano monotonicamente e nessuna viene mai ritirata. È survivorship bias strutturale.
- Regole in **probation con 0 successi (217, 218, 219) vengono imposte come "MUST follow"**: standard probatorio invertito. Una regola senza evidenza dovrebbe essere in quarantena, non attiva.
- Incoerenza di lifecycle: 209/210 hanno `probation_days: 7` ma status `active`; 217/218/219 hanno `probation_days: 0` ma status `probation`. Il campo è semanticamente rotto.
- Contraddizione con la nota di sistema: "servono almeno 100 trade prima di creare hard rules", ma esistono regole `active` con 5–20 successi.

### AMT_RULE_211 — non operazionalizzabile
"Aggiusta la size in base a vicinanza ai livelli e forza del momentum": nessuna soglia, nessuna direzione (vicino al livello → più o meno size?). Non è una regola, è un principio.

---

## 3. Errori di terminologia

| Regola | Problema |
|---|---|
| **181** | "**Body absorption**" non esiste in AMT. L'assorbimento è un fenomeno del lato passivo (limit order che assorbono market order aggressivi), misurato via delta vs risposta del prezzo — non un'anatomia della candela. Probabilmente intendete "big trade nei wick senza accettazione di prezzo". |
| **206** | "R-Ratio ≤ 2" usato come sinonimo di "perdita attesa piccola" — errore di definizione. |
| **206/213** | "Stop Reduction" è ambiguo: riduzione della distanza dello stop o riduzione degli stop-out? Il corpo delle regole indica il secondo significato → rinominare in "Stop-Out Prevention". |
| **205/217/218** | **Errore di categoria sull'azione**: sono regole di *gestione dell'uscita* ("non uscire presto") ma l'azione è `skip_trade`, che è un filtro di *ingresso*. Applicata letteralmente, la regola impedirebbe di entrare in trade che si intende tenere — non ha senso. Serve un'azione tipo `hold_position` / `no_early_exit`. |
| **209** | Stesso mismatch: la descrizione riguarda il **posizionamento dello stop**, ma l'azione è `reduce_contracts_or_skip`. L'azione corretta sarebbe `adjust_stop`. |
| **178** | Il testo della regola fa trapelare artefatti implementativi ("light_skip decisions"): le regole dovrebbero descrivere condizioni di mercato, non log interni. |

---

## 4. Conflitti logici tra regole

### Cluster A — Il paradosso IMBALANCE_HUNTING (conflitto più grave)
- **181**: IH è *esente* dal requisito strutturale ("momentum supersedes structural closes")
- **191**: IH è *esplicitamente esente* dalla conferma di Initiative (flip del delta)
- **215**: IH *richiede conferme aggiuntive* di momentum, incluso **delta alignment**
- **219**: IH *solo* con volume spike

→ **Contraddizione diretta**: la 191 esenta l'IH dalla conferma del delta che la 215 rende obbligatoria. Un agente che segue entrambe non può decidere. Il sistema deve scegliere una delle due filosofie: o l'IH è il modulo "fast" esente dalle conferme strutturali, oppure è il modulo soggetto a conferme rafforzate. Non entrambe.

### Cluster B — Ingressi post-sweep
- **210/216**: vietano l'ingresso dopo stop run/reversal
- **181 (eccezione M1)**: permette l'ingresso su momentum da wick — che è *esattamente* la price action post-sweep
- **Glossario "Second Drive"**: il re-test post-sweep è il setup ad alta probabilità

→ La 181-eccezione permette ciò che la 210 vieta, e entrambe contraddicono il framework teorico dichiarato.

### Cluster C — Frequency control vs natura della strategia
- **207**: limita trade consecutivi nella stessa direzione *durante le fasi di imbalance*
- Ma l'IMBALANCE_HUNTING esiste proprio per tradare la fase direzionale: nei trend day su NQ, 207/212 bloccano sistematicamente i trade di continuazione a più alta expectancy. Inoltre la 212 richiede "pullback sufficiente" — nei trend forti i pullback sono shallow per definizione → filtro che esclude i migliori setup.

### Cluster D — Exit management
- **205/217/218** ("non uscire presto") vs **206/211/213** ("riduci contratti"): una riduzione parziale *è* un'uscita anticipata. Nessuna precedenza definita tra le due famiglie.

### Cluster E — Contraddizione nei session_learnings
> "Missed opportunities in earlier sessions due to low confidence levels underscore the value of AMT_RULE_178"

Se opportunità profittevoli sono state *perse a causa* del filtro di confidence, questo è un **fallimento** della 178, non una conferma. Il learning è formulato al contrario e andrebbe corretto — o la regola va rivalutata.

---

## 5. Raccomandazioni di consolidamento

| Verdetto | Regole |
|---|---|
| **Eliminare** (duplicati) | 217, 216, 218 |
| **Spostare all'execution layer** | 178 (gate di confidence, circolare nel reasoning layer) |
| **Fondere** | 215+219 → unica regola di conferma IH; 209+213 → unica regola stop/sizing IH; 212+214+207 → unico circuit breaker con trigger espliciti |
| **Riscrivere** | 206 (metrica sbagliata + azione contraddittoria); 210 (aggiungere eccezione "second drive" coerente col glossario) |
| **Correggere azione** | 205 → `hold_position`; 209 → `adjust_stop` |
| **Quarantena** | 211, 215, 219 (0–2 successi: evidenza insufficiente per essere attive) |
| **Risolvere il paradosso IH** | Decidere: o esente da conferme (tenere 181/191-eccezioni, ritirare 215/219) o soggetto a conferme (ritirare le esenzioni) |

**Governance suggerita**: (1) campione minimo prima dell'attivazione (es. ≥ 20 applicazioni osservate); (2) logging *shadow* dei trade skippati per rendere falsificabili le regole di skip; (3) meccanismo di failure tracking — 0 fallimenti su 17 regole è la prova che oggi non esiste; (4) sistemare la semantica di `probation_days`; (5) assenza vistosa: nessuna regola copre le finestre news 09:45/10:00 EST, pur essendo l'unico rischio documentato nel vostro stesso glossario — su NQ è probabilmente il gap più costoso.

Vuoi che proceda con la riscrittura completa del ruleset consolidato (le ~8 regole finali con azioni corrette)?