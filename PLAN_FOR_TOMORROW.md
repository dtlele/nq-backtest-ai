# Piano Operativo per Domani (DeepPrint Pro + Backtest)

In base all'esecuzione di oggi e alla revisione di Kimi K3, ecco il piano d'azione da seguire domani alla ripresa dei lavori:

## 1. Dati Storici Reali (Priorità Assoluta)
Kimi K3 ha confermato che non possiamo usare dati simulati da OHLCV per validare logiche AMT (Volume Profile, Footprint, Delta, Absorption), altrimenti i risultati del backtest non avrebbero valore (si validerebbe solo il simulatore, non la strategia).

**Task:**
- Creare script `scripts/download_databento.py` (nel branch/progetto in cui lavoreremo).
- Scaricare i dati in formato **TBBO (Trades + BBO)** per 20-30 giorni. Questo permette di avere il vero flow tick-by-tick e classificare i trade in bid/ask in modo preciso, fondamentale per l'Absorption.
- Salvare i dati in `cache_ticks/` in formato Parquet per maggiore velocità e pulizia.
- Eseguire una **validazione incrociata**: aggregare le candele M1 dai tick scaricati e confrontarle con le candele in `cache_ohlc/` per assicurarsi dell'integrità dei dati.

## 2. Piattaforma Visiva (DeepPrint Pro)
- Aggiornare `platform/data_service.py` per leggere i file da `cache_ticks/` invece che generare barre sintetiche.
- Eseguire il replay di 1 giorno per fare QA visivo (Footprint vs Price Action a occhio).
- Confermare che il frontend (già in ascolto) gestisca e renderizzi correttamente i nuovi flussi dati reali.

## 3. Backtest Unificato
- Abbiamo eseguito un run di `run_unified_backtest_with_filters.py` che ha terminato con successo:
  - **Scenario**: TRIPLE A TRAP OPTIMIZED (1 ANNO)
  - **Trade Eseguiti**: 100
  - **Win Rate**: 34.0%
  - **Profit Factor**: 1.39
  - **Net P&L**: $14,685.83
  - **Setup migliore**: TREND_SHORT (PF 3.50, WR 60%)
- Nessun errore a runtime.
- **Task**: Una volta integrati i nuovi dati tick, rilanciare il backtest per vedere i veri risultati basati su flussi volumetrici precisi (GEX e AMT) e confrontarli con quelli attuali.
