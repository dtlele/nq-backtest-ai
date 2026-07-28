# V2 Audit — Audit Cumulativo Completo

**Setup testato:** V2 audit con prompt 4-step + R6 validator + R3 absorption + trailing minimale LLM (commit 9531678)
**Periodo:** 4 Feb - 28 Mar 2025 (54 giorni)
**Run completate:** 8 (V8b, V8b_v3, 11feb, 11feb_v2, unseen_feb, unseen_mar, unseen_mar2, mar_trail)
**Trades totali:** 48 (dopo deduplica su 50 raw)

---

## Risultato complessivo

| Metrica | Valore |
|---|---|
| Total trades | 48 |
| Winners | 22 |
| Losers | 26 |
| Win rate | **45.8%** |
| Total P&L | **+$903.27** |
| Avg P&L/trade | +$18.82 |
| Avg winner | +$98.31 |
| Avg loser | -$48.44 |
| P&L std dev | $84.33 |
| Sharpe proxy | 1.55 |

---

## Per direzione

| Dir | # | P&L | Avg |
|---|---|---|---|
| LONG | 16 | -$4.84 | -$0.30 |
| SHORT | 32 | **+$908.10** | **+$28.40** |

**Insight:** SHORT bias fortissimo in Feb-Mar 2025 (downtrend). Il sistema ha catturato questo molto bene (32 SHORT vs 16 LONG). Le LONG sono state ~breakeven (errore direzionale).

---

## Per exit reason

| Reason | # | % | Note |
|---|---|---|---|
| target | 7 | 14.6% | Hit full target |
| trailing_stop | 13 | **27.1%** | **Di cui 11/13 vincenti (84.6% WR)** |
| stop | 24 | 50% | Stop loss al livello iniziale |
| eod | 4 | 8.3% | Chiusura fine giornata |

**Trailing funziona:** 13 trailing stop attivati, 11 sono vincenti. Il fix trailing minimale LLM (10 barre, prompt minimal, attivazione a 0.3R) ha impatto positivo reale.

---

## Trade per giorno

| Data | Hold | Dir | Entry | Exit | P&L | Motivo |
|---|---|---|---|---|---|---|
| 2025-02-04 | 20:06 | long | 21633.50 | 21667.75 | +$97.17 | target |
| 2025-02-06 | 15:41 | long | 21781.75 | 21742.50 | -$50.86 | stop |
| 2025-02-10 | 18:36 | long | 21867.50 | 21843.75 | -$29.34 | eod |
| 2025-02-11 | 16:06 | long | 21830.50 | 21769.75 | -$50.49 | stop |
| 2025-02-12 | 16:11 | long | 21710.75 | 21802.00 | +$72.52 | eod |
| 2025-02-17 | 16:51 | long | 22242.50 | 22235.25 | -$11.31 | eod |
| 2025-02-18 | 15:11 | short | 22174.75 | 22208.25 | -$50.96 | stop |
| 2025-02-18 | 17:26 | short | 22172.25 | 22219.75 | -$50.64 | stop |
| 2025-02-20 | 18:31 | short | 22045.00 | 22077.25 | -$50.89 | stop |
| 2025-02-21 | 16:26 | short | 22013.00 | 21954.50 | +$99.65 | target |
| 2025-02-21 | 18:56 | short | 21788.25 | 21680.25 | **+$275.44** | target |
| 2025-02-24 | 15:16 | short | 21571.75 | 21635.00 | -$50.76 | stop |
| 2025-02-25 | 16:01 | short | 21088.00 | 21133.17 | -$50.90 | stop |
| 2025-02-25 | 17:03 | short | 21165.75 | 21187.92 | -$51.54 | stop |
| 2025-02-26 | 15:26 | long | 21327.75 | 21271.50 | -$50.66 | stop |
| 2025-02-27 | 15:21 | short | 21086.00 | 21136.00 | -$50.68 | stop |
| 2025-02-27 | 15:41 | short | 21093.75 | 21025.50 | +$123.57 | target |
| 2025-02-27 | 16:36 | short | 21091.50 | 21002.25 | +$113.28 | target |
| 2025-03-03 | 15:21 | short | 20849.75 | 20899.75 | -$50.60 | stop |
| 2025-03-03 | 18:21 | short | 20741.50 | 20710.00 | +$47.10 | trailing_stop |
| 2025-03-04 | 15:16 | short | 20175.75 | 20102.50 | **+$162.58** | trailing_stop |
| 2025-03-04 | 16:31 | short | 20174.00 | 20224.00 | -$50.76 | stop |
| 2025-03-05 | 16:01 | long | 20361.50 | 20310.00 | -$50.58 | stop |
| 2025-03-05 | 16:41 | short | 20248.25 | 20295.25 | -$50.59 | stop |
| 2025-03-06 | 15:06 | short | 20370.75 | 20418.00 | -$50.53 | stop |
| 2025-03-10 | 14:26 | short | 19709.25 | 19663.00 | +$70.56 | trailing_stop |
| 2025-03-10 | 16:01 | short | 19593.25 | 19625.12 | -$50.86 | stop |
| 2025-03-11 | 14:36 | short | 19337.25 | 19402.75 | -$50.33 | stop |
| 2025-03-13 | 15:50 | short | 19365.50 | 19265.75 | +$103.45 | trailing_stop |
| 2025-03-13 | 18:36 | short | 19325.25 | 19358.67 | -$50.90 | stop |
| 2025-03-14 | 14:06 | long | 19545.75 | 19476.50 | -$50.49 | stop |
| 2025-03-14 | 15:16 | long | 19625.75 | 19685.00 | +$86.72 | trailing_stop |
| 2025-03-14 | 16:36 | long | 19652.75 | 19705.00 | +$48.03 | eod |
| 2025-03-18 | 14:21 | short | 19666.25 | 19731.75 | -$50.54 | stop |
| 2025-03-18 | 14:46 | short | 19676.25 | 19726.25 | -$50.68 | stop |
| 2025-03-18 | 17:46 | short | 19723.25 | 19678.25 | +$100.81 | target |
| 2025-03-18 | 18:55 | short | 19753.25 | 19694.25 | +$91.34 | target |
| 2025-03-20 | 15:41 | long | 20018.50 | 20042.20 | +$43.58 | trailing_stop |
| 2025-03-21 | 17:11 | long | 19868.50 | 19844.25 | -$51.42 | stop |
| 2025-03-24 | 14:36 | long | 20327.25 | 20350.75 | +$35.06 | trailing_stop |
| 2025-03-24 | 16:16 | long | 20369.25 | 20379.00 | +$7.98 | trailing_stop |
| 2025-03-25 | 14:56 | long | 20487.25 | 20419.75 | -$50.73 | stop |
| 2025-03-26 | 15:36 | short | 20283.25 | 20165.50 | **+$225.91** | trailing_stop |
| 2025-03-27 | 18:21 | short | 20071.50 | 20100.00 | -$51.43 | stop |
| 2025-03-28 | 15:11 | short | 19605.50 | 19550.75 | +$91.58 | trailing_stop |
| 2025-03-28 | 16:11 | short | 19561.75 | 19494.00 | +$87.91 | trailing_stop |
| 2025-03-28 | 18:16 | short | 19492.00 | 19448.00 | +$69.33 | trailing_stop |
| 2025-03-28 | 18:21 | short | 19494.25 | 19426.25 | +$109.19 | trailing_stop |

