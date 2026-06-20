import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, time

def get_session_ib(df_day, ib_start_hour=8, ib_start_minute=0):
    """
    Calcola l'Initial Balance (IB) basato sulla prima candela a 30m 
    all'apertura della sessione di riferimento (es. 8:00 AM).
    Restituisce: (ib_high, ib_low, poc)
    """
    # Filtra la candela che rappresenta l'apertura
    open_bars = df_day[(df_day['time'].dt.hour == ib_start_hour) & 
                       (df_day['time'].dt.minute == ib_start_minute)]
    
    if open_bars.empty:
        return None, None, None
        
    ib_bar = open_bars.iloc[0]
    ib_high = ib_bar['high']
    ib_low = ib_bar['low']
    poc = (ib_high + ib_low) / 2  # Semplificazione del POC a metà del range IB
    
    return ib_high, ib_low, poc

def check_ibob_failed_auction(symbol="XAUUSD", timeframe=mt5.TIMEFRAME_M30, num_bars=500):
    if not mt5.initialize():
        print(f"Errore di inizializzazione MT5: {mt5.last_error()}")
        return

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, num_bars)
    if rates is None:
        print(f"Errore nel recupero dati per {symbol}")
        mt5.shutdown()
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df['date'] = df['time'].dt.date
    
    print(f"Analisi completata su {len(df)} candele per {symbol}. Ultima candela: {df.iloc[-1]['time']}")
    print("Ricerca setup 'Failed Auction' (Mean Reversion verso il POC)...\n")
    
    found_setup = False
    
    # Raggruppa per giorno
    for date, df_day in df.groupby('date'):
        # Calcola l'IB per il giorno corrente (es. candela delle 08:00)
        ib_high, ib_low, poc = get_session_ib(df_day, ib_start_hour=8)
        
        if ib_high is None:
            continue
            
        # Analizza le candele SUCCESSIVE all'Initial Balance
        post_ib_df = df_day[df_day['time'].dt.hour >= 8].iloc[1:]
        
        for idx, row in post_ib_df.iterrows():
            # SETUP LONG (Failed Auction al IB Low)
            # 1. Il prezzo rompe sotto l'IB Low (Sweep / First Drive)
            # 2. Il corpo della candela chiude SOPRA l'IB Low (Accettazione fallita, rientro nel range)
            if row['low'] < ib_low and row['close'] > ib_low:
                # Controlliamo che non sia una rottura enorme per evitare falsi positivi
                if (row['open'] >= ib_low) or (abs(row['close'] - ib_low) < (ib_high - ib_low) * 0.5):
                    print(f"🟢 SETUP LONG TROVATO! Data/Ora: {row['time']}")
                    print(f"    Sweep sotto IB Low ({ib_low}) fallito. Prezzo rientrato a {row['close']}")
                    print(f"    Target (POC): {poc}")
                    print(f"    Stop Loss: NO HARD SL. Uscita strutturale sotto {row['low']} (in chiusura 30m).")
                    print("-" * 50)
                    found_setup = True
                    
            # SETUP SHORT (Failed Auction al IB High)
            # 1. Il prezzo rompe sopra l'IB High (Sweep / First Drive)
            # 2. Il corpo della candela chiude SOTTO l'IB High (Accettazione fallita, rientro nel range)
            elif row['high'] > ib_high and row['close'] < ib_high:
                if (row['open'] <= ib_high) or (abs(ib_high - row['close']) < (ib_high - ib_low) * 0.5):
                    print(f"🔴 SETUP SHORT TROVATO! Data/Ora: {row['time']}")
                    print(f"    Sweep sopra IB High ({ib_high}) fallito. Prezzo rientrato a {row['close']}")
                    print(f"    Target (POC): {poc}")
                    print(f"    Stop Loss: NO HARD SL. Uscita strutturale sopra {row['high']} (in chiusura 30m).")
                    print("-" * 50)
                    found_setup = True

    if not found_setup:
        print("Nessun setup IBOB 'Failed Auction' trovato di recente.")

    mt5.shutdown()

if __name__ == "__main__":
    check_ibob_failed_auction(symbol="XAUUSD")
