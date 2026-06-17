import json

def analyze_jan_days():
    reasoning_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log_jan2025.jsonl"
    
    print("=== CANDIDATE EVALUATIONS FOR JAN 8, 13, 14, 2025 ===")
    with open(reasoning_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            date = data.get('date')
            if date in ['2025-01-08', '2025-01-13', '2025-01-14']:
                time = data.get('bar_time_et')
                direction = data.get('fabio_direction')
                decision = data.get('decision')
                reason = data.get('no_trade_reason')
                close = data.get('bar_close')
                ibh = data.get('ib_high')
                ibl = data.get('ib_low')
                day_type = data.get('day_type')
                
                print(f"Date: {date} | Time: {time} | Fabio: {direction} | Decision: {decision} | Reason: {reason}")
                print(f"  Day Type: {day_type} | Close: {close} | IB: [{ibl}, {ibh}]")
                print(f"  Fabio Reasoning: {data.get('fabio_reasoning')[:300]}")
                if data.get('andrea_reasoning'):
                    print(f"  Andrea Reasoning: {data.get('andrea_reasoning')[:300]}")
                print("-" * 100)

if __name__ == '__main__':
    analyze_jan_days()
