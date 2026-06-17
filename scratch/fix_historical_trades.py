import json
from pathlib import Path
from datetime import datetime, timezone

def fix_trades():
    # 1. Load reasoning log entries
    reasonings = {}
    with open('agent_memory/reasoning_log.jsonl', 'r') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            if data.get('decision') == 'trade' or data.get('trade_direction') is not None:
                t_utc = data.get('bar_time_utc')
                if t_utc:
                    reasonings[t_utc] = data

    print(f"Loaded {len(reasonings)} trade decisions from reasoning_log.")

    # Backup trades_log.jsonl first
    trades_log_path = Path('agent_memory/trades_log.jsonl')
    backup_path = Path('agent_memory/trades_log.jsonl.bak_before_fix_3_5')
    if trades_log_path.exists():
        backup_path.write_text(trades_log_path.read_text(encoding='utf-8'), encoding='utf-8')
        print(f"Backup created at {backup_path}")

    # 2. Parse and correct trades
    corrected_trades = []
    mismatch_count = 0
    
    with open(trades_log_path, 'r') as f:
        for line in f:
            if not line.strip(): continue
            t = json.loads(line)
            entry_time = t.get('entry_time')
            if not entry_time:
                corrected_trades.append(t)
                continue
                
            matched = reasonings.get(entry_time)
            if matched:
                r_entry = matched.get('trade_entry')
                t_entry = t.get('entry')
                
                if r_entry and abs(r_entry - t_entry) > 0.1:
                    print(f"Correcting Trade on {t.get('date')} {entry_time}:")
                    print(f"  Old Entry: {t_entry} -> New Entry: {r_entry}")
                    
                    # Update entry
                    t['entry'] = r_entry
                    
                    # Recalculate pnl_ticks
                    direction = t.get('direction')
                    sign = 1 if direction == 'long' else -1
                    exit_price = t.get('exit_price')
                    
                    pnl_ticks = sign * (exit_price - r_entry) / 0.25
                    t['pnl_ticks'] = pnl_ticks
                    
                    # Recalculate PnL USD
                    contracts = t.get('contracts', 1)
                    # MNQ Tick Value = 0.50
                    gross_pnl_usd = pnl_ticks * 0.50 * contracts
                    commissions = contracts * 1.20 # round turn
                    net_pnl_usd = gross_pnl_usd - commissions
                    
                    print(f"  Old PnL: ${t.get('pnl_usd'):.2f} -> New PnL: ${net_pnl_usd:.2f}")
                    t['pnl_usd'] = net_pnl_usd
                    
                    # Recalculate r_ratio
                    stop = t.get('stop')
                    risk = abs(r_entry - stop)
                    target = t.get('target')
                    reward = abs(target - r_entry)
                    t['r_ratio'] = round(reward / risk, 2) if risk > 0 else 0.0
                    
                    mismatch_count += 1
            corrected_trades.append(t)

    # 3. Write back to trades_log.jsonl
    with open(trades_log_path, 'w', encoding='utf-8') as f:
        for t in corrected_trades:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')
            
    print(f"Successfully corrected {mismatch_count} trades in trades_log.jsonl.")

    # 4. Update the compounding equity curve in session_state
    # Starting from $50,000, we add each trade PnL to compute the final equity
    equity = 50000.0
    for t in corrected_trades:
        equity += t.get('pnl_usd', 0.0)
        
    print(f"Recalculated final equity: ${equity:.2f}")
    
    # We can also update session_state if the user wants, but it might interfere with the running process
    # Let's read session_state, update its equity, and save it
    session_path = Path('agent_memory/session_state.json')
    if session_path.exists():
        try:
            state = json.loads(session_path.read_text(encoding='utf-8'))
            old_eq = state.get('equity')
            state['equity'] = equity
            session_path.write_text(json.dumps(state, indent=2), encoding='utf-8')
            print(f"Updated session_state.json equity from ${old_eq:.2f} to ${equity:.2f}")
        except Exception as e:
            print(f"Failed to update session_state.json: {e}")

if __name__ == '__main__':
    fix_trades()
