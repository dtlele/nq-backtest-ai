import sys
import collections

log_file = 'output/run_3days.log'
setups = collections.defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0})
current_setup = "unknown"
open_trades = {}
trade_id = 0

try:
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if 'setup=' in line:
                parts = line.split()
                for p in parts:
                    if p.startswith('setup='):
                        current_setup = p.split('=')[1]
            if '[TRADE OPEN]' in line:
                trade_id += 1
                open_trades[trade_id] = current_setup
                setups[current_setup]['trades'] += 1
            if 'Stop loss hit' in line:
                if len(open_trades) > 0:
                    last_id = max(open_trades.keys())
                    st = open_trades.pop(last_id)
                    setups[st]['losses'] += 1
            if 'Target hit' in line or 'PARTIAL TP' in line:
                if len(open_trades) > 0:
                    last_id = max(open_trades.keys())
                    st = open_trades[last_id]
                    if 'PARTIAL TP' in line:
                        setups[st]['wins'] += 1
                    else:
                        setups[st]['wins'] += 1
                        open_trades.pop(last_id)

    print('=== SETUP AUDIT ===')
    for s, data in setups.items():
        print(f"Setup: {s.upper():<15} | Trades: {data['trades']:<3} | Wins: {data['wins']:<3} | Losses: {data['losses']:<3} | Win Rate: {data['wins']/(data['wins']+data['losses'])*100 if data['wins']+data['losses']>0 else 0:.1f}%")
except Exception as e:
    print('Error:', e)