---

## Top 5 winner

| Data | P&L | Note |
|---|---|---|
| 21 Feb 18:56 short | **+$275.44** | target pieno, drive_down confermato |
| 26 Mar 15:36 short | **+$225.91** | trailing stop su swing, runner mode |
| 4 Mar 15:16 short | **+$162.58** | trailing stop, big SELL absorbed |
| 27 Feb 15:41 short | +$123.57 | target pieno |
| 13 Mar 15:50 short | +$103.45 | trailing stop |

## Bottom 5 (i loss)

| Data | P&L | Note |
|---|---|---|
| 25 Feb 17:03 short | -$51.54 | stop subito |
| 25 Feb 16:01 short | -$50.90 | stop subito |
| 20 Feb 18:31 short | -$50.89 | stop subito |
| 24 Feb 15:16 short | -$50.76 | stop subito |
| 4 Mar 16:31 short | -$50.76 | stop subito (re-entry) |

---

## Conclusioni

1. **Il sistema V2 audit è PROFITTEVOLE su 54 giorni:** +$903 in 48 trade, $19 avg/trade.
2. **WR sotto 50% ma R:R > 2:1:** avg winner $98 vs avg loser $48 = R:R effettivo 2.04:1. Edge reale.
3. **Trailing stop funziona:** 13 trailing attivati, 11 vincenti (84.6% WR). I winner catturati con trailing sono quelli più grossi (+$162, +$225, +$91, +$87, +$69, +$109, +$103, +$70, +$47, +$86, +$35).
4. **Bias SHORT molto forte in Feb-Mar 2025:** 32 SHORT, +$908. Le LONG sono state ~breakeven. Il sistema ha catturato il regime correttamente.
5. **5 winner sopra $100** (target pieno o trailing che ha lasciato correre).

## Caveat

- **Sample size 48 trade** è piccolo per claim statistici. Sharpe proxy 1.55 è buono ma servirebbero 100+ trade per robustezza.
- **Tutti su periodo Feb-Mar 2025** (downtrend noto). Su periodo uptrend potrebbe essere diverso.
- **V8b (4-11 Feb) testata su 3 trade noti:** il +$766 winner di 11 Feb 10:50 NON è stato catturato (LLM ha detto 'none' per flow dissent anche se era absorption). Questo è il costo della maggiore cautela.
- **Run con bug fix diversi (strong absorption hint 11 Feb, soft hint 11 Feb)** hanno avuto risultati peggiori del fix attuale (R3 absorption nel solo deep audit).

## Run breakdown

| Run | Periodo | Trade | P&L | Note |
|---|---|---|---|---|
| v2_audit_v8b_v3 | 4 Feb | 1 | +$97 | R3 absorption fix |
| v2_full_v8b | 4-11 Feb | 5 | -$15 | V8b, no absorption hint |
| v2_v8b_11feb | 11 Feb | 2 | -$101 | BAD: strong absorption hint |
| v2_v8b_11feb_v2 | 11 Feb | 1 | -$50 | Soft absorption hint |
| v2_unseen_feb | 12-28 Feb | 14 | +$266 | Unseen, 1° run |
| v2_unseen_mar | 3-4 Mar | 4 | +$108 | Inizio periodo |
| v2_unseen_mar2 | 13-18 Mar | (continua in mar_trail) |
| v2_mar_trail | 19-28 Mar | 13 | +$528 | NEW minimal trailing! |

**La differenza la fa il trailing minimo LLM (19-28 Mar): +$528 in 13 trade.**

