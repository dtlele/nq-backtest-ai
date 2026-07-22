import sys
import collections

log_file = 'output/run_3days.log'
conf_stats = collections.defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0})
current_conf = "unknown"
open_trades = {}
trade_id = 0

try:
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if 'conf=' in line and 'setup=' in line:
                parts = line.split()
                for p in parts:
                    if p.startswith('conf='):
                        current_conf = p.split('=')[1]
            if '[TRADE OPEN]' in line:
                trade_id += 1
                open_trades[trade_id] = current_conf
                conf_stats[current_conf]['trades'] += 1
            if 'Stop loss hit' in line:
                if len(open_trades) > 0:
                    last_id = max(open_trades.keys())
                    st = open_trades.pop(last_id)
                    conf_stats[st]['losses'] += 1
            if 'Target hit' in line or 'PARTIAL TP' in line:
                if len(open_trades) > 0:
                    last_id = max(open_trades.keys())
                    st = open_trades[last_id]
                    if 'PARTIAL TP' in line:
                        conf_stats[st]['wins'] += 1
                    else:
                        conf_stats[st]['wins'] += 1
                        open_trades.pop(last_id)

    print('=== CONFIDENCE AUDIT ===')
    for c, data in sorted(conf_stats.items(), reverse=True): # highest conf first
        wr = data['wins'] / (data['wins'] + data['losses']) * 100 if (data['wins'] + data['losses']) > 0 else 0
        print(f"Confidence: {c + '%':<5} | Trades: {data['trades']:<3} | Wins: {data['wins']:<3} | Losses: {data['losses']:<3} | Win Rate: {wr:.1f}%")
except Exception as e:
    print('Error:', e)
