import sys
import requests
import os

def send_telegram_message(message):
    # Puoi inserire il token e il chat_id qui sotto, oppure usare le variabili d'ambiente
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '8745379821:AAE3Oa2CUjrbVzRPW_yJyOwnpQHD4RXvjZ8')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '-1003723252971')
    
    if bot_token == 'INSERISCI_QUI_IL_TUO_BOT_TOKEN' or chat_id == 'INSERISCI_QUI_IL_TUO_CHAT_ID':
        print("Errore: Inserisci il Bot Token e il Chat ID nello script telegram_notifier.py")
        return
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Messaggio inviato su Telegram con successo!")
        else:
            print(f"Errore nell'invio del messaggio: {response.text}")
    except Exception as e:
        print(f"Errore di connessione a Telegram: {e}")

if __name__ == "__main__":
    # Legge l'output dello script precedente dalla riga di comando
    input_text = sys.stdin.read()
    
    if input_text.strip():
        # Formattiamo il testo con il tag <pre> per mantenere l'allineamento della tabella
        formatted_message = f"<b>📊 Aggiornamento Backtest NQ</b>\n<pre>{input_text}</pre>"
        send_telegram_message(formatted_message)
