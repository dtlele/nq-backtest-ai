# STATUS.md — Jarvis: Assistente Vocale per pi agent

## Stato Attuale: ✅ COMPLETATO (v1.0)

### Deliverable
| File | Stato | Righe |
|------|-------|-------|
| `jarvis.py` | ✅ Completo | ~530 righe |
| `config.json` | ✅ Configurato | modello free, wake word, VAD |
| `requirements.txt` | ✅ Dipendenze minime | 6 pacchetti |
| `STATUS.md` | ✅ Questo file | — |

### Architettura Realizzata

```
🎤 sounddevice → webrtcvad (VAD) → faster-whisper (STT IT)
  → pi --mode rpc (cervello, sessione persistente sul progetto NQ)
  → edge-tts (TTS italiano) → pygame (riproduzione audio)
```

### Componenti

1. **PiRPCClient** — Ponte bidirezionale con `pi --mode rpc`
   - Subprocess con stdin/stdout JSONL
   - Sessione persistente su `jarvis/.pi-sessions/`
   - Eventi streaming: `text_delta`, `tool_start/end`, `agent_settled`
   - ✅ Testato: risposta "Ecco un riepilogo del progetto in corso..." in italiano

2. **AudioCapture** — Acquisizione microfono + VAD + STT
   - `sounddevice.RawInputStream` (PCM16 16kHz mono)
   - `webrtcvad` con aggressività 3 (taglia bene il silenzio)
   - `faster-whisper` modello `base` su CPU (int8), lingua italiana
   - Lazy loading: whisper caricato al primo utilizzo

3. **TTSManager** — Sintesi vocale
   - `edge-tts` con voce `it-IT-DiegoNeural`
   - `pygame.mixer` per riproduzione MP3
   - Fallback silenzioso su `print()` se TTS fallisce

4. **Wake Word / PTT**
   - `mode=wakeword`: ascolto continuo, comando vale se inizia con "jarvis"
   - `mode=ptt`: trascrive tutto ciò che viene detto
   - Comando vocale "esci"/"chiudi" per terminare

### Test Eseguiti

| Test | Risultato |
|------|-----------|
| `import jarvis` | ✅ OK |
| Sintassi Python | ✅ OK (ast.parse) |
| RPC bridge: prompt → risposta | ✅ OK (65 caratteri in 30s, modello free) |
| Dipendenze installate | ✅ OK |
| `pi --mode rpc` con `-ne` | ✅ OK (risolve conflitto estensioni) |

### Problemi Risolti

1. **Conflitto estensioni pi**: Due estensioni registrano `memory_search` → risolto con flag `-ne`
2. **pi.cmd su Windows**: `subprocess.Popen("pi")` non trova il batch → risolto con `pi.cmd` esplicito
3. **Timeout modello free**: I modelli gratuiti OpenRouter sono lenti (10-30s per rispondere) → timeout aumentato a 30s
4. **`pkg_resources` mancante**: Python 3.13 + setuptools≥81 lo rimuove → pin `setuptools<81`

### Problemi Aperti

1. **Latenza STT**: `faster-whisper base` su CPU impiega ~3-5s per trascrivere una frase di 5s
2. **Latenza TTS**: `edge-tts` richiede chiamata HTTP (online) — ~2-3s per frase breve
3. **Latenza pi**: Modello free OpenRouter 10-30s. Consiglio: passare a modello a pagamento per uso reale
4. **pygame.mixer**: A volte non rilascia la risorsa audio → warning innocuo

### Come Usare

```powershell
cd C:\Users\Mauro\Documents\nq-backtest-clean\jarvis

# Installare dipendenze
python -m pip install -r requirements.txt
python -m pip install "setuptools<81"   # necessario per Python 3.13

# Modalità wake word (default)
python jarvis.py

# Modalità push-to-talk
python jarvis.py --mode ptt

# Con modello specifico
python jarvis.py --model "openrouter/deepseek/deepseek-chat"
```

### Prossimi Miglioramenti (v1.1)

- [ ] `--dry-run`: test senza microfono, simula input da tastiera
- [ ] Timer silenzio configurabile per modalità PTT
- [ ] Cache sessione pi per ripristino rapido
- [ ] Supporto CUDA opzionale per whisper (GPU ~10x più veloce)
- [ ] Interruzione vocale ("basta così") durante la risposta