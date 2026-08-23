# Audit dei Ragionamenti di Trading (Run Eseguite)

**Totale candidati analizzati:** 6958

## 1. Decisioni Finali
- **no_trade**: 6142
- **trade**: 453
- **light_skip**: 358
- **prefiltered**: 5

## 2. Direzione proposta da Fabio
- **none**: 5893
- **short**: 598
- **light_skip**: 358
- **long**: 104
- **prefiltered**: 5

## 3. Motivi di No-Trade più frequenti
- `fabio_confidence=45 < 75 (Prudenza post-stop attiva)`: 1953 volte
- `fabio_confidence=40 < 75 (Prudenza post-stop attiva)`: 1567 volte
- `fabio_confidence=40 < 65`: 1133 volte
- `fabio_confidence=45 < 65`: 828 volte
- `fabio_confidence=30 < 75 (Prudenza post-stop attiva)`: 222 volte
- `fabio_confidence=30 < 65`: 97 volte
- `fabio_confidence=70 < 75 (Prudenza post-stop attiva)`: 68 volte
- `fabio_confidence=0 < 78`: 55 volte
- `fabio_confidence=65 < 75 (Prudenza post-stop attiva)`: 52 volte
- `fabio_confidence=35 < 75 (Prudenza post-stop attiva)`: 15 volte

## 4. Veti del Risk Manager (Totale veti espliciti: 55)
Il Risk Manager è intervenuto pesantemente per bloccare i trade. Ecco alcuni esempi di ragionamento di veto:

### Esempio Veto 1:
> VETOED BY RISK MANAGER. Reason: The trade is occurring during a trend-down day with price outside the Initial Balance, indicating strong momentum. However, the current bar shows mixed delta (+182) and lacks clear institutional absorption or strong initiative big trades confirming the short bias. Additionally, we are approaching the 09:45 EST news window, which often creates liquidity voids and artificial delta spikes. Given the proximity to this event and the lack of clear institutional confirmation, the trade carries elevated risk. The stop would need to be placed behind the recent swing high around 21233.25, which is within the 15-20 point range, but the timing is problematic. 

VETO...

### Esempio Veto 2:
> VETOED BY RISK MANAGER. Reason: The trade is too close to the 09:45 EST macroeconomic news window, which often creates liquidity voids and artificial delta spikes. Additionally, the current bar shows mixed delta (+38) with no clear institutional absorption or initiative big trades confirming trend continuation. The stop would need to be placed beyond recent structural levels, likely exceeding 20 points due to volatility. 

VETO...

### Esempio Veto 3:
> VETOED BY RISK MANAGER. Reason: VETO. The trade is too close to the 09:45 EST macroeconomic news window, which creates a liquidity void and increases volatility risk. Additionally, the current bar delta is -288, indicating mixed institutional participation and potential exhaustion rather than strong continuation. The stop would need to be wider than 15-20 points to account for the expected volatility spike, violating max drawdown constraints....


## 5. Ragionamenti sui Trade Approvati
### Esempio Trade Approvato 1:
> Price is below IVB low in a strong downtrend. Big trades show absorption (SELL @ 26029.00-26029.50) without significant price advancement, indicating trapped buyers. Entry at 26026.25 aligns with the absorption wall. Stop placed 2-3 ticks above the wall at 26036.25. Target set at 25976.25 for a favorable risk-to-reward ratio....

### Esempio Trade Approvato 2:
> Price is below IVB low (26118.75) with strong selling pressure (delta +359 on last bar). Big trades are concentrated at the bid, indicating institutional absorption. The market is in an imbalance phase below IVB, favoring shorts. Stop is placed 2-3 ticks above the recent high to protect against a reversal....

### Esempio Trade Approvato 3:
> Price has broken above IVB high (25576.5) with strong volume (14176) and positive delta (+190). Big trades (4018 contracts) show absorption at ask, indicating institutional buying. M1 footprint confirms aggressive buying in zones 25548-25615. Stop placed 20 ticks below entry at recent absorption cluster....

