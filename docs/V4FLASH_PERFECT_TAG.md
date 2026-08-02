# 🏷️ prod-v4flash-perfect — TAG DI SICUREZZA

## Cosa protegge
La run V4 Flash **perfetta** (3 LONG, +$77.59):
- 4 Feb LONG +$53.88 (trailing)
- 6 Feb LONG +$42.26 (trailing)
- 6 Feb LONG -$51.49 (stop)
- 10 Feb LONG +$32.94 (trailing)

## Commit esatto
- **Tag**: `prod-v4flash-perfect` → punta a `2689eeb`
- **2689eeb**: feat(prompt): CHOP/BALANCE evidence threshold + absorption/delta-divergence (11:22 02/08)
- Questo era il codice ATTIVO quando la run è partita (12:18)

## Configurazione della run perfetta
- Modello: `deepseek/deepseek-v4-flash` (NON 0731)
- Trailing: trigger **0.8**, lock 50% a 1.5R, lock 75% a 2.5R, **NESSUN buffer**
- Prompt: 4-step + CHOP evidence threshold (2689eeb)
- Fabio-only, scalper mode, single process

## Come tornare
```bash
git checkout prod-v4flash-perfect
```

## ATTENZIONE
- Il commit `52d6989` (fix buffer trigger 1.5) è DOPO questo tag
- La run clean attuale (PID 706) usa 52d6989 con buffer — è un TEST, non la configurazione perfetta
- Se il test buffer fallisce → tornare a `prod-v4flash-perfect`
