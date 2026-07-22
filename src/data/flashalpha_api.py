import os
import json
import requests
from pathlib import Path

API_KEY = "AwIKtBUk0rZJUr1itbkN1JtCwvmhFEarXKk9JUXh"
BASE_URL = "https://lab.flashalpha.com/v1/exposure/gex"

# Flag globale: se la quota è esaurita non ritentiamo più nella stessa run
_QUOTA_EXHAUSTED = False

def fetch_and_update_gex(target_date_str: str) -> dict:
    """
    Chiama l'API di FlashAlpha per ottenere i livelli GEX del Nasdaq (NQ)
    e aggiorna il file config/daily_gex.json.
    
    Nota: Per il piano gratuito è obbligatorio specificare la data di scadenza (expiration).
    Normalmente, per l'intraday, si passa la data odierna (0DTE).
    """
    global _QUOTA_EXHAUSTED
    
    # Se la quota è già nota come esaurita, non ritentare
    if _QUOTA_EXHAUSTED:
        return {}
    
    # Se la data è già in cache sul disco, non chiamare l'API
    base_dir = Path("C:/Users/Mauro/Documents/nq-backtest-clean")
    config_path = base_dir / 'config' / 'daily_gex.json'
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
                if target_date_str in cached and cached[target_date_str]:
                    return cached[target_date_str]
        except Exception:
            pass

    url = f"{BASE_URL}/NQ%3DF"
    
    headers = {
        "X-Api-Key": API_KEY,
        "Accept": "application/json"
    }
    
    params = {
        "expiration": target_date_str
    }
    
    print(f"Scaricando dati GEX da FlashAlpha per la scadenza: {target_date_str}...")
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 429:
        print(f"  [GEX] Quota API FlashAlpha esaurita. GEX disabilitato per questa run.")
        _QUOTA_EXHAUSTED = True
        return {}
    
    if response.status_code != 200:
        print(f"Errore API ({response.status_code}): {response.text}")
        return {}
        
    data = response.json()
    
    # Estrazione Zero Gamma (Gamma Flip)
    zero_gamma = data.get("gamma_flip")
    if zero_gamma is None:
        # Se l'API ritorna null, possiamo fare una stima o loggare l'assenza
        print("Avviso: gamma_flip ritornato nullo dall'API (forse scadenza vuota o weekend).")
        zero_gamma = 0
        
    # Estrazione Call Wall e Put Wall
    # Il Call Wall è lo strike con il 'call_gex' o 'net_gex' positivo più alto
    # Il Put Wall è lo strike con il 'put_gex' o 'net_gex' negativo più grande (valore assoluto)
    call_wall_strike = 0
    max_call_gex = 0
    put_wall_strike = 0
    min_put_gex = 0 # Ricordiamo che il GEX put è spesso negativo o noi cerchiamo la concentrazione massima
    
    strikes = data.get("strikes", [])
    for s in strikes:
        strike_price = s.get("strike", 0)
        c_gex = s.get("call_gex", 0)
        p_gex = s.get("put_gex", 0)
        
        if c_gex > max_call_gex:
            max_call_gex = c_gex
            call_wall_strike = strike_price
            
        # Troviamo il picco massimo delle Put (assumendo che p_gex sia positivo come size, oppure negativo)
        # Alcuni provider usano numeri negativi per le Put, usiamo il valore assoluto per sicurezza
        if abs(p_gex) > abs(min_put_gex):
            min_put_gex = p_gex
            put_wall_strike = strike_price

    result = {
        "zero_gamma": float(zero_gamma),
        "call_wall": float(call_wall_strike),
        "put_wall": float(put_wall_strike),
        "notes": "Dati scaricati automaticamente da FlashAlpha API"
    }
    
    # Aggiorna il file JSON
    base_dir = Path("C:/Users/Mauro/Documents/nq-backtest-clean")
    config_path = base_dir / 'config' / 'daily_gex.json'
    
    current_config = {}
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            try:
                current_config = json.load(f)
            except json.JSONDecodeError:
                current_config = {}
                
    current_config[target_date_str] = result
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(current_config, f, indent=2)
        
    print(f"Livelli GEX aggiornati con successo per il {target_date_str}: {result}")
    return result

if __name__ == "__main__":
    # Test per vedere se il formato dell'API cambia o se funziona tutto
    fetch_and_update_gex("2026-07-17")
