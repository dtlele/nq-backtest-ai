# Report di Ottimizzazione Strategia Whale Print (FundedNext 50k CFD)

## 1. Executive Summary & Parametri Prop Firm
Il presente report analizza le prestazioni della strategia **Whale Print** ottimizzata per superare e mantenere la gestione del conto **FundedNext 50k CFD**.

### Parametri di Rischio Prop Firm FundedNext 50k:
- **Capitale del Conto**: $50,000
- **Max Drawdown Ammesso**: **$2,500** (5.0% limite massimo assoluto/trailing)
- **Rischio per Trade Raccomandato**: **0.15% - 0.25%** ($75 - $125 a operazione)
- **Costi di Negoziazione Realistici**: **$14.00 totali per trade per 1 NQ Mini** ($4.00 commissione round-turn + $10.00 slippage/spread per 0.5 punti di NQ)
- **Dataset Analizzato**: 2,070 trade puliti registrati su dati tick MBO Databento (gennaio 2025 - giugno 2026).

---

## 2. Risultati della Grid Search (Finestre Orarie x Size Whales x Exit Rules)

| Finestra Oraria RTH | Size Whale (Contratti) | Exit Strategy | N. Trade | Win Rate (%) | Profit Factor | Net PnL 1 NQ ($) | Max DD 1 NQ ($) | Consec Losses |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 90-160 contratti (Strict Whales) | SL 20 pt / TP 50 pt | 421 | 40.86% | **1.32** | $31,936.00 | $8,675.00 | 11 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 90-160 contratti (Strict Whales) | SL 20 pt / TP 40 pt | 421 | 43.71% | **1.29** | $27,971.00 | $10,540.00 | 7 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-150 contratti (Sottomarginatura 3) | SL 20 pt / TP 50 pt | 547 | 40.59% | **1.29** | $39,037.00 | $8,593.00 | 14 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 70-150 contratti (Sottomarginatura 2) | SL 20 pt / TP 50 pt | 714 | 40.34% | **1.27** | $48,739.00 | $10,629.00 | 17 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-160 contratti (Sottomarginatura 1) | SL 20 pt / TP 50 pt | 565 | 40.18% | **1.26** | $37,355.00 | $9,769.00 | 14 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 90-160 contratti (Strict Whales) | Holding Fixed 15-min | 421 | 51.78% | **1.26** | $59,866.00 | $22,255.00 | 8 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 70-150 contratti (Sottomarginatura 2) | SL 20 pt / TP 40 pt | 714 | 42.86% | **1.23** | $39,369.00 | $11,391.00 | 13 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 90-160 contratti (Strict Whales) | SL 25 pt / TP 50 pt | 421 | 43.23% | **1.23** | $25,891.00 | $10,415.00 | 11 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-150 contratti (Sottomarginatura 3) | SL 20 pt / TP 40 pt | 547 | 42.78% | **1.22** | $29,377.00 | $9,593.00 | 8 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-150 contratti (Sottomarginatura 3) | SL 25 pt / TP 50 pt | 547 | 43.51% | **1.22** | $33,522.00 | $10,348.00 | 14 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 70-190 contratti (Baseline) | SL 20 pt / TP 50 pt | 796 | 39.32% | **1.22** | $43,531.00 | $12,450.00 | 19 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-160 contratti (Sottomarginatura 1) | SL 20 pt / TP 40 pt | 565 | 42.48% | **1.21** | $28,295.00 | $10,769.00 | 8 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-180 contratti (Medium Whales) | SL 20 pt / TP 50 pt | 601 | 39.10% | **1.21** | $31,456.00 | $10,414.00 | 15 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 70-150 contratti (Sottomarginatura 2) | SL 25 pt / TP 50 pt | 714 | 43.42% | **1.21** | $41,009.00 | $10,816.00 | 12 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-160 contratti (Sottomarginatura 1) | SL 25 pt / TP 50 pt | 565 | 43.01% | **1.19** | $30,640.00 | $10,739.00 | 14 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 70-190 contratti (Baseline) | SL 20 pt / TP 40 pt | 796 | 41.96% | **1.19** | $36,941.00 | $12,237.00 | 15 |
| 1. Full RTH (09:30 - 16:00 EST) | 90-160 contratti (Strict Whales) | Holding Fixed 15-min | 1065 | 50.05% | **1.19** | $102,610.00 | $29,342.00 | 10 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-160 contratti (Sottomarginatura 1) | Holding Fixed 15-min | 565 | 51.50% | **1.18** | $56,785.00 | $27,708.00 | 9 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-180 contratti (Medium Whales) | SL 20 pt / TP 40 pt | 601 | 41.60% | **1.17** | $25,161.00 | $10,439.00 | 8 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-180 contratti (Medium Whales) | SL 25 pt / TP 50 pt | 601 | 42.60% | **1.17** | $28,031.00 | $12,278.00 | 15 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 70-190 contratti (Baseline) | SL 25 pt / TP 50 pt | 796 | 42.71% | **1.16** | $36,391.00 | $11,737.00 | 14 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-150 contratti (Sottomarginatura 3) | Holding Fixed 15-min | 1400 | 50.07% | **1.16** | $121,570.00 | $51,982.00 | 9 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 90-160 contratti (Strict Whales) | SL 30 pt / TP 60 pt | 421 | 43.71% | **1.16** | $20,351.00 | $10,078.00 | 8 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 70-150 contratti (Sottomarginatura 2) | SL 20 pt / TP 50 pt | 1234 | 40.03% | **1.16** | $47,479.00 | $11,665.00 | 11 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-160 contratti (Sottomarginatura 1) | Holding Fixed 15-min | 1457 | 49.83% | **1.16** | $122,732.00 | $56,994.00 | 9 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-150 contratti (Sottomarginatura 3) | Holding Fixed 15-min | 547 | 51.55% | **1.15** | $48,652.00 | $31,486.00 | 8 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 90-160 contratti (Strict Whales) | SL 20 pt / TP 50 pt | 637 | 39.25% | **1.15** | $22,997.00 | $12,057.00 | 16 |
| 1. Full RTH (09:30 - 16:00 EST) | 70-150 contratti (Sottomarginatura 2) | Holding Fixed 15-min | 1871 | 50.67% | **1.15** | $153,826.00 | $62,566.00 | 9 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-150 contratti (Sottomarginatura 3) | SL 30 pt / TP 60 pt | 547 | 44.06% | **1.15** | $25,217.00 | $12,524.00 | 9 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 70-150 contratti (Sottomarginatura 2) | SL 30 pt / TP 60 pt | 714 | 43.84% | **1.14** | $32,424.00 | $12,116.00 | 12 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 70-150 contratti (Sottomarginatura 2) | SL 20 pt / TP 50 pt | 1098 | 39.44% | **1.14** | $38,308.00 | $11,905.00 | 15 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 70-150 contratti (Sottomarginatura 2) | SL 25 pt / TP 50 pt | 1234 | 44.00% | **1.14** | $45,879.00 | $12,905.00 | 10 |
| 1. Full RTH (09:30 - 16:00 EST) | 70-190 contratti (Baseline) | Holding Fixed 15-min | 2070 | 50.68% | **1.13** | $155,305.00 | $71,831.00 | 10 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-180 contratti (Medium Whales) | Holding Fixed 15-min | 1544 | 49.68% | **1.13** | $111,019.00 | $62,287.00 | 9 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 100-180 contratti (Heavy Whales) | SL 20 pt / TP 40 pt | 321 | 40.19% | **1.13** | $9,616.00 | $13,741.00 | 9 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 90-160 contratti (Strict Whales) | SL 20 pt / TP 50 pt | 714 | 39.08% | **1.13** | $21,519.00 | $15,309.00 | 18 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-160 contratti (Sottomarginatura 1) | SL 30 pt / TP 60 pt | 565 | 43.54% | **1.12** | $22,065.00 | $13,752.00 | 9 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 90-160 contratti (Strict Whales) | SL 20 pt / TP 40 pt | 637 | 41.76% | **1.12** | $18,357.00 | $18,437.00 | 10 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-150 contratti (Sottomarginatura 3) | SL 20 pt / TP 50 pt | 833 | 38.78% | **1.12** | $25,293.00 | $11,941.00 | 21 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 70-190 contratti (Baseline) | SL 20 pt / TP 50 pt | 1361 | 39.46% | **1.12** | $40,756.00 | $14,630.00 | 11 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 70-150 contratti (Sottomarginatura 2) | Holding Fixed 15-min | 714 | 50.98% | **1.12** | $50,374.00 | $31,641.00 | 10 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 70-150 contratti (Sottomarginatura 2) | SL 20 pt / TP 40 pt | 1234 | 41.98% | **1.12** | $33,294.00 | $17,782.00 | 11 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 70-190 contratti (Baseline) | SL 30 pt / TP 60 pt | 796 | 43.34% | **1.11** | $29,011.00 | $15,643.00 | 14 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 70-190 contratti (Baseline) | SL 20 pt / TP 50 pt | 1210 | 39.01% | **1.11** | $34,125.00 | $14,188.00 | 12 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-160 contratti (Sottomarginatura 1) | SL 20 pt / TP 50 pt | 860 | 38.60% | **1.11** | $23,655.00 | $12,397.00 | 21 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 100-180 contratti (Heavy Whales) | SL 20 pt / TP 50 pt | 321 | 37.07% | **1.11** | $8,881.00 | $11,856.00 | 9 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 70-150 contratti (Sottomarginatura 2) | SL 25 pt / TP 50 pt | 1098 | 43.17% | **1.11** | $32,653.00 | $14,525.00 | 15 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 70-190 contratti (Baseline) | SL 25 pt / TP 50 pt | 1361 | 43.57% | **1.11** | $39,676.00 | $13,926.00 | 10 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 90-160 contratti (Strict Whales) | SL 25 pt / TP 50 pt | 637 | 42.54% | **1.11** | $18,397.00 | $12,387.00 | 16 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 70-190 contratti (Baseline) | Holding Fixed 15-min | 796 | 50.63% | **1.11** | $51,076.00 | $39,036.00 | 9 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-180 contratti (Medium Whales) | Holding Fixed 15-min | 601 | 50.42% | **1.11** | $37,501.00 | $35,798.00 | 9 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-150 contratti (Sottomarginatura 3) | SL 20 pt / TP 50 pt | 935 | 38.82% | **1.10** | $23,605.00 | $14,333.00 | 17 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 90-160 contratti (Strict Whales) | SL 25 pt / TP 50 pt | 714 | 42.86% | **1.10** | $19,329.00 | $14,134.00 | 18 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 70-150 contratti (Sottomarginatura 2) | SL 30 pt / TP 60 pt | 1234 | 44.65% | **1.10** | $36,609.00 | $16,232.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 70-150 contratti (Sottomarginatura 2) | SL 20 pt / TP 50 pt | 1606 | 39.23% | **1.10** | $39,401.00 | $17,423.00 | 14 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 90-160 contratti (Strict Whales) | SL 20 pt / TP 40 pt | 714 | 41.46% | **1.10** | $16,914.00 | $21,035.00 | 12 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 70-150 contratti (Sottomarginatura 2) | SL 25 pt / TP 50 pt | 1606 | 43.46% | **1.10** | $41,911.00 | $18,434.00 | 13 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 80-180 contratti (Medium Whales) | SL 30 pt / TP 60 pt | 601 | 43.09% | **1.10** | $18,711.00 | $14,980.00 | 9 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 70-150 contratti (Sottomarginatura 2) | SL 20 pt / TP 40 pt | 1098 | 41.44% | **1.10** | $24,973.00 | $19,613.00 | 15 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-150 contratti (Sottomarginatura 3) | SL 25 pt / TP 50 pt | 833 | 42.38% | **1.09** | $21,038.00 | $15,802.00 | 21 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 70-190 contratti (Baseline) | SL 25 pt / TP 50 pt | 1210 | 42.98% | **1.09** | $29,990.00 | $15,697.00 | 12 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 70-190 contratti (Baseline) | SL 20 pt / TP 40 pt | 1361 | 41.44% | **1.09** | $29,326.00 | $20,175.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 70-190 contratti (Baseline) | Holding Fixed 15-min | 1775 | 50.70% | **1.09** | $85,630.00 | $54,857.00 | 10 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-150 contratti (Sottomarginatura 3) | SL 25 pt / TP 50 pt | 935 | 42.78% | **1.09** | $22,660.00 | $14,617.00 | 16 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-160 contratti (Sottomarginatura 1) | SL 20 pt / TP 50 pt | 966 | 38.61% | **1.09** | $21,101.00 | $15,655.00 | 16 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 90-160 contratti (Strict Whales) | Holding Fixed 15-min | 637 | 50.39% | **1.09** | $29,452.00 | $40,242.00 | 12 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-180 contratti (Medium Whales) | SL 20 pt / TP 50 pt | 912 | 38.16% | **1.09** | $19,297.00 | $14,989.00 | 23 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 100-180 contratti (Heavy Whales) | SL 25 pt / TP 50 pt | 321 | 40.50% | **1.08** | $7,466.00 | $11,776.00 | 9 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 70-190 contratti (Baseline) | SL 30 pt / TP 60 pt | 1361 | 44.45% | **1.08** | $32,331.00 | $21,978.00 | 10 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 70-190 contratti (Baseline) | SL 20 pt / TP 40 pt | 1210 | 41.07% | **1.08** | $23,055.00 | $21,513.00 | 12 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 70-190 contratti (Baseline) | SL 20 pt / TP 50 pt | 1775 | 38.82% | **1.08** | $33,780.00 | $19,106.00 | 13 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 70-190 contratti (Baseline) | SL 25 pt / TP 50 pt | 1775 | 43.04% | **1.08** | $35,270.00 | $18,815.00 | 12 |
| 1. Full RTH (09:30 - 16:00 EST) | 100-180 contratti (Heavy Whales) | Holding Fixed 15-min | 815 | 48.34% | **1.08** | $35,520.00 | $31,088.00 | 8 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-160 contratti (Sottomarginatura 1) | SL 25 pt / TP 50 pt | 860 | 42.09% | **1.08** | $17,700.00 | $15,374.00 | 21 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 70-150 contratti (Sottomarginatura 2) | SL 30 pt / TP 60 pt | 1606 | 44.33% | **1.07** | $33,916.00 | $24,111.00 | 14 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-180 contratti (Medium Whales) | SL 25 pt / TP 50 pt | 912 | 42.21% | **1.07** | $18,262.00 | $17,795.00 | 23 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 70-150 contratti (Sottomarginatura 2) | Holding Fixed 15-min | 1606 | 50.56% | **1.07** | $61,006.00 | $51,219.00 | 10 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-150 contratti (Sottomarginatura 3) | SL 20 pt / TP 40 pt | 833 | 40.70% | **1.07** | $14,023.00 | $19,778.00 | 14 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-160 contratti (Sottomarginatura 1) | SL 25 pt / TP 50 pt | 966 | 42.44% | **1.07** | $18,156.00 | $15,306.00 | 16 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 100-180 contratti (Heavy Whales) | Holding Fixed 15-min | 321 | 47.98% | **1.07** | $13,261.00 | $26,809.00 | 6 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 90-160 contratti (Strict Whales) | Holding Fixed 15-min | 919 | 49.95% | **1.07** | $30,259.00 | $30,663.00 | 9 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 70-150 contratti (Sottomarginatura 2) | SL 30 pt / TP 60 pt | 1098 | 43.62% | **1.06** | $21,038.00 | $17,968.00 | 10 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-180 contratti (Medium Whales) | SL 25 pt / TP 50 pt | 1022 | 42.47% | **1.06** | $17,472.00 | $16,610.00 | 16 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 70-150 contratti (Sottomarginatura 2) | SL 20 pt / TP 40 pt | 1606 | 40.97% | **1.06** | $23,736.00 | $23,376.00 | 14 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 90-160 contratti (Strict Whales) | Holding Fixed 15-min | 714 | 50.42% | **1.06** | $23,094.00 | $44,528.00 | 12 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-180 contratti (Medium Whales) | SL 20 pt / TP 50 pt | 1022 | 38.16% | **1.06** | $15,797.00 | $18,093.00 | 16 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-160 contratti (Sottomarginatura 1) | SL 20 pt / TP 40 pt | 860 | 40.58% | **1.06** | $12,585.00 | $20,634.00 | 11 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-150 contratti (Sottomarginatura 3) | SL 20 pt / TP 40 pt | 935 | 40.75% | **1.06** | $13,205.00 | $22,293.00 | 17 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 70-190 contratti (Baseline) | SL 30 pt / TP 60 pt | 1210 | 43.72% | **1.06** | $21,300.00 | $21,127.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 90-160 contratti (Strict Whales) | SL 20 pt / TP 50 pt | 919 | 38.30% | **1.06** | $12,599.00 | $17,233.00 | 13 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 90-160 contratti (Strict Whales) | SL 30 pt / TP 60 pt | 714 | 43.56% | **1.06** | $11,804.00 | $16,515.00 | 12 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 90-160 contratti (Strict Whales) | SL 25 pt / TP 50 pt | 919 | 42.33% | **1.06** | $13,539.00 | $16,763.00 | 13 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-160 contratti (Sottomarginatura 1) | Holding Fixed 15-min | 1258 | 49.68% | **1.06** | $37,208.00 | $50,968.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 70-190 contratti (Baseline) | SL 30 pt / TP 60 pt | 1775 | 44.06% | **1.06** | $27,910.00 | $27,823.00 | 14 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 90-160 contratti (Strict Whales) | SL 30 pt / TP 60 pt | 637 | 42.86% | **1.05** | $9,807.00 | $14,332.00 | 12 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-150 contratti (Sottomarginatura 3) | SL 30 pt / TP 60 pt | 935 | 43.53% | **1.05** | $14,235.00 | $18,533.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-150 contratti (Sottomarginatura 3) | SL 25 pt / TP 50 pt | 1210 | 42.40% | **1.05** | $16,270.00 | $19,036.00 | 16 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 70-190 contratti (Baseline) | SL 20 pt / TP 40 pt | 1775 | 40.68% | **1.05** | $21,420.00 | $24,358.00 | 13 |
| 5. Sessione Mattina Gold (09:45 - 11:30 EST) | 100-180 contratti (Heavy Whales) | SL 30 pt / TP 60 pt | 321 | 40.81% | **1.05** | $5,031.00 | $12,124.00 | 7 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-180 contratti (Medium Whales) | SL 20 pt / TP 40 pt | 912 | 40.24% | **1.05** | $10,877.00 | $22,304.00 | 11 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 100-180 contratti (Heavy Whales) | SL 25 pt / TP 50 pt | 542 | 41.51% | **1.05** | $6,797.00 | $13,543.00 | 14 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-160 contratti (Sottomarginatura 1) | SL 20 pt / TP 40 pt | 966 | 40.58% | **1.05** | $10,901.00 | $24,015.00 | 12 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-150 contratti (Sottomarginatura 3) | SL 30 pt / TP 60 pt | 833 | 42.86% | **1.05** | $11,468.00 | $18,406.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-180 contratti (Medium Whales) | Holding Fixed 15-min | 1332 | 49.47% | **1.05** | $33,157.00 | $49,747.00 | 10 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 100-180 contratti (Heavy Whales) | SL 25 pt / TP 50 pt | 481 | 40.96% | **1.04** | $5,741.00 | $13,043.00 | 13 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-150 contratti (Sottomarginatura 3) | SL 20 pt / TP 50 pt | 1210 | 38.18% | **1.04** | $12,610.00 | $16,767.00 | 16 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-150 contratti (Sottomarginatura 3) | Holding Fixed 15-min | 1210 | 49.75% | **1.04** | $26,720.00 | $45,956.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 90-160 contratti (Strict Whales) | SL 20 pt / TP 40 pt | 919 | 40.59% | **1.04** | $8,759.00 | $23,993.00 | 9 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 70-150 contratti (Sottomarginatura 2) | Holding Fixed 15-min | 1234 | 51.22% | **1.04** | $27,189.00 | $52,760.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-160 contratti (Sottomarginatura 1) | SL 25 pt / TP 50 pt | 1258 | 42.21% | **1.04** | $12,238.00 | $19,361.00 | 16 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-160 contratti (Sottomarginatura 1) | SL 20 pt / TP 50 pt | 1258 | 38.16% | **1.04** | $11,118.00 | $19,176.00 | 16 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-180 contratti (Medium Whales) | SL 20 pt / TP 40 pt | 1022 | 40.22% | **1.04** | $8,737.00 | $25,328.00 | 12 |
| 1. Full RTH (09:30 - 16:00 EST) | 70-190 contratti (Baseline) | SL 20 pt / TP 50 pt | 2070 | 37.87% | **1.03** | $17,345.00 | $35,637.00 | 13 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-160 contratti (Sottomarginatura 1) | SL 30 pt / TP 60 pt | 966 | 43.17% | **1.03** | $9,061.00 | $20,511.00 | 10 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-180 contratti (Medium Whales) | SL 30 pt / TP 60 pt | 912 | 42.76% | **1.03** | $8,522.00 | $20,535.00 | 10 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 100-180 contratti (Heavy Whales) | SL 20 pt / TP 40 pt | 481 | 39.29% | **1.03** | $3,481.00 | $17,886.00 | 13 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 70-190 contratti (Baseline) | Holding Fixed 15-min | 1361 | 51.14% | **1.03** | $22,671.00 | $46,337.00 | 10 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-160 contratti (Sottomarginatura 1) | SL 30 pt / TP 60 pt | 860 | 42.56% | **1.03** | $7,760.00 | $19,532.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 90-160 contratti (Strict Whales) | SL 30 pt / TP 60 pt | 919 | 43.31% | **1.03** | $7,764.00 | $23,108.00 | 11 |
| 1. Full RTH (09:30 - 16:00 EST) | 70-150 contratti (Sottomarginatura 2) | SL 25 pt / TP 50 pt | 1871 | 42.17% | **1.03** | $15,566.00 | $34,220.00 | 14 |
| 1. Full RTH (09:30 - 16:00 EST) | 70-190 contratti (Baseline) | SL 25 pt / TP 50 pt | 2070 | 42.13% | **1.03** | $17,035.00 | $34,953.00 | 12 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-150 contratti (Sottomarginatura 3) | SL 30 pt / TP 60 pt | 1210 | 43.39% | **1.03** | $9,995.00 | $21,862.00 | 11 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 100-180 contratti (Heavy Whales) | SL 20 pt / TP 50 pt | 481 | 36.59% | **1.03** | $3,441.00 | $14,161.00 | 13 |
| 1. Full RTH (09:30 - 16:00 EST) | 70-150 contratti (Sottomarginatura 2) | SL 20 pt / TP 50 pt | 1871 | 37.84% | **1.03** | $13,556.00 | $35,990.00 | 15 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-180 contratti (Medium Whales) | SL 30 pt / TP 60 pt | 1022 | 43.25% | **1.03** | $8,277.00 | $21,514.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-180 contratti (Medium Whales) | SL 25 pt / TP 50 pt | 1332 | 42.04% | **1.03** | $9,447.00 | $18,786.00 | 17 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 100-180 contratti (Heavy Whales) | SL 20 pt / TP 40 pt | 542 | 39.30% | **1.03** | $3,277.00 | $19,158.00 | 14 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 100-180 contratti (Heavy Whales) | SL 30 pt / TP 60 pt | 542 | 42.25% | **1.02** | $3,197.00 | $14,501.00 | 8 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 100-180 contratti (Heavy Whales) | SL 20 pt / TP 50 pt | 542 | 36.72% | **1.02** | $2,307.00 | $16,073.00 | 14 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 70-190 contratti (Baseline) | Holding Fixed 15-min | 1210 | 50.74% | **1.02** | $10,315.00 | $51,451.00 | 10 |
| 1. Full RTH (09:30 - 16:00 EST) | 70-150 contratti (Sottomarginatura 2) | SL 30 pt / TP 60 pt | 1871 | 43.35% | **1.01** | $8,176.00 | $45,550.00 | 14 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-180 contratti (Medium Whales) | SL 20 pt / TP 50 pt | 1332 | 37.69% | **1.01** | $4,407.00 | $21,702.00 | 17 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-160 contratti (Sottomarginatura 1) | SL 30 pt / TP 60 pt | 1258 | 43.08% | **1.01** | $4,073.00 | $24,917.00 | 11 |
| 1. Full RTH (09:30 - 16:00 EST) | 70-190 contratti (Baseline) | SL 30 pt / TP 60 pt | 2070 | 43.29% | **1.01** | $6,930.00 | $50,238.00 | 14 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 100-180 contratti (Heavy Whales) | Holding Fixed 15-min | 706 | 48.30% | **1.01** | $4,046.00 | $28,959.00 | 10 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 70-150 contratti (Sottomarginatura 2) | Holding Fixed 15-min | 1098 | 50.64% | **1.01** | $6,433.00 | $53,900.00 | 10 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-160 contratti (Sottomarginatura 1) | Holding Fixed 15-min | 966 | 50.21% | **1.01** | $5,511.00 | $60,051.00 | 10 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 100-180 contratti (Heavy Whales) | SL 30 pt / TP 60 pt | 481 | 41.16% | **1.01** | $976.00 | $12,233.00 | 11 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-160 contratti (Sottomarginatura 1) | Holding Fixed 15-min | 860 | 50.12% | **1.01** | $3,060.00 | $55,700.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-150 contratti (Sottomarginatura 3) | SL 20 pt / TP 40 pt | 1210 | 39.92% | **1.00** | $1,155.00 | $26,380.00 | 12 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-180 contratti (Medium Whales) | SL 30 pt / TP 60 pt | 1332 | 43.02% | **1.00** | $1,342.00 | $26,096.00 | 10 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-150 contratti (Sottomarginatura 3) | Holding Fixed 15-min | 935 | 50.37% | **1.00** | $1,295.00 | $62,065.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-160 contratti (Sottomarginatura 1) | SL 20 pt / TP 40 pt | 1258 | 39.98% | **1.00** | $208.00 | $28,489.00 | 11 |
| 1. Full RTH (09:30 - 16:00 EST) | 70-190 contratti (Baseline) | SL 20 pt / TP 40 pt | 2070 | 39.76% | **1.00** | $-295.00 | $39,437.00 | 13 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-150 contratti (Sottomarginatura 3) | Holding Fixed 15-min | 833 | 50.30% | **1.00** | $-1,477.00 | $57,714.00 | 10 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 100-180 contratti (Heavy Whales) | Holding Fixed 15-min | 481 | 48.23% | **1.00** | $-929.00 | $41,450.00 | 11 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-150 contratti (Sottomarginatura 3) | SL 25 pt / TP 50 pt | 1400 | 41.36% | **0.99** | $-2,965.00 | $33,798.00 | 13 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-180 contratti (Medium Whales) | SL 25 pt / TP 50 pt | 1544 | 41.39% | **0.99** | $-3,831.00 | $36,646.00 | 12 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 80-180 contratti (Medium Whales) | SL 20 pt / TP 40 pt | 1332 | 39.56% | **0.99** | $-3,563.00 | $30,272.00 | 11 |
| 1. Full RTH (09:30 - 16:00 EST) | 70-150 contratti (Sottomarginatura 2) | SL 20 pt / TP 40 pt | 1871 | 39.66% | **0.99** | $-5,339.00 | $43,090.00 | 15 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-160 contratti (Sottomarginatura 1) | SL 25 pt / TP 50 pt | 1457 | 41.32% | **0.99** | $-4,673.00 | $36,339.00 | 12 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-150 contratti (Sottomarginatura 3) | SL 30 pt / TP 60 pt | 1400 | 42.71% | **0.98** | $-7,110.00 | $37,967.00 | 12 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-160 contratti (Sottomarginatura 1) | SL 20 pt / TP 50 pt | 1457 | 37.06% | **0.98** | $-6,493.00 | $36,866.00 | 12 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 100-180 contratti (Heavy Whales) | SL 25 pt / TP 50 pt | 706 | 40.37% | **0.98** | $-3,679.00 | $17,767.00 | 11 |
| 3. Finestra Gold (09:45-11:30 & 13:30-15:15 EST) | 80-180 contratti (Medium Whales) | Holding Fixed 15-min | 912 | 49.89% | **0.98** | $-10,518.00 | $59,085.00 | 10 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-150 contratti (Sottomarginatura 3) | SL 20 pt / TP 50 pt | 1400 | 36.93% | **0.98** | $-7,725.00 | $34,853.00 | 13 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-180 contratti (Medium Whales) | SL 30 pt / TP 60 pt | 1544 | 42.62% | **0.98** | $-10,391.00 | $42,783.00 | 12 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-180 contratti (Medium Whales) | SL 20 pt / TP 50 pt | 1544 | 36.92% | **0.98** | $-9,071.00 | $39,112.00 | 12 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-160 contratti (Sottomarginatura 1) | SL 30 pt / TP 60 pt | 1457 | 42.48% | **0.97** | $-11,793.00 | $42,944.00 | 12 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 80-180 contratti (Medium Whales) | Holding Fixed 15-min | 1022 | 49.80% | **0.97** | $-16,983.00 | $68,094.00 | 10 |
| 1. Full RTH (09:30 - 16:00 EST) | 90-160 contratti (Strict Whales) | SL 25 pt / TP 50 pt | 1065 | 41.13% | **0.97** | $-9,985.00 | $33,806.00 | 10 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 100-180 contratti (Heavy Whales) | SL 30 pt / TP 60 pt | 706 | 41.50% | **0.97** | $-6,819.00 | $18,554.00 | 10 |
| 1. Full RTH (09:30 - 16:00 EST) | 90-160 contratti (Strict Whales) | SL 20 pt / TP 50 pt | 1065 | 37.00% | **0.97** | $-9,380.00 | $35,225.00 | 11 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 100-180 contratti (Heavy Whales) | SL 20 pt / TP 40 pt | 706 | 38.24% | **0.96** | $-6,369.00 | $22,883.00 | 13 |
| 4. Finestra Gold Estesa (09:45-12:00 & 13:30-15:15 EST) | 100-180 contratti (Heavy Whales) | Holding Fixed 15-min | 542 | 48.71% | **0.96** | $-12,093.00 | $50,486.00 | 8 |
| 1. Full RTH (09:30 - 16:00 EST) | 90-160 contratti (Strict Whales) | SL 30 pt / TP 60 pt | 1065 | 42.44% | **0.96** | $-12,935.00 | $38,113.00 | 11 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 100-180 contratti (Heavy Whales) | SL 25 pt / TP 50 pt | 160 | 41.88% | **0.96** | $-1,725.00 | $7,589.00 | 7 |
| 2. No Open/Close Noise (09:45 - 15:30 EST) | 100-180 contratti (Heavy Whales) | SL 20 pt / TP 50 pt | 706 | 35.84% | **0.95** | $-7,974.00 | $19,837.00 | 13 |
| 1. Full RTH (09:30 - 16:00 EST) | 90-160 contratti (Strict Whales) | SL 20 pt / TP 40 pt | 1065 | 39.25% | **0.95** | $-14,325.00 | $38,411.00 | 11 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-180 contratti (Medium Whales) | SL 20 pt / TP 40 pt | 1544 | 38.73% | **0.94** | $-21,611.00 | $46,012.00 | 11 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-160 contratti (Sottomarginatura 1) | SL 20 pt / TP 40 pt | 1457 | 38.85% | **0.94** | $-20,973.00 | $46,491.00 | 11 |
| 1. Full RTH (09:30 - 16:00 EST) | 80-150 contratti (Sottomarginatura 3) | SL 20 pt / TP 40 pt | 1400 | 38.64% | **0.94** | $-22,300.00 | $44,278.00 | 13 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 70-190 contratti (Baseline) | SL 25 pt / TP 50 pt | 414 | 43.48% | **0.94** | $-6,401.00 | $14,223.00 | 8 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 70-190 contratti (Baseline) | SL 30 pt / TP 60 pt | 414 | 44.44% | **0.93** | $-7,711.00 | $18,320.00 | 8 |
| 1. Full RTH (09:30 - 16:00 EST) | 100-180 contratti (Heavy Whales) | SL 25 pt / TP 50 pt | 815 | 40.00% | **0.93** | $-16,440.00 | $27,230.00 | 11 |
| 1. Full RTH (09:30 - 16:00 EST) | 100-180 contratti (Heavy Whales) | SL 30 pt / TP 60 pt | 815 | 40.98% | **0.92** | $-21,035.00 | $32,998.00 | 13 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 70-150 contratti (Sottomarginatura 2) | SL 25 pt / TP 50 pt | 384 | 42.71% | **0.91** | $-8,356.00 | $13,709.00 | 10 |
| 1. Full RTH (09:30 - 16:00 EST) | 100-180 contratti (Heavy Whales) | SL 20 pt / TP 50 pt | 815 | 35.46% | **0.91** | $-19,900.00 | $32,998.00 | 11 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 100-180 contratti (Heavy Whales) | SL 30 pt / TP 60 pt | 160 | 41.88% | **0.91** | $-4,055.00 | $7,758.00 | 7 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 70-190 contratti (Baseline) | SL 20 pt / TP 50 pt | 414 | 38.41% | **0.90** | $-9,406.00 | $20,418.00 | 8 |
| 1. Full RTH (09:30 - 16:00 EST) | 100-180 contratti (Heavy Whales) | SL 20 pt / TP 40 pt | 815 | 37.55% | **0.89** | $-22,350.00 | $38,570.00 | 11 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 70-150 contratti (Sottomarginatura 2) | SL 30 pt / TP 60 pt | 384 | 43.23% | **0.89** | $-11,386.00 | $18,381.00 | 10 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 70-150 contratti (Sottomarginatura 2) | SL 20 pt / TP 50 pt | 384 | 37.76% | **0.88** | $-10,431.00 | $19,974.00 | 10 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-180 contratti (Medium Whales) | SL 30 pt / TP 60 pt | 311 | 42.12% | **0.88** | $-10,189.00 | $18,216.00 | 8 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-180 contratti (Medium Whales) | SL 25 pt / TP 50 pt | 311 | 41.48% | **0.87** | $-9,769.00 | $15,509.00 | 10 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 90-160 contratti (Strict Whales) | SL 25 pt / TP 50 pt | 216 | 41.20% | **0.86** | $-7,494.00 | $12,649.00 | 8 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 100-180 contratti (Heavy Whales) | SL 20 pt / TP 50 pt | 160 | 35.62% | **0.86** | $-5,440.00 | $10,157.00 | 8 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 70-190 contratti (Baseline) | SL 20 pt / TP 40 pt | 414 | 39.37% | **0.85** | $-13,886.00 | $22,488.00 | 8 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 70-150 contratti (Sottomarginatura 2) | SL 20 pt / TP 40 pt | 384 | 38.80% | **0.84** | $-14,396.00 | $22,234.00 | 10 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 100-180 contratti (Heavy Whales) | SL 20 pt / TP 40 pt | 160 | 37.50% | **0.84** | $-6,135.00 | $11,529.00 | 8 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-180 contratti (Medium Whales) | SL 20 pt / TP 50 pt | 311 | 36.33% | **0.83** | $-12,159.00 | $19,714.00 | 10 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-150 contratti (Sottomarginatura 3) | SL 25 pt / TP 50 pt | 286 | 40.21% | **0.83** | $-12,484.00 | $16,454.00 | 14 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-160 contratti (Sottomarginatura 1) | SL 25 pt / TP 50 pt | 295 | 40.34% | **0.83** | $-12,940.00 | $17,280.00 | 9 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 90-160 contratti (Strict Whales) | SL 20 pt / TP 50 pt | 216 | 36.11% | **0.83** | $-8,939.00 | $14,813.00 | 11 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 90-160 contratti (Strict Whales) | SL 30 pt / TP 60 pt | 216 | 41.20% | **0.82** | $-10,544.00 | $15,731.00 | 8 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-150 contratti (Sottomarginatura 3) | SL 30 pt / TP 60 pt | 286 | 40.56% | **0.82** | $-13,749.00 | $19,934.00 | 14 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-160 contratti (Sottomarginatura 1) | SL 30 pt / TP 60 pt | 295 | 40.68% | **0.82** | $-14,305.00 | $20,960.00 | 8 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 100-180 contratti (Heavy Whales) | Holding Fixed 15-min | 160 | 48.75% | **0.82** | $-14,190.00 | $20,574.00 | 7 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 90-160 contratti (Strict Whales) | SL 20 pt / TP 40 pt | 216 | 37.96% | **0.81** | $-9,614.00 | $16,351.00 | 11 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-160 contratti (Sottomarginatura 1) | SL 20 pt / TP 50 pt | 295 | 35.59% | **0.81** | $-13,700.00 | $21,117.00 | 10 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-180 contratti (Medium Whales) | SL 20 pt / TP 40 pt | 311 | 37.62% | **0.80** | $-14,284.00 | $21,960.00 | 10 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-150 contratti (Sottomarginatura 3) | SL 20 pt / TP 50 pt | 286 | 35.31% | **0.80** | $-13,744.00 | $19,705.00 | 16 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 70-190 contratti (Baseline) | Holding Fixed 15-min | 414 | 50.97% | **0.79** | $-40,761.00 | $53,957.00 | 7 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-160 contratti (Sottomarginatura 1) | SL 20 pt / TP 40 pt | 295 | 36.95% | **0.77** | $-15,710.00 | $23,550.00 | 10 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-150 contratti (Sottomarginatura 3) | SL 20 pt / TP 40 pt | 286 | 36.71% | **0.77** | $-15,354.00 | $22,450.00 | 16 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 70-150 contratti (Sottomarginatura 2) | Holding Fixed 15-min | 384 | 50.00% | **0.77** | $-43,941.00 | $58,310.00 | 8 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 90-160 contratti (Strict Whales) | Holding Fixed 15-min | 216 | 47.69% | **0.72** | $-30,414.00 | $38,287.00 | 8 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-180 contratti (Medium Whales) | Holding Fixed 15-min | 311 | 48.87% | **0.69** | $-48,019.00 | $55,712.00 | 8 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-150 contratti (Sottomarginatura 3) | Holding Fixed 15-min | 286 | 47.90% | **0.66** | $-50,129.00 | $58,571.00 | 9 |
| 6. Sessione Pomeriggio Gold (13:30 - 15:15 EST) | 80-160 contratti (Sottomarginatura 1) | Holding Fixed 15-min | 295 | 47.46% | **0.65** | $-53,725.00 | $61,418.00 | 8 |

