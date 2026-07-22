# Riepilogo Sessione: Evoluzione Prompt e GLM-5.2

## Punti Chiave
1. **Risoluzione Problemi Modello:** Abbiamo scoperto che l'infrastruttura stava ancora utilizzando `deepseek-chat` causando errori 429 continui su OpenRouter. Abbiamo sostituito globalmente il motore con `z-ai/glm-5.2`.
2. **Aggiornamento Prompt:** Abbiamo inserito le "Domande Chiave AMT" nei prompt ibridi e predatori. Il modello ora valuta criticamente la sua posizione rispetto a VAH, VAL, POC e VWAP prima di decidere (evitando ingressi contro muri AMT).
3. **Pulizia Codice Obsoleto:** Ho eliminato da `src/signal_context.py` il vecchio blocco del `Trinity Trigger` che creava conflitti e allucinazioni normative nel ragionamento del LLM.
4. **Test di 20 Varianti:** È stato avviato un `/goal` in background per far scontrare in parallelo 20 prompt con "personalità" estreme diverse (dal cecchino puro AMT al momentum chaser) sui giorni campione di Gennaio.

## Prossimi Passi per la Nuova Sessione
1. Leggere il file `output/variants20_report.md` generato dallo script notturno per incoronare la variante vincitrice assoluta.
2. Trasferire la logica vincente sul backtester principale.
3. Passare al frontend (`TradingChart.jsx`) per disegnare sul grafico la visualizzazione in tempo reale di Stop Loss, Target e Limit Orders calcolati da Fabio.
