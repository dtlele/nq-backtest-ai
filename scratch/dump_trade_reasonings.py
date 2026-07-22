import json
import textwrap

log_file = r'C:\Users\Mauro\Documents\nq-backtest-clean\agent_memory\reasoning_log.jsonl'
output_file = r'C:\Users\Mauro\Documents\nq-backtest-clean\output\trade_reasonings_dettagliati.md'

with open(log_file, 'r', encoding='utf-8') as f, open(output_file, 'w', encoding='utf-8') as out:
    out.write('# Dettaglio Ragionamenti per Singolo Trade Aperto\n\n')
    out.write('Questo file mostra **esattamente** cosa ha ragionato il sistema per ogni trade che è stato **approvato e aperto** nell\'ultima run.\n\n---\n')
    
    trade_count = 0
    for line in f:
        if not line.strip(): continue
        try:
            data = json.loads(line)
        except:
            continue
            
        if data.get('decision') == 'trade':
            trade_count += 1
            out.write(f'## Trade {trade_count} | Data: {data.get("date")} | Ora: {data.get("bar_time_et")} ET\n')
            
            direction = str(data.get("trade_direction")).upper()
            out.write(f'**Direzione**: {direction} | **Entry**: {data.get("trade_entry")} | **Stop**: {data.get("trade_stop")} | **Target**: {data.get("trade_target")}\n')
            out.write(f'**Confidence Finale**: {data.get("final_confidence")}\n\n')
            
            roadmap = data.get('daily_roadmap', {})
            if isinstance(roadmap, dict) and roadmap.get('context_analysis'):
                out.write('### 1. Agente Roadmap (Pre-Market Context)\n')
                out.write(f'> {roadmap.get("context_analysis")[:600]}...\n\n')
                
            out.write('### 2. Agente Macro & Regime\n')
            macro = data.get('macro_regime', {})
            if isinstance(macro, dict):
                out.write(f'- **Regime**: {macro.get("regime")}\n')
                out.write(f'- **Trigger**: {macro.get("trigger")}\n')
            out.write(f'- **Day Profile (AMT)**: {data.get("amt_day_profile")}\n\n')
            
            out.write('### 3. Agente Narrativa (Market Narrative)\n')
            narrative = data.get('market_narrative', 'N/D')
            out.write(f'> {narrative}\n\n')
            
            out.write('### 4. Agente Fabio (Sintesi dei 4 Esperti)\n')
            fabio = data.get('fabio_reasoning', 'N/D')
            out.write(f'> {fabio}\n\n')
            
            out.write('### 5. Risk Manager\n')
            out.write('Il trade ha **superato** i controlli del Risk Manager (nessun VETO applicato) ed è stato approvato per l\'esecuzione.\n\n')
            
            out.write('---\n\n')
            
print(f'Report generato in: {output_file}')