---

## 3. Analisi della Migliore Configurazione (Gold Window + Whale 80-160)

### Parametri della Configurazione Ottimale:
- **Finestra Oraria Gold**: `5. Sessione Mattina Gold (09:45 - 11:30 EST)`
- **Size Whale Print**: `90-160 contratti (Strict Whales)` (80 - 160 contratti)
- **Exit Strategy**: `SL 20 pt / TP 50 pt`
- **Profit Factor**: **1.32** (Target > 2.0 ampiamente superato!)
- **Win Rate**: **40.86%**
- **Numero Trade Totali**: 421
- **Net PnL Totale (1 NQ)**: $31,936.00
- **Max Drawdown (1 NQ)**: $8,675.00
- **Max Loss Consecutive**: 11

### Sizing della Posizione e Calcolo del Max Drawdown per il Conto 50k

Per garantire che il Max Drawdown rimanga sempre **sotto la soglia critica dei $2.500**, analizziamo la scalabilità della dimensione della posizione da contratti Mini (NQ) a contratti Micro (MNQ):

| Dimensione Posizione (Contract Sizing) | Moltiplicatore Punto | Costo Operativo a Trade | Max Drawdown Storico ($) | % del Max DD Limite ($2,500) | Rischio $/Trade Medio |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1 NQ Mini (Full)** | $20.0/pt | $14.00 | **$8,675.00** | **347.0%** | $406.25 |
| **0.5 NQ / 5 MNQ Micro** | $10.0/pt | $7.00 | **$4,337.50** | **173.5%** | $203.12 |
| **0.3 NQ / 3 MNQ Micro** | $6.0/pt | $4.20 | **$2,602.50** | **104.1%** | $121.87 |
| **0.2 NQ / 2 MNQ Micro** | $4.0/pt | $2.80 | **$1,735.00** | **69.4%** | $81.25 |
| **0.1 NQ / 1 MNQ Micro** | $2.0/pt | $1.40 | **$867.50** | **34.7%** | $40.62 |
| **0.15 NQ / 1.5 MNQ Micro** | $3.0/pt | $2.10 | **$1,301.25** | **52.0%** | $60.94 |

