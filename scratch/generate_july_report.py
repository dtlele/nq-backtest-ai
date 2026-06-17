import json
from collections import defaultdict
from pathlib import Path

def main():
    trades = []
    # Load all July trades
    with open('agent_memory/trades_log.jsonl', 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            t = json.loads(line)
            if t.get('date', '').startswith('2025-07'):
                trades.append(t)
                
    # Sort chronologically
    trades.sort(key=lambda x: x.get('entry_time', ''))
    
    total_trades = len(trades)
    if total_trades == 0:
        print("No July trades found!")
        return
        
    wins = [t for t in trades if t.get('pnl_usd', 0.0) > 0]
    losses = [t for t in trades if t.get('pnl_usd', 0.0) <= 0]
    
    gross_profit = sum(t.get('pnl_usd', 0.0) for t in wins)
    gross_loss = abs(sum(t.get('pnl_usd', 0.0) for t in losses))
    net_pnl = gross_profit - gross_loss
    
    win_rate = (len(wins) / total_trades) * 100 if total_trades > 0 else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    avg_win = gross_profit / len(wins) if len(wins) > 0 else 0.0
    avg_loss = -gross_loss / len(losses) if len(losses) > 0 else 0.0
    avg_rr = avg_win / abs(avg_loss) if abs(avg_loss) > 0 else 0.0
    
    # Group by day
    daily_stats = defaultdict(lambda: {'trades': [], 'pnl': 0.0, 'wins': 0, 'losses': 0})
    for t in trades:
        date = t.get('date')
        daily_stats[date]['trades'].append(t)
        pnl = t.get('pnl_usd', 0.0)
        daily_stats[date]['pnl'] += pnl
        if pnl > 0:
            daily_stats[date]['wins'] += 1
        else:
            daily_stats[date]['losses'] += 1

    md = []
    md.append("# 📅 Report Audit Mensile — Luglio 2025 (1-16)\n")
    md.append("Rapporto provvisorio delle performance per la prima metà di Luglio 2025.\n")
    
    md.append("## 📊 Statistiche Generali")
    md.append("| Metrica | Valore |")
    md.append("| :--- | :--- |")
    md.append(f"| **Trade Totali** | {total_trades} |")
    md.append(f"| **Vittorie (Wins)** | {len(wins)} ({win_rate:.1f}%) |")
    md.append(f"| **Perdite (Losses)** | {len(losses)} ({100 - win_rate:.1f}%) |")
    md.append(f"| **PnL Netto** | **${net_pnl:+.2f}** |")
    md.append(f"| **Profit Factor** | **{profit_factor:.2f}** |")
    md.append(f"| **Average Win** | **${avg_win:.2f}** |")
    md.append(f"| **Average Loss** | **${avg_loss:.2f}** |")
    md.append(f"| **Rapporto R/R Medio (Avg Win/Avg Loss)** | **{avg_rr:.2f}** |")
    md.append("")
    
    md.append("## 📅 Dettaglio Giornaliero e Trade Log")
    
    for date in sorted(daily_stats.keys()):
        stats = daily_stats[date]
        pnl_str = f"+${stats['pnl']:.2f}" if stats['pnl'] >= 0 else f"-${abs(stats['pnl']):.2f}"
        md.append(f"### {date} | Daily PnL: {pnl_str} | W/L: {stats['wins']}/{stats['losses']}\n")
        
        for t in stats['trades']:
            p = t.get('pnl_usd', 0.0)
            p_str = f"+${p:.2f}" if p >= 0 else f"-${abs(p):.2f}"
            icon = "✅" if p > 0 else "❌"
            # Format time from ISO
            entry_time = t.get('entry_time', '')
            if 'T' in entry_time:
                # e.g. 2025-07-02T13:46:00+00:00 -> 13:46
                entry_time = entry_time.split('T')[1][:5]
            else:
                entry_time = '??:??'
                
            md.append(f"**{icon} {entry_time} | {t.get('direction', '').upper()} @ {t.get('entry')}** ➔ Exit: {t.get('exit_price')} ({t.get('exit_reason')}) | **PnL: {p_str}**")
            md.append(f"> **Fabio's Reasoning:** *{t.get('fabio_reasoning', 'N/A')}*")
            
            andrea_reason = t.get('andrea_reasoning')
            if andrea_reason:
                md.append(f"> **Andrea's Reasoning:** *{andrea_reason}*")
            md.append("")
        md.append("\n---\n")
        
    # Write to files
    out_dir = Path('output/reports')
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = out_dir / 'july_report_1_16.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(md))
        
    print(f"Report saved to {report_file}")
    
    # Save a copy as a brain artifact if possible
    artifact_path = Path(r'C:\Users\Mauro\.gemini\antigravity\brain\e86b7458-2bf7-4121-9908-1844e8f5d6dd\july_report_1_16.md')
    with open(artifact_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md))
    print(f"Artifact saved to {artifact_path}")

if __name__ == '__main__':
    main()
