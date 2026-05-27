import json
import os

trades_file = 'agent_memory/trades_log.jsonl'
stats = {
    'total_trades': 0,
    'pnl_usd': 0.0,
    'pnl_ticks': 0.0,
    'wins': 0,
    'losses': 0,
    'setups': {}
}

if os.path.exists(trades_file):
    with open(trades_file, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data['date'].startswith('2025-10'):
                    stats['total_trades'] += 1
                    stats['pnl_usd'] += data['pnl_usd']
                    stats['pnl_ticks'] += data['pnl_ticks']
                    
                    if data['pnl_usd'] > 0:
                        stats['wins'] += 1
                    else:
                        stats['losses'] += 1
                    
                    setup = data.get('setup_type', 'unknown')
                    if setup not in stats['setups']:
                        stats['setups'][setup] = {'trades': 0, 'pnl': 0.0}
                    stats['setups'][setup]['trades'] += 1
                    stats['setups'][setup]['pnl'] += data['pnl_usd']
            except:
                continue

print(json.dumps(stats, indent=2))
