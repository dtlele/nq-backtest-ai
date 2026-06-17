import json

def check_discrepancies():
    with open('agent_memory/trades_log.jsonl', 'r') as f:
        for i, line in enumerate(f):
            if not line.strip(): continue
            t = json.loads(line)
            entry = t.get('entry')
            exit_p = t.get('exit_price')
            pnl_ticks = t.get('pnl_ticks', 0.0)
            direction = t.get('direction')
            date = t.get('date')
            time = t.get('entry_time')
            pnl_usd = t.get('pnl_usd', 0.0)
            
            sign = 1 if direction == 'long' else -1
            expected_ticks = sign * (exit_p - entry) / 0.25
            
            if abs(expected_ticks - pnl_ticks) > 0.5:
                print(f"Trade {i+1} on {date} {time}:")
                print(f"  Direction: {direction}")
                print(f"  Logged Entry: {entry} | Logged Exit: {exit_p}")
                print(f"  Logged PnL Ticks: {pnl_ticks} | Expected PnL Ticks: {expected_ticks:.1f}")
                print(f"  Logged PnL USD: ${pnl_usd:.2f}")
                print(f"  Fabio Entry: {t.get('fabio_reasoning')[:100]}...")

if __name__ == '__main__':
    check_discrepancies()
