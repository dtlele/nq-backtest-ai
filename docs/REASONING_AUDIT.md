# Audit Bulk Reasoning — 19 trade con decision='trade'

**File analizzato:** `agent_memory_backup/reasoning_log.jsonl` (648 entries, 19 trade)
**Periodo log:** 2025-02-03 → 2026-01-09 (mix di run)
**Prompt atteso:** 4-step chain-of-thought forzato

---

## Risultato compliance al 4-step prompt

| Completezza | # | % |
|---|---|---|
| 4/4 fasi presenti | **0** | **0%** |
| 3/4 fasi presenti | 10 | 53% |
| 2/4 fasi presenti | 9 | 47% |

**Fase più mancante: STEP2_AUCTION (100%, 19/19 trade)**

| Step | % mancante | Note |
|---|---|---|
| STEP1_BIAS | 42% | Modello spesso non dichiara bias esplicitamente |
| STEP2_AUCTION | **100%** | **CRITICO**: fase d'asta mai analizzata |
| STEP3_SIGNATURE | 11% | Quasi sempre presente |
| STEP4_LOCATION | 0% | Sempre presente |

---

## Esempi specifici

### Caso 1: 2026-01-09 10:32 LONG (manca STEP1+2)
> "Il prezzo ha rotto l'IB High con forte volume e delta positivo, confermando un trend rialzista. Gli ultimi big trades sono concentrati sul lato bid, indicando assorbimento istituzionale. La presenza di ordini passivi significativi a 25818.00 offre uno stop strutturale solido."
- ❌ Bias non dichiarato
- ❌ Fase asta non analizzata

### Caso 2: 2025-02-03 10:01 SHORT (manca solo STEP2)
> "Anchor: Wall @ 21156.25. Price at 21169 sits below VAL (21177.25)... 3 of 4 experts agree on short bias with med strength. The Wall at L4 is the last defense—if it breaks, downside accelerates. Flow's weak long call lacks conviction..."
- ✅ Bias esplicito
- ✅ Location esplicita
- ❌ Fase asta non analizzata

### Caso 3: 2025-02-03 10:12 SHORT (manca solo STEP2)
> "Anchor: Wall @ 21149.5. Price sits directly on L4 Wall (21149.5), below VAL (21170.75) and POC (21201.75), confirming bearish structure. 3 of 4 experts align short with med strength..."
- ✅ Bias esplicito
- ❌ Fase asta

---

## Implicazioni

Il prompt 4-step è un'**intenzione** ma il modello:
1. **Salta sistematicamente Step 2 (fase asta)** perché richiede 4+ keyword specifiche
2. **Spesso omette Step 1 (bias)** perché deduce la direzione implicitamente
3. **Step 3+4 sono naturali** (sa fare order flow + livelli)

## Raccomandazioni

1. **Rendere Step 2 concreto**: domande sì/no + JSON obbligatorio
2. **Forzare output strutturato** invece di testo libero
3. **Validatore post-LLM**: se manca keyword "auction phase", forza 'none'
4. **Prompt con template fisso** che il modello deve riempire

## Statistiche run baseline (prod1-yellow)

- 48 trade totali su 4 mesi (Feb-Mar 2025)
- +$903 totali, WR 45.8%, avg winner $98 vs avg loser $48 (R:R 2:1)
- Il sistema PROFITTA ma il reasoning è incompleto
- Forse con reasoning completo la qualità migliorerebbe
