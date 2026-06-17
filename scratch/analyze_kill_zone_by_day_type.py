import json
import os

def main():
    try:
        with open('scratch/veto_simulation_results.json', 'r', encoding='utf-8') as f:
            results = json.load(f)
    except Exception as e:
        print(f"Error: {e}")
        return
        
    kz_trades = [r for r in results if 'kill zone' in r.get('no_trade_reason', '').lower()]
    print(f"Total Kill Zone trades: {len(kz_trades)}")
    
    print("\nKill Zone Trades Breakdown:")
    for t in kz_trades:
        # We need the day type from reasoning_log
        # Wait, the script simulate_veto_outcomes saved the reasoning log fields?
        # Let's check what fields we have in v.
        # date, timestamp, direction, entry, stop, target, fabio_reasoning, andrea_reasoning, no_trade_reason, sim_is_win, sim_pnl_usd
        # It didn't save the day_type!
        # Let's load the day_type directly from the reasoning_log.jsonl files for each trade.
        pass
        
    # Let's map timestamp -> day_type by reading reasoning_log
    day_types = {}
    log_files = [
        'c:/Users/Mauro/Documents/nq-backtest/agent_memory/reasoning_log.jsonl',
        'c:/Users/Mauro/Documents/nq-backtest/agent_memory/reasoning_log.jsonl.bak_202507',
        'c:/Users/Mauro/Documents/nq-backtest/agent_memory/reasoning_log.jsonl.pre_may19_clean',
        'c:/Users/Mauro/Documents/nq-backtest/agent_memory/reasoning_log_backup.jsonl'
    ]
    for lf in log_files:
        if not os.path.exists(lf): continue
        with open(lf, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    r = json.loads(line)
                except:
                    continue
                date = r.get('date')
                ts = r.get('bar_time_utc') or r.get('timestamp') or r.get('entry_time') or r.get('logged_at')
                dt = r.get('day_type')
                if date and ts and dt:
                    day_types[(date, ts)] = dt
                    
    # Now analyze Kill Zone trades with day_type
    wins_by_dt = {}
    losses_by_dt = {}
    
    for t in kz_trades:
        key = (t['date'], t['timestamp'])
        dt = day_types.get(key, 'unknown')
        is_win = t['sim_is_win']
        pnl = t['sim_pnl_usd']
        
        if is_win:
            if dt not in wins_by_dt: wins_by_dt[dt] = []
            wins_by_dt[dt].append(pnl)
        else:
            if dt not in losses_by_dt: losses_by_dt[dt] = []
            losses_by_dt[dt].append(pnl)
            
    print("\n--- Kill Zone Wins by Day Type ---")
    for dt, pnls in wins_by_dt.items():
        print(f"Day Type: {dt} -> {len(pnls)} wins (Total PnL: ${sum(pnls):.2f})")
        
    print("\n--- Kill Zone Losses by Day Type ---")
    for dt, pnls in losses_by_dt.items():
        print(f"Day Type: {dt} -> {len(pnls)} losses (Total PnL: ${sum(pnls):.2f})")
        
    print("\n--- Win Rate and net PnL by Day Type ---")
    all_dts = set(wins_by_dt.keys()) | set(losses_by_dt.keys())
    for dt in all_dts:
        w_count = len(wins_by_dt.get(dt, []))
        l_count = len(losses_by_dt.get(dt, []))
        total = w_count + l_count
        wr = (w_count / total * 100) if total else 0
        w_pnl = sum(wins_by_dt.get(dt, []))
        l_pnl = sum(losses_by_dt.get(dt, []))
        print(f"Day Type: {dt}")
        print(f"  Trades: {total} (Wins: {w_count}, Losses: {l_count})")
        print(f"  Win Rate: {wr:.2f}%")
        print(f"  Net PnL: ${w_pnl + l_pnl:.2f} (Wins: ${w_pnl:.2f}, Losses: ${l_pnl:.2f})")
        print("-" * 30)

if __name__ == '__main__':
    main()
