import pandas as pd
from typing import Dict, Any
from src.data_loader import load_day
import pytz

def process_overnight_session(filepath: str, target_date_str: str) -> Dict[str, Any]:
    """
    Legge il file trade di Databento e calcola le metriche della sessione overnight (Globex).
    La sessione RTH (Regular Trading Hours) inizia alle 09:30 ET. Tutto ciò che viene prima
    nella sessione CME (che inizia alle 18:00 ET del giorno prima) è considerato "Overnight".
    
    Args:
        filepath: Percorso al file `.trades.csv` di Databento
        target_date_str: Data del giorno di trading in formato 'YYYY-MM-DD'
        
    Returns:
        Dict contenente: VWAP, POC, High, Low, Total Volume
    """
    # Carichiamo i trade come DataFrame usando la funzione esistente
    df = load_day(filepath, as_df=True)
    if df.empty:
        return {}

    # I timestamp in Databento (ts_event) sono in UTC. Convertiamo l'indice in US/Eastern
    df = df.set_index('ts_event')
    df.index = df.index.tz_convert('US/Eastern')
    
    # La sessione CME per una data T inizia alle 18:00 ET del giorno T-1.
    # L'apertura RTH è alle 09:30 ET del giorno T.
    # Filtriamo i dati: prendiamo tutti i trade precedenti alle 09:30 ET del giorno target.
    # Nota: Databento normalmente raggruppa il file proprio per "Trading Session" CME.
    market_open = pd.Timestamp(f"{target_date_str} 09:30:00", tz='US/Eastern')
    
    overnight_df = df[df.index < market_open].copy()
    
    if overnight_df.empty:
        return {
            "overnight_high": None,
            "overnight_low": None,
            "overnight_vwap": None,
            "overnight_poc": None,
            "overnight_volume": 0
        }

    # Calcolo High / Low
    high = overnight_df['price'].max()
    low = overnight_df['price'].min()
    total_volume = overnight_df['size'].sum()
    
    # Calcolo VWAP: sum(Price * Volume) / sum(Volume)
    overnight_df['pv'] = overnight_df['price'] * overnight_df['size']
    vwap = overnight_df['pv'].sum() / total_volume if total_volume > 0 else 0
    
    # Calcolo POC (Point of Control): Il prezzo con il maggior volume scambiato
    volume_by_price = overnight_df.groupby('price')['size'].sum()
    poc = volume_by_price.idxmax() if not volume_by_price.empty else 0

    return {
        "overnight_high": float(high),
        "overnight_low": float(low),
        "overnight_vwap": float(round(vwap, 2)),
        "overnight_poc": float(poc),
        "overnight_volume": int(total_volume)
    }

if __name__ == "__main__":
    # Test isolato (simulazione)
    import os
    test_file = "C:/Users/Mauro/Documents/databento-data/glbx-mdp3-20250109.trades.csv"
    if os.path.exists(test_file):
        stats = process_overnight_session(test_file, "2025-01-09")
        print(f"Overnight Stats (9 Gennaio): {stats}")
    else:
        print("Test file non trovato. Verifica il percorso in C:/Users/Mauro/Documents/databento-data/")
