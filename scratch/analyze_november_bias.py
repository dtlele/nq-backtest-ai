import json
from collections import defaultdict
from datetime import datetime

def analyze_november():
    log_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\reasoning_log.jsonl"
    
    # We want to group evaluations by date
    daily_stats = defaultdict(lambda: {
        'total_evaluations': 0,
        'long_candidates': 0,
        'short_candidates': 0,
        'none_candidates': 0,
        'prefiltered': 0,
        'light_skip': 0,
        'short_disabled_count': 0,
        'long_taken': 0,
        'long_rejected_low_conf': 0,
        'long_rejected_andrea': 0,
        'long_pnl_usd': 0.0,
        'trades': []
    })
    
    # Load reasoning log
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                date_str = data.get('date', '')
                if not date_str.startswith('2025-11'):
                    continue
                
                stats = daily_stats[date_str]
                stats['total_evaluations'] += 1
                
                direction = data.get('fabio_direction', '')
                decision = data.get('decision', '')
                reason = data.get('no_trade_reason', '')
                
                # Check candidate direction
                if direction == 'short':
                    stats['short_candidates'] += 1
                    if 'short_trades_disabled' in str(reason) or 'short_trades_disabled' in str(data.get('no_trade_reason', '')):
                        stats['short_disabled_count'] += 1
                elif direction == 'long':
                    stats['long_candidates'] += 1
                    # Was it taken or rejected?
                    if decision == 'no_trade':
                        if 'confidence' in str(reason) or 'conf=' in str(reason):
                            stats['long_rejected_low_conf'] += 1
                        else:
                            stats['long_rejected_andrea'] += 1
                elif direction == 'none':
                    stats['none_candidates'] += 1
                
                if decision == 'prefiltered':
                    stats['prefiltered'] += 1
                elif decision == 'light_skip':
                    stats['light_skip'] += 1
                    
            except Exception as e:
                print(f"Error parsing line: {e}")
                
    # Now let's load trade logs to get the PnL of each day in November
    trades_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    with open(trades_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                t = json.loads(line)
                date_str = t.get('date', '')
                if not date_str.startswith('2025-11'):
                    continue
                
                stats = daily_stats[date_str]
                stats['long_taken'] += 1
                pnl = t.get('pnl_usd', 0.0)
                stats['long_pnl_usd'] += pnl
                stats['trades'].append(t)
            except Exception as e:
                print(f"Error parsing trade: {e}")
                
    # Print results in a clean table format
    print(f"=== NOVEMBER 2025 DAILY BIAS & CANDIDATES ANALYSIS ===")
    print(f"{'Date':<12} | {'PnL ($)':<9} | {'L Taken':<7} | {'L Rejected':<10} | {'S Discarded':<11} | {'L Candidates':<12} | {'S Candidates':<12} | {'Daily Bias'}")
    print("-" * 105)
    
    for date in sorted(daily_stats.keys()):
        stats = daily_stats[date]
        pnl = stats['long_pnl_usd']
        l_taken = stats['long_taken']
        l_rej = stats['long_rejected_low_conf'] + stats['long_rejected_andrea']
        s_disc = stats['short_disabled_count']
        l_cand = stats['long_candidates']
        s_cand = stats['short_candidates']
        
        # Calculate daily bias based on candidates
        total_cand = l_cand + s_cand
        if total_cand == 0:
            bias = "No bias (0 candidates)"
        else:
            long_ratio = l_cand / total_cand
            if long_ratio > 0.7:
                bias = "Strong LONG Bias"
            elif long_ratio > 0.55:
                bias = "Slight LONG Bias"
            elif long_ratio < 0.3:
                bias = "Strong SHORT Bias"
            elif long_ratio < 0.45:
                bias = "Slight SHORT Bias"
            else:
                bias = "Neutral Bias"
                
        print(f"{date:<12} | {pnl:>9.2f} | {l_taken:>7} | {l_rej:>10} | {s_disc:>11} | {l_cand:>12} | {s_cand:>12} | {bias}")
        
        # If there are trades on this day, show some details
        if stats['trades']:
            print("  -> Trades details:")
            for i, t in enumerate(stats['trades']):
                print(f"     T{i+1}: {t.get('setup_type')} {t.get('direction').upper()} entry={t.get('entry')} exit={t.get('exit_price')} reason={t.get('exit_reason')} pnl={t.get('pnl_usd')}")

if __name__ == '__main__':
    analyze_november()
