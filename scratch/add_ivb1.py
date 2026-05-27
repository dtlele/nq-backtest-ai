import json

file_path = 'knowledge/fabio_knowledge.json'
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

ivb_model_1_text = """### IVB Model 1 (Continuazione del Trend)
Il modello IVB 1 è il setup primario di continuazione del trend di Fabio Valentini, progettato per operare a favore del momentum istituito dal breakout della prima ora (o mezz'ora) di scambi.

**1. Il Contesto (Breakout IVB):**
*   Il mercato deve aver rotto con decisione (chiusura full-body) l'estremità superiore (High) o inferiore (Low) del range Initial Volume Breakout (IVB).
*   Il breakout deve essere supportato da un'aggressività istituzionale misurabile (es. Big Trades >30 contratti sul NQ).

**2. Il Pullback (La Zona di Reload):**
*   Fabio non entra mai sul primo "drive" (primo impulso). Attende un ritracciamento fisiologico del prezzo verso una zona di equilibrio.
*   Questa zona è tipicamente il **Value Area High/Low (VAH/VAL)** del range appena rotto, oppure il **POC (Point of Control)** o un **Low Volume Node (LVN)** lasciato dal movimento impulsivo.

**3. L'Assorbimento (Il Muro Istituzionale):**
*   Quando il prezzo raggiunge la zona di "reload", l'orderflow deve mostrare **assorbimento** dei trader che cercano di invertire il trend.
*   **Per un Long:** I venditori aggressivi spingono giù il prezzo nel pullback, "tirano pugni al muro" (alti volumi di vendita) ma il prezzo si ferma. Le "Deep Trades" (grandi bolle rosse) vengono assorbite dai limit order passivi dei compratori istituzionali.

**4. L'Ingresso (Il Second Drive):**
*   L'ingresso avviene quando il mercato dimostra di rigettare il pullback e riprende la direzione originaria (il "Second Drive").
*   **Trigger M1:** Si entra con ordine a mercato non appena si forma una candela di inversione M1 (o M5) che "distrugge" il muro di assorbimento, confermando che i compratori/venditori istituzionali hanno ripreso il controllo dell'asta.

**5. Gestione del Rischio:**
*   Lo Stop Loss è chirurgico: piazzato 1-3 tick dietro il cluster istituzionale ("wall") che ha difeso il livello durante il pullback. Se quel muro viene rotto, l'ipotesi di continuazione è invalidata e si esce immediatamente.
*   Target primario ("Protection Level") al successivo High/Low di sessione o estensione algoritmica statistica, con break-even molto veloce (spesso in 20-30 secondi) non appena parte il momentum."""

if 'simplified_strategy' not in data:
    data['simplified_strategy'] = {}

data['simplified_strategy']['ivb_model_1'] = ivb_model_1_text

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Added ivb_model_1 to knowledge.")
