import json
import os

# FINAL AUDIT SOURCE
target_file = r'c:\Users\Mauro\Documents\nq-backtest\agent_memory\sept_2025_final_audit.jsonl'

unique_trades = []
if os.path.exists(target_file):
    with open(target_file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                unique_trades.append(json.loads(line))
            except:
                continue

unique_trades.sort(key=lambda x: x['entry_time'])

total_trades = len(unique_trades)
wins = [t for t in unique_trades if t['pnl_ticks'] > 0]
losses = [t for t in unique_trades if t['pnl_ticks'] <= 0]

total_pnl = sum(t['pnl_ticks'] for t in unique_trades)
win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0

gross_profit = sum(t['pnl_ticks'] for t in wins)
gross_loss = abs(sum(t['pnl_ticks'] for t in losses))
profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

print(f"\n" + "="*60)
print(f"   REPORT FINALE SETTEMBRE 2025 - AUDIT ISTITUZIONALE NQ")
print("="*60)
print(f"Setup Operativi (AAA): {total_trades}")
print(f"Vittorie: {len(wins)} | Perdite: {len(losses)}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Profit Factor: {profit_factor:.2f}")
print(f"PnL Netto: {total_pnl:.2f} Ticks (${total_pnl*5:,.2f} / contratto)")
print("-" * 60)

# Generate Markdown Report
md_report = [
    "# Audit Istituzionale NQ - Settembre 2025",
    "",
    "## Riepilogo Performance",
    f"- **Win Rate:** {win_rate:.2f}%",
    f"- **Profit Factor:** {profit_factor:.2f}",
    f"- **PnL Totale:** {total_pnl:.2f} Ticks",
    f"- **Totale Trade:** {total_trades}",
    "",
    "## Registro Operativo Consolidato",
    "| Data | Ora (ET) | Direzione | Setup | PnL (Ticks) | Esito |",
    "| :--- | :--- | :--- | :--- | :--- | :--- |"
]

for t in unique_trades:
    try:
        time_part = t['entry_time'].split('T')[1][:5]
        hour = int(time_part.split(':')[0]) - 4
        et_time = f"{hour:02d}:{time_part.split(':')[1]}"
    except:
        et_time = t['entry_time']
        
    outcome = "✅ WIN" if t['pnl_ticks'] > 0 else "❌ LOSS"
    line = f"| {t['date']} | {et_time} | {t['direction'].upper()} | {t['setup_type'].upper()} | {t['pnl_ticks']:.2f} | {outcome} |"
    md_report.append(line)

report_path = "agent_memory/sept_2025_full_audit.md"
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_report))

print(f"Report Markdown aggiornato: {report_path}")
print("="*60 + "\n")
