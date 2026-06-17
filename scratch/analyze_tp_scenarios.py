import json

def analyze_rr_distribution():
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    
    print("=== RISK-TO-REWARD (R:R) DISTRIBUTION (MAY-NOV 2025 ACTIVE RUN) ===")
    
    rr_buckets = {
        "< 0.5": [],
        "0.5 - 1.0": [],
        "1.0 - 1.5": [],
        "1.5 - 2.0": [],
        "2.0 - 3.0": [],
        "3.0 - 5.0": [],
        "> 5.0": []
    }
    
    with open(trades_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                t = json.loads(line)
                date_str = t.get('date', '')
                if not (date_str >= '2025-05-01' and date_str <= '2025-11-30'):
                    continue
                    
                entry = t.get('entry', 0.0)
                stop = t.get('stop', 0.0)
                target = t.get('target', 0.0)
                pnl = t.get('pnl_usd', 0.0)
                
                risk = abs(entry - stop)
                reward = abs(target - entry)
                
                if risk == 0:
                    continue
                    
                rr = reward / risk
                
                if rr < 0.5:
                    bucket = "< 0.5"
                elif rr < 1.0:
                    bucket = "0.5 - 1.0"
                elif rr < 1.5:
                    bucket = "1.0 - 1.5"
                elif rr < 2.0:
                    bucket = "1.5 - 2.0"
                elif rr < 3.0:
                    bucket = "2.0 - 3.0"
                elif rr < 5.0:
                    bucket = "3.0 - 5.0"
                else:
                    bucket = "> 5.0"
                    
                rr_buckets[bucket].append(t)
            except Exception as e:
                pass
                
    total_trades = sum(len(items) for items in rr_buckets.values())
    print(f"{'R:R Bucket':<10} | {'Trades':<6} | {'Wins':<5} | {'Losses':<6} | {'WR%':<6} | {'PnL':<8}")
    print("-" * 55)
    for bucket, items in rr_buckets.items():
        wins = [i for i in items if i['pnl_usd'] > 0]
        losses = [i for i in items if i['pnl_usd'] <= 0]
        wr = len(wins) / len(items) * 100 if items else 0
        pnl = sum(i['pnl_usd'] for i in items)
        print(f"{bucket:<10} | {len(items):<6} | {len(wins):<5} | {len(losses):<6} | {wr:>5.1f}% | {pnl:>+8.2f}")

if __name__ == '__main__':
    analyze_rr_distribution()
