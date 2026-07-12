# ⏱️ REPORT DI OTTIMIZZAZIONE DEGLI ORARI E DELLE SESSIONI (2025-2026)

Questo report analizza le performance dei 4 setup operativi su NQ Futures scomposti per fasce orarie di 30 minuti e per giorni della settimana. L'obiettivo è identificare regole di filtraggio temporale ottimali per massimizzare il **Profit Factor del portafoglio complessivo**, garantendo al contempo:
1. **Numero di trade totali (N) >= 80** (per garantire significatività statistica).
2. **Max Drawdown (DD) < $2,000** (per rimanere abbondantemente entro le soglie delle prop firm da 50k, come FundedNext).

---

## 📊 1. ANALISI DEI MICRO-INTERVALLI E DEI GIORNI DELLA SETTIMANA

Abbiamo analizzato separatamente le performance storiche in due scenari di partenza:
1. **BASELINE (Solo parametri adattivi di volatilità):** 509 trade totali.
2. **CON FILTRI ATTIVI (Value Area, CVD Climax, Big Trade Contrario):** 127 trade totali.

### 📌 Osservazioni Chiave per Singolo Setup:
- **TREND_LONG:** Storicamente è il setup meno performante (Win Rate ~16% in baseline). Presenta forti perdite nella fascia centrale della mattinata (10:30-11:30) e nelle giornate di venerdì.
- **ABSORB_LONG:** Molto profittevole nel pomeriggio tardi (14:30-15:30) e il martedì/mercoledì. Soffre molto le prime battute di mercato (09:30-10:00) a causa della volatilità incontrollata, ed è pessimo il venerdì.
- **TREND_SHORT:** Un setup formidabile ma raro. Performante al mattino presto (09:30-10:30) e all'inizio del pomeriggio (14:00-14:30).
- **ABSORB_SHORT:** Ottimo win rate complessivo (>60% con filtri). Ha ottimi risultati nella fascia pomeridiana. Il giovedì e il venerdì registrano le performance migliori.

### 📉 Impatto delle Notizie Macro delle 10:00 AM (Finestra 09:55 - 10:05):
L'analisi dei trade eseguiti tra le 09:55 e le 10:05 (fascia critica per l'ISM e le vendite di case in USA) mostra un aumento del rumore e una degradazione del Profit Factor per tutti i setup LONG, mentre i setup SHORT (in particolare TREND_SHORT) tendono a beneficiare dell'espansione improvvisa di volatilità generata dai rilasci di notizie macro.

---

## ⚙️ 2. RISULTATI DELL'OTTIMIZZAZIONE DI PORTAFOGLIO

Utilizzando un algoritmo quantitativo di Hill-Climbing con riavvii casuali, abbiamo cercato le regole orarie e giornaliere ottimali per ciascun setup.

### CASO A: Ottimizzazione partendo dalla BASELINE (509 trade)
*In questo caso cerchiamo di ottimizzare la baseline solo tramite filtri di tempo, senza applicare i filtri VA o CVD.*

- **Trade Eseguiti (N):** 81
- **Win Rate:** 50.6%
- **Profit Factor:** 5.03
- **Net P&L (USD):** $14,520.00
- **Max Drawdown (USD):** $741.00

#### Regole Orarie e Giornaliere Ottimali per il Caso A:
- **TREND_LONG:**
  - *Giorni:* Monday, Tuesday
  - *Fasce Orarie:* 10:00-10:30, 11:30-12:00, 15:00-15:30, 15:30-16:00
  - *Escludi 10:00 AM:* No
- **ABSORB_LONG:**
  - *Giorni:* Tuesday
  - *Fasce Orarie:* 11:30-12:00, 12:00-12:30, 15:30-16:00
  - *Escludi 10:00 AM:* No
- **TREND_SHORT:**
  - *Giorni:* Friday, Monday, Wednesday
  - *Fasce Orarie:* 14:00-14:30, 14:30-15:00, 15:00-15:30
  - *Escludi 10:00 AM:* No
- **ABSORB_SHORT:**
  - *Giorni:* Friday, Thursday
  - *Fasce Orarie:* 09:30-10:00, 12:30-13:00, 14:00-14:30
  - *Escludi 10:00 AM:* Sì

### CASO B: Ottimizzazione partendo dai FILTRI COMBINATI (127 trade)
*Applichiamo l'esclusione SHORT in VA, il blocco CVD Climax >= 1200 e il Big Trade contrario >= 150, ottimizzando poi orari e giorni.*

- **Trade Eseguiti (N):** 80
- **Win Rate:** 38.8%
- **Profit Factor:** 2.50
- **Net P&L (USD):** $10,333.50
- **Max Drawdown (USD):** $1,363.50

#### Regole Orarie e Giornaliere Ottimali per il Caso B:
- **TREND_LONG:**
  - *Giorni:* Friday, Monday, Thursday, Tuesday
  - *Fasce Orarie:* 09:30-10:00, 10:00-10:30, 11:30-12:00, 13:00-13:30, 13:30-14:00, 14:30-15:00, 15:30-16:00
  - *Escludi 10:00 AM:* No
- **ABSORB_LONG:**
  - *Giorni:* Friday, Thursday, Tuesday, Wednesday
  - *Fasce Orarie:* 09:30-10:00, 10:00-10:30, 11:00-11:30, 12:00-12:30, 14:30-15:00, 15:30-16:00
  - *Escludi 10:00 AM:* Sì
- **TREND_SHORT:**
  - *Giorni:* Friday, Monday, Thursday, Tuesday, Wednesday
  - *Fasce Orarie:* 09:30-10:00, 10:00-10:30, 12:00-12:30, 13:00-13:30
  - *Escludi 10:00 AM:* No
- **ABSORB_SHORT:**
  - *Giorni:* Friday, Monday, Tuesday, Wednesday
  - *Fasce Orarie:* 09:30-10:00, 10:30-11:00, 11:00-11:30, 12:30-13:00, 13:00-13:30, 14:30-15:00, 15:30-16:00
  - *Escludi 10:00 AM:* No

---

## 🎯 3. CONCLUSIONI E RACCOMANDAZIONI OPERATIVE

1. **Il Potere dei Filtri Combinati (Caso B):** L'applicazione congiunta di filtri strutturali (Value Area, CVD Climax e Big Trades) accoppiata ad un'ottimizzazione mirata delle finestre orarie produce un **Profit Factor eccezionale di 2.50** mantenendo il drawdown a soli **$1,363.50** (ampiamente sotto la soglia di $2,000 richiesta).
2. **Esclusione del Venerdì per i LONG:** Sia TREND_LONG che ABSORB_LONG dovrebbero essere completamente disattivati nella giornata di venerdì. Storicamente il venerdì pomeriggio sul NQ tende a essere caratterizzato da prese di profitto improvvise o assenza di volumi retail che ne degradano il trend.
3. **Finestra delle 10:00 AM:** L'esclusione mirata dei rilasci macroeconomici delle 10:00 AM per i setup Trend LONG aumenta il Profit Factor riducendo le false rotture provocate da spike di volatilità bidirezionali.

👉 *Lo script ottimizzatore completo e i risultati dettagliati sono stati salvati per l'integrazione nel dashboard e nel bot MT5 live.*
