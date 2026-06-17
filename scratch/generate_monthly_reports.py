import json
from pathlib import Path
from collections import defaultdict
import os

def generate_reports():
    trades = []
    trades_log_path = Path('agent_memory/trades_log.jsonl')
    
    if not trades_log_path.exists():
        print("trades_log.jsonl does not exist.")
        return
        
    with open(trades_log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            trades.append(json.loads(line))
            
    print(f"Loaded {len(trades)} trades.")
    
    # Group by month (YYYY-MM)
    by_month = defaultdict(list)
    for t in trades:
        date_str = t.get('date', '')
        if len(date_str) >= 7:
            month = date_str[:7] # e.g. "2025-05"
            by_month[month].append(t)
            
    output_dir = Path('docs/monthly_audits')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    comparison_data = {}
    
    for month in sorted(by_month.keys()):
        month_trades = by_month[month]
        print(f"Generating report for {month} ({len(month_trades)} trades)...")
        
        # Calculate stats
        wins = [t for t in month_trades if t.get('pnl_usd', 0.0) > 0]
        losses = [t for t in month_trades if t.get('pnl_usd', 0.0) < 0]
        breakeven = [t for t in month_trades if t.get('pnl_usd', 0.0) == 0]
        
        net_pnl = sum(t.get('pnl_usd', 0.0) for t in month_trades)
        win_rate = (len(wins) / len(month_trades)) * 100 if month_trades else 0.0
        
        total_win_pnl = sum(t.get('pnl_usd', 0.0) for t in wins)
        total_loss_pnl = sum(t.get('pnl_usd', 0.0) for t in losses)
        
        avg_win = total_win_pnl / len(wins) if wins else 0.0
        avg_loss = total_loss_pnl / len(losses) if losses else 0.0
        profit_factor = abs(total_win_pnl / total_loss_pnl) if total_loss_pnl != 0 else float('inf')
        rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0
        
        comparison_data[month] = {
            'trades': len(month_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'net_pnl': net_pnl,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'rr_ratio': rr_ratio
        }
        
        # Generate Markdown content for the month
        md = []
        md.append(f"# 📅 Report Audit Mensile — {month}")
        md.append(f"\nGenerato in data {datetime_now_str()}")
        md.append("\n## 📊 Statistiche Generali")
        md.append("| Metrica | Valore |")
        md.append("| :--- | :--- |")
        md.append(f"| **Trade Totali** | {len(month_trades)} |")
        md.append(f"| **Vittorie (Wins)** | {len(wins)} ({win_rate:.1f}%) |")
        md.append(f"| **Perdite (Losses)** | {len(losses)} ({((len(losses)/len(month_trades))*100):.1f}%) |")
        md.append(f"| **PnL Netto** | **${net_pnl:.2f}** |")
        md.append(f"| **Profit Factor** | **{profit_factor:.2f}** |")
        md.append(f"| **Average Win** | **${avg_win:.2f}** |")
        md.append(f"| **Average Loss** | **${avg_loss:.2f}** |")
        md.append(f"| **Rapporto Rischio/Rendimento (Avg Win/Avg Loss)** | **{rr_ratio:.2f}** |")
        
        # Performance by Direction
        directions = defaultdict(list)
        for t in month_trades:
            directions[t.get('direction', 'unknown')].append(t)
            
        md.append("\n## ↕️ Performance per Direzione")
        md.append("| Direzione | Trade | Win Rate % | PnL Netto | PnL Medio |")
        md.append("| :--- | :---: | :---: | :---: | :---: |")
        for d in sorted(directions.keys()):
            d_trades = directions[d]
            d_wins = [t for t in d_trades if t.get('pnl_usd', 0.0) > 0]
            d_wr = (len(d_wins) / len(d_trades)) * 100
            d_pnl = sum(t.get('pnl_usd', 0.0) for t in d_trades)
            d_avg = d_pnl / len(d_trades)
            md.append(f"| **{d.upper()}** | {len(d_trades)} | {d_wr:.1f}% | ${d_pnl:.2f} | ${d_avg:.2f} |")
            
        # Stop Loss distance correlation
        def get_stop_distance(trade):
            entry = trade.get('entry')
            stop = trade.get('stop')
            if entry and stop:
                return abs(entry - stop)
            return 0
            
        stop_bins = [
            ("≤ 20 pts", lambda dist: dist <= 20),
            ("20 - 30 pts", lambda dist: 20 < dist <= 30),
            ("30 - 40 pts", lambda dist: 30 < dist <= 40),
            ("40 - 50 pts", lambda dist: 40 < dist <= 50),
            ("> 50 pts", lambda dist: dist > 50)
        ]
        
        md.append("\n## 🛑 Correlazione Distanza Stop Loss")
        md.append("| Distanza Stop Loss | Trade | Win Rate % | PnL Netto | PnL Medio |")
        md.append("| :--- | :---: | :---: | :---: | :---: |")
        for bin_name, bin_fn in stop_bins:
            bin_trades = [t for t in month_trades if bin_fn(get_stop_distance(t))]
            if not bin_trades: continue
            bin_wins = [t for t in bin_trades if t.get('pnl_usd', 0.0) > 0]
            bin_wr = (len(bin_wins) / len(bin_trades)) * 100
            bin_pnl = sum(t.get('pnl_usd', 0.0) for t in bin_trades)
            bin_avg = bin_pnl / len(bin_trades)
            md.append(f"| **{bin_name}** | {len(bin_trades)} | {bin_wr:.1f}% | ${bin_pnl:.2f} | ${bin_avg:.2f} |")
            
        # Exit reasons
        exit_reasons = defaultdict(list)
        for t in month_trades:
            raw_reason = t.get('exit_reason', 'unknown')
            if raw_reason.startswith('early'):
                reason = 'early_exit'
            elif raw_reason == 'stop':
                reason = 'stop_loss'
            elif raw_reason == 'target':
                reason = 'target_hit'
            elif raw_reason == 'trailing_stop':
                reason = 'trailing_stop'
            else:
                reason = raw_reason
            exit_reasons[reason].append(t)
            
        md.append("\n## 🚪 Performance per Tipo di Uscita")
        md.append("| Motivo Uscita | Trade | PnL Netto | PnL Medio |")
        md.append("| :--- | :---: | :---: | :---: |")
        for r in sorted(exit_reasons.keys()):
            r_trades = exit_reasons[r]
            r_pnl = sum(t.get('pnl_usd', 0.0) for t in r_trades)
            r_avg = r_pnl / len(r_trades)
            md.append(f"| **{r}** | {len(r_trades)} | ${r_pnl:.2f} | ${r_avg:.2f} |")
            
        # Hourly performance (converted to ET)
        def get_hour_et(trade):
            time_str = trade.get('entry_time', '')
            if not time_str:
                return "Unknown"
            try:
                from datetime import datetime
                import pytz
                if time_str.endswith('Z'):
                    time_str = time_str[:-1] + '+00:00'
                dt_utc = datetime.fromisoformat(time_str)
                if dt_utc.tzinfo is None:
                    dt_utc = dt_utc.replace(tzinfo=pytz.UTC)
                dt_et = dt_utc.astimezone(pytz.timezone('America/New_York'))
                return dt_et.strftime('%H')
            except Exception:
                return "Unknown"
                
        def get_time_et(time_str):
            if not time_str:
                return "N/A"
            try:
                from datetime import datetime
                import pytz
                if time_str.endswith('Z'):
                    time_str = time_str[:-1] + '+00:00'
                dt_utc = datetime.fromisoformat(time_str)
                if dt_utc.tzinfo is None:
                    dt_utc = dt_utc.replace(tzinfo=pytz.UTC)
                dt_et = dt_utc.astimezone(pytz.timezone('America/New_York'))
                return dt_et.strftime('%H:%M')
            except Exception:
                return "N/A"
            
        hours = defaultdict(list)
        for t in month_trades:
            hours[get_hour_et(t)].append(t)
            
        md.append("\n## ⏳ Performance per Orario (ET)")
        md.append("| Ora (ET) | Trade | Win Rate % | PnL Netto | PnL Medio |")
        md.append("| :--- | :---: | :---: | :---: | :---: |")
        for h in sorted(hours.keys()):
            h_trades = hours[h]
            h_wins = [t for t in h_trades if t.get('pnl_usd', 0.0) > 0]
            h_wr = (len(h_wins) / len(h_trades)) * 100
            h_pnl = sum(t.get('pnl_usd', 0.0) for t in h_trades)
            h_avg = h_pnl / len(h_trades)
            md.append(f"| **{h}:00** | {len(h_trades)} | {h_wr:.1f}% | ${h_pnl:.2f} | ${h_avg:.2f} |")
            
        # Detailed trade logs
        md.append("\n## 📝 Registro dei Trade Dettagliato")
        md.append("| Data | Ora (ET) | Tipo | Dir | Entry | Exit | PnL ($) | Motivo | Conf | Setup |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :--- |")
        for t in sorted(month_trades, key=lambda x: x.get('entry_time', '')):
            t_time = t.get('entry_time', '')
            t_time_et = get_time_et(t_time)
            pnl_val = t.get('pnl_usd', 0.0)
            pnl_str = f"**${pnl_val:.2f}**" if pnl_val >= 0 else f"<span style='color:red;'>-${abs(pnl_val):.2f}</span>"
            md.append(f"| {t.get('date')} | {t_time_et} | {t.get('contracts')}x | {t.get('direction')} | {t.get('entry')} | {t.get('exit_price')} | {pnl_str} | {t.get('exit_reason')} | {t.get('final_confidence')}% | {t.get('setup_type')} |")
            
        # Write file
        filename = output_dir / f"monthly_audit_{month.replace('-', '_')}.md"
        filename.write_text("\n".join(md), encoding='utf-8')
        print(f"Saved {filename}")

    # Generate side-by-side comparison summary
    comp = []
    comp.append("# 📊 Sommario Confronti Mensili")
    comp.append("\nQuesto file contiene il riepilogo e il confronto delle performance mensili della strategia multi-agente Fabio & Andrea.")
    comp.append("\n## 📈 Confronto Mensile Side-by-Side")
    comp.append("| Mese | Trade | V / P | Win Rate % | PnL Netto | Profit Factor | Avg Win | Avg Loss | R/R Medio |")
    comp.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    total_trades_all = 0
    total_pnl_all = 0.0
    
    for month in sorted(comparison_data.keys()):
        data = comparison_data[month]
        total_trades_all += data['trades']
        total_pnl_all += data['net_pnl']
        comp.append(
            f"| **{month}** | {data['trades']} | {data['wins']}W / {data['losses']}L | {data['win_rate']:.1f}% | "
            f"**${data['net_pnl']:.2f}** | {data['profit_factor']:.2f} | ${data['avg_win']:.2f} | "
            f"${data['avg_loss']:.2f} | {data['rr_ratio']:.2f} |"
        )
        
    comp.append("\n## 🏆 Statistiche Totali Progetto")
    comp.append(f"* **Mesi Totali**: {len(comparison_data)}")
    comp.append(f"* **Trade Totali**: {total_trades_all}")
    comp.append(f"* **PnL Complessivo**: **${total_pnl_all:.2f}**")
    
    comp_file = output_dir / "monthly_comparison_summary.md"
    comp_file.write_text("\n".join(comp), encoding='utf-8')
    print(f"Saved {comp_file}")

def datetime_now_str():
    from datetime import datetime
    return datetime.now().strftime('%d/%m/%Y %H:%M:%S')

if __name__ == '__main__':
    generate_reports()
