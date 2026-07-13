---
name: minimax-video-analyst
description: Skill per utilizzare il modello Minimax e analizzare clip video di trading o sessioni di mercato.
---

# Minimax Video Analyst Skill

Questa skill permette agli agenti di utilizzare l'agente specializzato `minimax_agent.py` per guardare video (es. registrazioni di NinjaTrader o VolFix) e produrre insight testuali sull'azione dei prezzi, l'order flow o altre dinamiche visive.

## 🧠 Capacità
- **Video Encoding**: Converte il video locale in Base64 (tramite `llm_client.py`).
- **Analisi Multimodale**: Invia i fotogrammi a un modello LLM/VLM compatibile (es. `minimax/video-01` via OpenRouter).
- **Trading Focus**: Il prompt di sistema forza il modello a comportarsi da analista quantitativo esperto.

## 🛠 Utilizzo
Se l'utente fornisce il percorso a un video (`.mp4`, `.webm`, `.mkv`), esegui lo script:

```bash
python src/agents/minimax_agent.py "C:/percorso/del/video.mp4" "Cosa fa il footprint in questo momento?"
```

L'agente elaborerà la richiesta e stamperà un log di risposta.

## ⚠️ Requisiti
- OpenRouter API Key attiva in `.env`.
- Il modello target su OpenRouter deve supportare il parsing di URL base64 di tipo `video/*`.
