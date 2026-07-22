import json
from collections import defaultdict
from datetime import datetime
import pandas as pd

def compute_audit():
    # 1. Get current simulation time
    last_time = "N/A"
    try:
        with open('agent_memory/reasoning_log.jsonl', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                last_reasoning = json.loads(lines[-1])
                last_time = last_reasoning.get('bar_time_utc') or last_reasoning.get('bar_time_et')
    except Exception as e:
        pass

    # 2. Parse and group trades
    trades_raw = []
    try:
        with open('agent_memory/trades_log.jsonl', 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        trade = json.loads(line)
                        trades_raw.append(trade)
                    except:
                        pass
    except:
        pass

    by_entry = {}
    for t in trades_raw:
        etime = t.get('entry_time')
        if etime not in by_entry: by_entry[etime] = []
        by_entry[etime].append(t)
        
    merged_trades = []
    for etime, parts in by_entry.items():
        if len(parts) == 1:
            merged_trades.append(parts[0])
        else:
            m = parts[0].copy()
            m['pnl_usd'] = sum(p.get('pnl_usd', p.get('pnl', 0)) for p in parts)
            # compute avg R based on pnl/risk
            # R value could be complex, let's just sum it for now
            m['r_ratio'] = sum(p.get('r_ratio', 0) for p in parts)
            merged_trades.append(m)

    if not merged_trades:
        print("Nessun trade registrato ancora.")
        return

    # 3. Calculate statistics
    total_trades = len(merged_trades)
    wins = [t for t in merged_trades if t.get('pnl_usd', t.get('pnl', 0)) > 0]
    losses = [t for t in merged_trades if t.get('pnl_usd', t.get('pnl', 0)) <= 0]
    win_rate = len(wins) / total_trades if total_trades else 0
    total_pnl = sum(t.get('pnl_usd', t.get('pnl', 0)) for t in merged_trades)
    
    avg_win = sum(t.get('pnl_usd', t.get('pnl', 0)) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.get('pnl_usd', t.get('pnl', 0)) for t in losses) / len(losses) if losses else 0
    
    # R computation:
    # If a trade hit full target, it's roughly 1.5R to 2R.
    r_ratios = [t.get('r_ratio', 0) for t in merged_trades if t.get('r_ratio')]
    avg_r = sum(r_ratios) / len(r_ratios) if r_ratios else 0
    
    # Group by direction
    longs = [t for t in merged_trades if t.get('direction') == 'long']
    shorts = [t for t in merged_trades if t.get('direction') == 'short']
    
    # Hourly distribution
    hourly_pnl = defaultdict(float)
    for t in merged_trades:
        try:
            et = pd.to_datetime(t.get('entry_time')).tz_convert('America/New_York')
            hour = et.hour
            hourly_pnl[hour] += t.get('pnl_usd', t.get('pnl', 0))
        except:
            pass

    print(f"=== AUDIT COMPLETO DEL BACKTEST ===")
    print(f"Ora Attuale Simulazione: {last_time}")
    print(f"Totale Trade Aggregati: {total_trades}")
    print(f"Win Rate: {win_rate*100:.1f}% ({len(wins)} Vinte, {len(losses)} Perse)")
    print(f"PNL Totale: ${total_pnl:.2f}")
    print(f"Avg Win: ${avg_win:.2f} | Avg Loss: ${avg_loss:.2f}")
    if avg_loss != 0:
        print(f"Payoff Ratio (Win/Loss): {abs(avg_win/avg_loss):.2f}")
    print(f"R Medio Realizzato per Trade: {avg_r:.2f}R")
    
    print(f"\n--- Direzionalita ---")
    print(f"Longs: {len(longs)} | Shorts: {len(shorts)}")
    
    print(f"\n--- Distribuzione Oraria (ET) ---")
    for h in sorted(hourly_pnl.keys()):
        print(f"Ore {h:02d}:00 -> ${hourly_pnl[h]:.2f}")

if __name__ == '__main__':
    compute_audit()
