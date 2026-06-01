import json
import os

# Barra attuale
lines = open('agent_memory/reasoning_log.jsonl', encoding='utf-8').readlines()
last = json.loads(lines[-1])
print('=== STATO ATTUALE ===')
print(f"Giornata: {last['date']} | Barra: {last['bar_time_et']} | Dir: {last['fabio_direction']} | Conf: {last['fabio_confidence']}")
print()

# Segnali forti nella run attuale per Mar 10
current_signals = [json.loads(l) for l in lines
                   if json.loads(l).get('date') == '2025-03-10'
                   and json.loads(l).get('fabio_confidence', 0) >= 70
                   and json.loads(l).get('fabio_direction') not in ['none', 'light_skip', 'prefiltered']]
print(f'=== RUN ATTUALE - Segnali >= 70 conf il 10 Marzo: {len(current_signals)} ===')
for t in current_signals:
    print(f"  {t['bar_time_et']} | dir={t['fabio_direction']} conf={t['fabio_confidence']} | entry={t.get('fabio_entry')} stop={t.get('fabio_stop')} target={t.get('fabio_target')}")
    reasoning = t.get('fabio_reasoning', '')
    print(f"  Ragionamento: {reasoning[:180]}")
    print()

# Confronto con versione profittevole (backup)
backup = 'agent_memory/reasoning_log_backup.jsonl'
if os.path.exists(backup):
    backup_lines = open(backup, encoding='utf-8').readlines()
    trades_orig = [json.loads(l) for l in backup_lines
                   if json.loads(l).get('date') == '2025-03-10'
                   and json.loads(l).get('decision') == 'trade']
    print(f'=== RUN PROFITTEVOLE (backup) - Trade eseguiti il 10 Marzo: {len(trades_orig)} ===')
    for t in trades_orig:
        print(f"  {t['bar_time_et']} | dir={t['fabio_direction']} conf={t['fabio_confidence']} | entry={t.get('fabio_entry')} stop={t.get('fabio_stop')} target={t.get('fabio_target')}")
        reasoning = t.get('fabio_reasoning', '')
        print(f"  Ragionamento: {reasoning[:180]}")
        print()
else:
    print('Backup reasoning_log non trovato in agent_memory/reasoning_log_backup.jsonl')
