# Ricostruzione Ordini Istituzionali (Footprint MBO / Bubbles)

L'obiettivo di questo piano è allineare in modo millimetrico i dati elaborati dal nostro backtest con le visualizzazioni (DeepCharts / Sierra Chart) che utilizza Fabio Valentini per identificare l'assorbimento e i "muri" istituzionali.

## Il Problema Attuale (Frammentazione MBP-1)
I dati Databento forniscono ogni singola esecuzione sul book (Market By Price). Se un algoritmo istituzionale lancia un ordine "Market" da 150 contratti, e questo colpisce 15 limit order da 10 contratti, Databento registra 15 trade distinti da 10. 
L'attuale `NQ_BIG_TRADE_THRESHOLD = 30` cerca un *singolo* trade >= 30, scartando i 15 trade da 10 e perdendo completamente l'impronta istituzionale.

## Soluzione: Aggregazione Footprint per Candela
Le "Bolle" (Bubbles) che Fabio visualizza non sono altro che **nodi di volume ad alto spessore sul footprint (Bid/Ask) di una candela**. 
Invece di filtrare i singoli eventi, il nostro aggregatore calcolerà il footprint esatto di ogni candela e rileverà le "bolle".

### [MODIFY] `src/bar_aggregator.py`
Riscriveremo la logica di popolamento di `big_trades` all'interno della funzione `aggregate_to_bars()`:
1.  **Raggruppamento Spaziale e Temporale**: Raggrupperemo tutti i trade per `candela (es. 5min)`, `lato (Bid/Ask)` e `prezzo esatto`.
2.  **Somma del Volume (Ricostruzione Bubble)**: Calcoleremo la somma dei volumi per ogni livello di prezzo su quel lato.
3.  **Filtro Istituzionale**: Se la somma totale del volume su quel nodo di prezzo (nella candela) è `>= NQ_BIG_TRADE_THRESHOLD` (30 contratti), creeremo un oggetto `Trade` sintetico (una "Bolla") con `size` pari al volume totale aggregato.
4.  **Iniezione**: Inseriremo queste Bolle nella lista `big_trades` della classe `Bar`.

## Vantaggi e Impatto su `candidate_detector.py`
-   **Nessuna modifica necessaria al detector o agli agenti**: Il `candidate_detector.py` è già programmato per cercare queste bolle e calcolare il `wall_max_size`.
-   **Precisione del Muro**: Prima il `wall_max_size` riportava la dimensione del frammento più grande (es. 15 contratti). Ora il LLM vedrà finalmente "Muro Difeso con 350 Contratti a 19500.25", esattamente come Fabio legge dai cluster di bolle!
-   **Aderenza Totale**: In questo modo stiamo replicando fedelmente il calcolo di un Footprint Chart istituzionale.

## User Review Required
> [!IMPORTANT]
> Questa modifica altererà drasticamente (in positivo) il numero di setup identificati, poiché l'agente smetterà di essere "cieco" al 99% degli ordini istituzionali frammentati.  
> Sei d'accordo con questo approccio che trasforma i "singoli trade >= 30" in "Nodi Footprint >= 30 per candela"?

## Open Questions
- Vuoi che mantenga la soglia a `30` contratti (standard NQ) per le bolle ricostruite, o ritieni che sommando tutti i trade di un livello in 5 minuti il numero diventi fisiologicamente più alto e la soglia andrebbe alzata (es. 50 o 100)? Io suggerirei di partire da 30 e valutare quanti trade scattano nel log.
