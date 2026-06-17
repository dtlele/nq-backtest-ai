import json

def inspect_active_setups():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    
    setups = {}
    with open(trades_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                t = json.loads(line)
                setup = t.get('setup_type', 'unknown')
                pnl = t.get('pnl_usd', 0.0)
                direction = t.get('direction', 'unknown')
                
                if setup not in setups:
                    setups[setup] = {'count': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0, 'directions': set()}
                
                setups[setup]['count'] += 1
                setups[setup]['pnl'] += pnl
                setups[setup]['directions'].add(direction)
                if pnl > 0:
                    setups[setup]['wins'] += 1
                else:
                    setups[setup]['losses'] += 1
            except Exception as e:
                print(f"Error: {e}")
                
    print("=== Setups in active trades_log.jsonl ===")
    for setup, stats in setups.items():
        wr = stats['wins'] / stats['count'] * 100
        print(f"Setup: {setup:<25} | Count: {stats['count']:<3} | Wins: {stats['wins']:<3} | Losses: {stats['losses']:<3} | WR: {wr:>5.1f}% | PnL: {stats['pnl']:>+8.2f} | Directions: {list(stats['directions'])}")

if __name__ == '__main__':
    inspect_active_setups()
