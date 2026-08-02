# 🏆 DUAL AUDIT = setup vincente (4-11 Feb 2025)

## Confronto 3 vie
| Metrica | Perfetta (v4-flash solo) | Clean (0731 solo) | DUAL (0731+v4-flash audit) |
|---|---|---|---|
| Trade | 4 | 6 | 4 |
| WR | 50% | 33.3% | 50% |
| P&L | +$77.59 | -$42.23 | +$43.91 |
| PF | ~1.7 | 0.78 | 1.50 |

## Setup vincente
- Reflex: `deepseek/deepseek-v4-flash-0731` (aggressivo, vede di piu')
- Audit 2: `deepseek/deepseek-v4-flash` (conservativo, filtra)
- Trailing: buffer trigger 1.5R (lock 50% a 1.5R, 75% a 2.5R)
- Doppio voto: un REJECT basta per bocciare (commit fa4ce52)

## Perche' vince
1. Buffer: il 4 Feb LONG va a target +$90.84 (vs +$53.88 tagliato)
2. Dual audit: blocca i 2 short pericolosi del 5 Feb (-$104 evitati)
3. 0731 da solo = troppo aggressivo (-$42.23)

## Comando validazione estesa (in corso)
PID 1940: --start-date 20250212 --end-date 20250430