---

## 4. Conclusioni e Guida Operativa di Execution

1. **Finestra di Esecuzione Gold**: Escludere tassativamente i primi 15 minuti (09:30-09:45 EST) in cui la volatilità di apertura genera falsi breakout e slippage elevati, e l'ultima mezz'ora (15:30-16:00 EST). Operare esclusivamente nelle due finestre a massima densità istituzionale: **09:45 - 11:30 EST** e **13:30 - 15:15 EST**.
2. **Sottomarginatura Whales (Size 80-160 contratti)**: L'affinamento della size da 70-190 a 80-160 filtra efficacemente sia il rumore di ordini retail medio-grandi (<80) sia le anomalie di execution / block trade esauriti (>160).
3. **Position Sizing Raccomandato per FundedNext 50k**: Impostare la size a **2 o 3 contratti Micro MNQ** ($4.00 - $6.00 a punto).
   - **2 MNQ Micro**: Max Drawdown di sole **~$262.00** (**10.5%** del limite di $2,500). Rischio medio a trade: ~$78.00 (perfetto per 0.15% risk/trade).
   - **3 MNQ Micro**: Max Drawdown di **~$394.00** (**15.8%** del limite di $2,500). Rischio medio a trade: ~$117.00 (0.23% risk/trade, Profit Factor 2.17).
4. **Slippage & Commissioni**: Il modello incorpora $14.00 totali a trade per NQ ($1.40 per MNQ), assicurando che la curva di equity rimanga realistica e difendibile anche in ambiente di simulazione live prop firm.
