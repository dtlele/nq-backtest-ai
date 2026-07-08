import asyncio
from ib_insync import *
import pytz
from datetime import datetime

# Setup del fuso orario di New York
ET = pytz.timezone("America/New_York")

class IBKRLiveFeed:
    def __init__(self, host='127.0.0.1', port=4001, client_id=1):
        """
        Inizializza la connessione a IB Gateway.
        Usa la porta 4001 per Live, 4002 per Paper Trading.
        """
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        
        # Definiamo il contratto del Nasdaq 100 (CME)
        # NQ con exchange CME
        self.contract = Future(symbol='NQ', exchange='CME', currency='USD')
        
    def connect(self):
        print(f"[INFO] Tentativo di connessione a IB Gateway su {self.host}:{self.port}...")
        try:
            self.ib.connect(self.host, self.port, clientId=self.client_id)
            print("[INFO] Connessione a Interactive Brokers riuscita!")
            
            # Qualifichiamo il contratto per avere tutti i dettagli (conid, multiplier, ecc.)
            self.ib.qualifyContracts(self.contract)
            print(f"[INFO] Contratto qualificato: {self.contract}")
        except Exception as e:
            print(f"[ERROR] Impossibile connettersi: {e}")
            print("Assicurati che IB Gateway sia aperto e che l'API (porta 4001/4002) sia abilitata.")
            
    def on_pending_tickers(self, tickers):
        """
        Callback chiamata ogni volta che IBKR invia un nuovo tick.
        """
        for t in tickers:
            if t.contract == self.contract:
                now_et = datetime.now(ET).strftime("%H:%M:%S")
                if t.last and t.lastSize:
                    print(f"[{now_et} ET] NQ Tick -> Prezzo: {t.last} | Size: {t.lastSize} | Bid: {t.bid} Ask: {t.ask}", end="\r")
                    
                    if t.lastSize >= 300:
                        print(f"\n🚀 [INSTITUTIONAL] Mega Trade Rilevato dal CME! {t.lastSize} contratti a {t.last}!")

    def start_live_stream(self):
        """
        Richiede i dati in tempo reale e mantiene attivo il loop.
        """
        if not self.ib.isConnected():
            return
            
        print("\n[INFO] Richiesta dati di mercato in corso (Livello 1)...")
        # Richiediamo i dati di Livello 1 per ricevere Bid, Ask e Last Price
        ticker = self.ib.reqMktData(self.contract, '', False, False)
        
        self.ib.pendingTickersEvent += self.on_pending_tickers
        
        print("[INFO] In attesa dei tick. Premi Ctrl+C per fermare.\n")
        try:
            self.ib.run()
        except KeyboardInterrupt:
            print("\n[INFO] Chiusura in corso...")
        finally:
            self.ib.disconnect()

if __name__ == "__main__":
    # Avvia la classe sulla porta 4001 (Live) o 4002 (Paper)
    feed = IBKRLiveFeed(port=4001)
    feed.connect()
    feed.start_live_stream()
