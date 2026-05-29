import os
from openai import OpenAI
from dotenv import load_dotenv

def test_openrouter():
    load_dotenv()
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY non trovata nell'ambiente (o nel file .env).")
        return
    
    print(f"🔑 Chiave trovata: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else ''}")
    
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        
        print("⏳ Invio richiesta di test a OpenRouter (modello: google/gemini-2.5-flash)...")
        response = client.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=[
                {"role": "user", "content": "Rispondi solo con la parola 'OK'."}
            ],
            extra_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "NQ Backtest Test",
            }
        )
        
        print(f"✅ Successo! Risposta: {response.choices[0].message.content}")
        
    except Exception as e:
        print(f"❌ Errore durante la richiesta API: {e}")

if __name__ == "__main__":
    test_openrouter()
