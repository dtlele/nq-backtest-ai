import sys
import os
from pathlib import Path

os.environ['OPENROUTER_MODEL'] = 'moonshotai/kimi-k3'

sys.path.append('C:/Users/Mauro/Documents/nq-backtest-clean')
from src.agents.llm_client import llm_ask

log_content = Path('C:/Users/Mauro/Documents/nq-backtest-clean/output_k3_arch_old.log').read_text(encoding='utf-16')
log_tail = '\n'.join(log_content.splitlines()[-400:])

prompt = f"""Ecco gli ultimi log del nostro nuovo sistema di trading algoritmico (architettura Chief+Compiler basata sui tuoi suggerimenti).
L'agente al comando del Chief è GLM-5.2.
Voglio che tu analizzi questi log come un revisore quantitativo d'élite.

LOGS:
{log_tail}

OBIETTIVO:
- Valuta come l'agente (GLM-5.2) sta ragionando sulla scelta degli Anchor e sui bias (Long/Short).
- Analizza l'interazione tra l'LLM e i filtri scritti in codice (es. PROXIMITY VETO, R:R calculation).
- C'è qualche anomalia o stiamo lavorando in modo istituzionale come previsto?
- Sii CONCISO (bullet points) e severo.
"""

response = llm_ask("Sei l'Architetto Revisore.", prompt, use_cache=False)

out_path = Path('C:/Users/Mauro/Documents/nq-backtest-clean/kimi_log_analysis.md')
out_path.write_text(str(response), encoding='utf-8')
print('Analysis saved to kimi_log_analysis.md')
