import json
import collections

log_file = r'C:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl'
output_file = r'C:\Users\Mauro\Documents\nq-backtest\scratch\trading_audit.md'

stats = {
    'total': 0,
    'decisions': collections.Counter(),
    'fabio_directions': collections.Counter(),
    'no_trade_reasons': collections.Counter(),
    'vetoes': 0,
    'veto_snippets': [],
    'trade_snippets': []
}

try:
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
                
            stats['total'] += 1
            decision = data.get('decision')
            stats['decisions'][decision] += 1
            stats['fabio_directions'][data.get('fabio_direction')] += 1
            
            if decision == 'no_trade':
                stats['no_trade_reasons'][data.get('no_trade_reason')] += 1
                
            reasoning = data.get('fabio_reasoning', '')
            if isinstance(reasoning, str) and 'VETO' in reasoning.upper():
                stats['vetoes'] += 1
                if len(stats['veto_snippets']) < 3:
                    stats['veto_snippets'].append(reasoning)
            
            if decision == 'trade':
                if len(stats['trade_snippets']) < 3:
                    stats['trade_snippets'].append(reasoning)
except Exception as e:
    print(f"Error reading {log_file}: {e}")

with open(output_file, 'w', encoding='utf-8') as out:
    out.write("# Audit dei Ragionamenti di Trading (Run Eseguite)\n\n")
    out.write(f"**Totale candidati analizzati:** {stats['total']}\n\n")
    
    out.write("## 1. Decisioni Finali\n")
    for k, v in stats['decisions'].most_common():
        out.write(f"- **{k}**: {v}\n")
    
    out.write("\n## 2. Direzione proposta da Fabio\n")
    for k, v in stats['fabio_directions'].most_common():
        out.write(f"- **{k}**: {v}\n")
        
    out.write("\n## 3. Motivi di No-Trade più frequenti\n")
    for k, v in stats['no_trade_reasons'].most_common(10):
        out.write(f"- `{k}`: {v} volte\n")
        
    out.write(f"\n## 4. Veti del Risk Manager (Totale veti espliciti: {stats['vetoes']})\n")
    out.write("Il Risk Manager è intervenuto pesantemente per bloccare i trade. Ecco alcuni esempi di ragionamento di veto:\n\n")
    for i, snip in enumerate(stats['veto_snippets']):
        out.write(f"### Esempio Veto {i+1}:\n> {snip[:800]}...\n\n")
        
    out.write("\n## 5. Ragionamenti sui Trade Approvati\n")
    if stats['trade_snippets']:
        for i, snip in enumerate(stats['trade_snippets']):
            out.write(f"### Esempio Trade Approvato {i+1}:\n> {str(snip)[:800]}...\n\n")
    else:
        out.write("Nessun trade approvato trovato nel log recente.\n")
        
print(f"Audit generato in {output_file}")
