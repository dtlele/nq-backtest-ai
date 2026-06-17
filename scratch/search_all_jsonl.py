import os
import json

def search_all_jsonl_deep():
    root_dir = r'c:\Users\Mauro\Documents\nq-backtest'
    
    for dirpath, _, filenames in os.walk(root_dir):
        if any(x in dirpath for x in ['.git', '__pycache__', '.pytest_cache', 'dashboard', 'node_modules']):
            continue
            
        for filename in filenames:
            if filename.endswith('.jsonl') or filename.endswith('.json'):
                path = os.path.join(dirpath, filename)
                july_lines = 0
                july_trades = []
                
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        if filename.endswith('.json'):
                            try:
                                data = json.load(f)
                                if isinstance(data, list):
                                    for item in data:
                                        if isinstance(item, dict):
                                            date = item.get('date', '') or item.get('timestamp', '')
                                            if '2025-07' in str(date) or '202507' in str(date):
                                                july_lines += 1
                                                if 'pnl_usd' in item or 'pnl' in item:
                                                    july_trades.append(item)
                            except:
                                pass
                        else:
                            for line in f:
                                if '2025-07' in line or '202507' in line:
                                    july_lines += 1
                                    try:
                                        item = json.loads(line)
                                        if isinstance(item, dict) and ('pnl_usd' in item or 'pnl' in item or 'exit_reason' in item):
                                            july_trades.append(item)
                                    except:
                                        pass
                except Exception as e:
                    pass
                    
                if july_lines > 0 or len(july_trades) > 0:
                    rel_path = os.path.relpath(path, root_dir)
                    print(f"File: {rel_path} | July references: {july_lines} | July trades: {len(july_trades)}")
                    if len(july_trades) > 0:
                        pnl_sum = sum(float(t.get('pnl_usd', t.get('pnl', 0))) for t in july_trades)
                        losses = len([t for t in july_trades if float(t.get('pnl_usd', t.get('pnl', 0))) < 0])
                        wins = len([t for t in july_trades if float(t.get('pnl_usd', t.get('pnl', 0))) > 0])
                        print(f"  PnL Sum: ${pnl_sum:.2f} | Wins: {wins} | Losses: {losses}")

if __name__ == '__main__':
    search_all_jsonl_deep()
