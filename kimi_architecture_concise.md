## Diagnosi critica (3 peccati architettonici)

- **LLM fa aritmetica**: entry/stop/target come float generati dal Chief = allucinazioni geometriche. L'LLM deve scegliere *l'ancora* (ID livello), il codice calcola *il prezzo*.
- **VETO via string matching**: `"VETO" in report.upper()` è fragile. Serve output strutturato.
- **Risk Manager cieco**: il Bouncer valuta senza conoscere entry/stop proposti. Il rischio va validato *dopo* la decisione, sui numeri.

## Architettura target (pipeline)

```
Bar → FeatureEngine (deterministico) → MarketVector
    → Gate (light_analyze, pesi calibrati su storico)
    → Expert in parallelo (feature slice dedicata, NON stesso blob)
    → Chief LLM → TradeIntent {direction, setup, anchor_level_id, bias}
    → ExecutionCompiler (100% codice): entry/stop/target/size
    → RiskValidator (regole deterministiche + veto opzionale strutturato)
    → FabioSignal
```

## Contratti dati

**MarketVector** (calcolato 1x per barra, condiviso):
- `atr_m1, atr_m5, vwap_sigma_dist, delta_zscore, gex_regime (enum)`
- `levels: [{id, type: VAH/VAL/POC/swing/wall, price, size}]` → gli agenti referenziano `level_id`, mai prezzi liberi

**ExpertReport** (JSON obbligatorio, no prosa):
```json
{"bias": -1|0|1, "strength": 0-3, "key_level_ids": [], "invalidation_id": "L7"}
```
- Ogni expert riceve solo la sua slice: Flow→delta/walls, AMT→VA/POC/IB, GEX→regime. Meno token, meno rumore.

**TradeIntent** dal Chief: `{direction, setup_type, anchor_level_id, conviction: low/med/high}` — niente float.

## Stop/Risk deterministico (niente hardcode, niente prompt)

```
stop = anchor_price ± max(1.0 × ATR_m1, 8 tick)   # buffer = volatilità reale
risk_$ = equity × fixed_pct
contracts = risk_$ / (stop_dist × tick_value)
```
- **R:R minimo enforced in codice** post-compilazione: se target/entry < 1.5R → reject o riduci target a struttura.
- Confidence: derivata da confluence count + light_score, non dal numero 0-100 dell'LLM (non calibrato).

## Gestione trade attiva

Stesso split: LLM output `{decision, structural_event_id}`, il codice calcola `new_stop`.
Guardrail **in codice, non nel prompt**:
- stop long solo crescente (mai allargare)
- trailing attivo solo se `unrealized ≥ 1R` (check deterministico)
- `new_stop ≥ event_level ∓ buffer(ATR)`
- Regole tipo "1:1 prima di trailare" nel prompt = lo stesso hardcoding che odi, solo in linguaggio naturale. Spostale nel validatore.

## Quick wins (ordinati per ROI)

1. **Pydantic schema** su tutti gli output LLM (elimina il retry loop fragile).
2. **Risk come post-validator** con i numeri reali del trade: `{veto: bool, reason_code: enum}`.
3. **ExecutionCompiler**: 1 giornata di lavoro, elimina il 90% dei trade invalidi.
4. Modello economico per i 4 expert, modello forte solo per il Chief (latenza scalping).
5. `market_narrative` → structured state `{regime, trapped_side, active_levels}`, non prosa.
6. Calibra i pesi di `light_analyze` con regressione logistica sui trade storici invece di magic number.

**Principio guida**: l'LLM decide *direzione e struttura* (pattern recognition, suo punto forte); il codice decide *prezzi, size e validità* (geometria, suo punto debole). Mai il contrario.