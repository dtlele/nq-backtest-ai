import json

wins = []
losses = []

with open('agent_memory/trades_log.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        try:
            t = json.loads(line)
            if t.get('logged_at', '') < "2026-05-30T07:32:00":
                continue
                
            pnl = float(t.get('pnl_usd', 0))
            if pnl > 10:
                wins.append(t)
            elif pnl < -10:
                losses.append(t)
        except:
            pass

with open('scratch/march_reasonings.md', 'w', encoding='utf-8') as out:
    out.write("# Analisi Ragionamenti - Marzo 2025 (Run 0.1% Risk)\n\n")
    
    out.write("## TRADES IN PROFITTO (WINS)\n\n")
    for w in wins:
        out.write(f"### {w['date']} {w['entry_time'][11:16]} | {w['direction'].upper()} | +${w['pnl_usd']}\n")
        out.write(f"**Fabio:** {w.get('fabio_reasoning', '')}\n\n")
        out.write(f"**Andrea:** {w.get('andrea_reasoning', '')}\n\n")
        out.write("---\n\n")
        
    out.write("## TRADES IN PERDITA (LOSSES)\n\n")
    for l in losses:
        out.write(f"### {l['date']} {l['entry_time'][11:16]} | {l['direction'].upper()} | -${abs(l['pnl_usd'])}\n")
        out.write(f"**Fabio:** {l.get('fabio_reasoning', '')}\n\n")
        out.write(f"**Andrea:** {l.get('andrea_reasoning', '')}\n\n")
        out.write("---\n\n")

print(f"Estratti {len(wins)} wins e {len(losses)} losses.")
