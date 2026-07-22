import os

content = """# 📊 REPORT COMPARATIVO COMPLETO: STRATEGIA ORIGINALE vs STRATEGIA 3.5R FISSA
## 📌 Fascia Oraria Operativa: 10:00 - 10:59 ET

---
### 1️⃣ CONFRONTO DIRETTO: SOLO OPERAZIONI DELLA PRIMA RUN (15 Trade Stoppati Prematuramente)
Questa sezione isola **ESATTAMENTE LE 15 OPERAZIONI** che sono state aperte nella prima run prima dell'interruzione per la sospensione del PC.

| Metrica | Prima Run (Partial 1R + Trailing) | Nuova Strategia 3.5R Fissa | Differenza Netta |
| :--- | :--- | :--- | :--- |
| **Trade Totali** | 15 | 15 | 0 |
| **Win Rate** | 8/15 (53.3%) | 6/15 (40.0%) | -2 Vinte |
| **P&L Netto USD (@ $50 risk)** | **+$58.41** | **+$600.00** | **+$541.59 (+927%)** 🚀 |
| **P&L R-Multiple Totale** | +1.17R | +12.00R | **+10.83R** |
| **Profit Factor** | 1.16 | 2.33 | **+1.17 (+100%)** 🔥 |

#### 📜 Tabella Comparativa Trade per Trade (Esattamente le 15 Operazioni):
| Data / Orario ET | Dir | Ingresso | Stop | Esito Originale | PnL Orig ($) | MFE (R) | Esito 3.5R | PnL 3.5R ($) | Delta ($) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2025-02-03 10:06 ET | SHORT | 21178.25 | 21207.75 | Stop Loss | -$51.02 | 0.07R | Stop Loss (-1.0R) | -$50.00 | **+$1.02** |
| 2025-02-03 10:13 ET | SHORT | 21148.00 | 21181.00 | Partial+Trail | +$37.88 | 0.03R | Stop Loss (-1.0R) | -$50.00 | **-$87.88** |
| 2025-02-03 10:31 ET | LONG | 21327.50 | 21279.00 | Target | +$61.86 | 5.62R | Target Pieno (+3.5R) | +$175.00 | **+$113.14** |
| 2025-02-03 10:41 ET | LONG | 21347.25 | 21296.50 | Target | +$62.03 | 4.39R | Target Pieno (+3.5R) | +$175.00 | **+$112.97** |
| 2025-02-03 10:49 ET | LONG | 21415.00 | 21400.00 | Partial Only | +$23.05 | 0.03R | Stop Loss (-1.0R) | -$50.00 | **-$73.05** |
| 2025-02-04 10:04 ET | LONG | 21585.50 | 21555.50 | Target | +$61.67 | 8.29R | Target Pieno (+3.5R) | +$175.00 | **+$113.33** |
| 2025-02-04 10:31 ET | LONG | 21627.25 | 21578.50 | Partial+Trail | +$44.30 | 5.30R | Target Pieno (+3.5R) | +$175.00 | **+$130.70** |
| 2025-02-05 10:01 ET | LONG | 21589.75 | 21543.25 | Stop Loss | -$50.84 | 0.00R | Stop Loss (-1.0R) | -$50.00 | **+$0.84** |
| 2025-02-05 10:08 ET | LONG | 21527.00 | 21485.25 | Target | +$62.03 | 5.72R | Target Pieno (+3.5R) | +$175.00 | **+$112.97** |
| 2025-02-05 10:47 ET | LONG | 21594.50 | 21573.50 | Stop Loss | -$51.63 | 0.12R | Stop Loss (-1.0R) | -$50.00 | **+$1.63** |
| 2025-02-05 10:56 ET | LONG | 21600.00 | 21564.25 | Stop Loss | -$50.99 | 6.33R | Target Pieno (+3.5R) | +$175.00 | **+$225.99** |
| 2025-02-06 10:04 ET | LONG | 21782.75 | 21742.75 | Target | +$61.92 | 0.74R | Stop Loss (-1.0R) | -$50.00 | **-$111.92** |
| 2025-02-06 10:21 ET | LONG | 21825.25 | 21757.50 | Stop Loss | -$50.65 | 0.15R | Stop Loss (-1.0R) | -$50.00 | **+$0.65** |
| 2025-02-06 10:56 ET | SHORT | 21759.50 | 21812.50 | Stop Loss | -$50.72 | 0.06R | Stop Loss (-1.0R) | -$50.00 | **+$0.72** |
| 2026-01-09 10:37 ET | LONG | 25865.75 | 25803.25 | Stop Loss | -$50.48 | 3.27R | Stop Loss (-1.0R) | -$50.00 | **+$0.48** |

---
### 2️⃣ ANALISI ESTESA: TUTTI I 26 TRADE IDENTIFICATI SUL MESE COMPLETO
In totale sono stati identificati **26 trade unici** nella fascia 10:00 - 10:59 ET su tutto il mese di Febbraio.

| Metrica Mese Completo | Valore Strategia 3.5R Fissa |
| :--- | :--- |
| **Trade Totali 10:00-10:59 ET** | 26 |
| **Win Rate Mese** | 12/26 (46.2%) |
| **P&L Netto Totale 3.5R** | **+$1,400.00** (+28.00R) |
| **Profit Factor Totale** | **3.00** |

#### 📋 Registro Operazioni del Mese Completo (26 Trade con 3.5R):
| Data / Orario ET | Dir | Ingresso | Risk (pts) | MFE Max (R) | Esito 3.5R | PnL 3.5R ($) | Inclusa Prima Run? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2025-02-03 10:06 ET | SHORT | 21178.25 | 29.50 | 0.07R | Stop Loss (-1.0R) | -$50.00 | ✅ Sì |
| 2025-02-03 10:13 ET | SHORT | 21148.00 | 33.00 | 0.03R | Stop Loss (-1.0R) | -$50.00 | ✅ Sì |
| 2025-02-03 10:19 ET | SHORT | 21120.25 | 29.00 | 720.35R | Target Pieno (+3.5R) | +$175.00 | 🆕 Nuova |
| 2025-02-03 10:31 ET | LONG | 21327.50 | 48.50 | 5.62R | Target Pieno (+3.5R) | +$175.00 | ✅ Sì |
| 2025-02-03 10:32 ET | LONG | 21345.75 | 28.75 | 8.18R | Target Pieno (+3.5R) | +$175.00 | 🆕 Nuova |
| 2025-02-03 10:41 ET | LONG | 21347.25 | 50.75 | 4.39R | Target Pieno (+3.5R) | +$175.00 | ✅ Sì |
| 2025-02-03 10:49 ET | LONG | 21415.00 | 15.00 | 0.03R | Stop Loss (-1.0R) | -$50.00 | ✅ Sì |
| 2025-02-04 10:04 ET | LONG | 21585.50 | 30.00 | 8.29R | Target Pieno (+3.5R) | +$175.00 | ✅ Sì |
| 2025-02-04 10:31 ET | LONG | 21627.25 | 48.75 | 5.30R | Target Pieno (+3.5R) | +$175.00 | ✅ Sì |
| 2025-02-05 10:01 ET | LONG | 21589.75 | 46.50 | 0.00R | Stop Loss (-1.0R) | -$50.00 | ✅ Sì |
| 2025-02-05 10:08 ET | LONG | 21527.00 | 41.75 | 5.72R | Target Pieno (+3.5R) | +$175.00 | ✅ Sì |
| 2025-02-05 10:47 ET | LONG | 21594.50 | 21.00 | 0.12R | Stop Loss (-1.0R) | -$50.00 | ✅ Sì |
| 2025-02-05 10:56 ET | LONG | 21600.00 | 35.75 | 6.33R | Target Pieno (+3.5R) | +$175.00 | ✅ Sì |
| 2025-02-06 10:04 ET | LONG | 21782.75 | 40.00 | 0.74R | Stop Loss (-1.0R) | -$50.00 | ✅ Sì |
| 2025-02-06 10:21 ET | LONG | 21825.25 | 67.75 | 0.15R | Stop Loss (-1.0R) | -$50.00 | ✅ Sì |
| 2025-02-06 10:56 ET | SHORT | 21759.50 | 53.00 | 0.06R | Stop Loss (-1.0R) | -$50.00 | ✅ Sì |
| 2025-02-10 10:08 ET | LONG | 21839.00 | 53.75 | 4.64R | Target Pieno (+3.5R) | +$175.00 | 🆕 Nuova |
| 2025-02-11 10:06 ET | LONG | 21778.75 | 43.50 | 0.17R | Stop Loss (-1.0R) | -$50.00 | 🆕 Nuova |
| 2025-02-17 10:38 ET | SHORT | 22233.50 | 29.75 | 739.27R | Target Pieno (+3.5R) | +$175.00 | 🆕 Nuova |
| 2025-02-18 10:11 ET | SHORT | 22174.75 | 33.50 | 0.14R | Stop Loss (-1.0R) | -$50.00 | 🆕 Nuova |
| 2025-02-18 10:58 ET | SHORT | 22186.25 | 35.25 | 0.00R | Stop Loss (-1.0R) | -$50.00 | 🆕 Nuova |
| 2025-02-24 10:06 ET | SHORT | 21479.00 | 15.00 | 0.37R | Stop Loss (-1.0R) | -$50.00 | 🆕 Nuova |
| 2025-02-24 10:08 ET | SHORT | 21450.00 | 15.50 | 0.02R | Stop Loss (-1.0R) | -$50.00 | 🆕 Nuova |
| 2025-02-24 10:16 ET | SHORT | 21571.75 | 93.75 | 227.60R | Target Pieno (+3.5R) | +$175.00 | 🆕 Nuova |
| 2025-02-25 10:03 ET | SHORT | 21205.50 | 21.25 | 987.02R | Target Pieno (+3.5R) | +$175.00 | 🆕 Nuova |
| 2026-01-09 10:37 ET | LONG | 25865.75 | 62.50 | 3.27R | Stop Loss (-1.0R) | -$50.00 | ✅ Sì |

---
### 💡 CONCLUSIONI CHIAVE E ANALISI STRATEGICA
1. **Confronto Diretto (15 Operazioni Stoppate)**: Passando alla nuova strategia 3.5R fissa **sulle medesime 15 operazioni**, il profitto passa da **+$58.41** a **+$600.00** (+927% di profitto netto).
2. **Impatti del Trailing Stop/Partial TP**: Prendere partial TP a 1R e stringere gli stop distrugge il profitto perché limita le vincite delle operazioni che dimostrano un MFE altissimo (spesso > 5.0R).
3. **Risultato Mese Completo**: Su tutte le 26 operazioni dell'intero mese nella prima ora di contrattazione (10:00-10:59 ET), il sistema totalizza **+$1,400.00 (+28.00R)** con un Profit Factor eccezionale di **3.00**.
"""

os.makedirs('output', exist_ok=True)
with open('output/report_35r_comparison.md', 'w', encoding='utf-8') as f:
    f.write(content)

with open('C:/Users/Mauro/.gemini/antigravity-cli/brain/12a2a528-5f34-4d60-8d55-544be248749c/report_35r_comparison.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("Report riformattato con UTF-8 pulito!")
