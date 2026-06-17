import json
from datetime import datetime
from collections import defaultdict

def run_analysis():
    log_path = r"c:\Users\Mauro\Documents\nq-backtest\agent_memory\trades_log.jsonl"
    
    trades = []
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                trades.append(json.loads(line))
            except Exception as e:
                print(f"Error parsing line: {e}")
                
    # Sort trades by entry time to ensure sequential equity calculations
    trades.sort(key=lambda t: t.get('entry_time', t.get('date')))
    
    # Filter trades from May 1 to Nov 30, 2025
    filtered_trades = []
    for t in trades:
        date_str = t.get('date')
        if not date_str:
            continue
        try:
            trade_date = datetime.strptime(date_str, "%Y-%m-%d")
            if datetime(2025, 5, 1) <= trade_date <= datetime(2025, 11, 30):
                filtered_trades.append(t)
        except ValueError:
            continue
            
    print(f"Total trades loaded: {len(trades)}")
    print(f"Trades in May-Nov range: {len(filtered_trades)}")
    
    if not filtered_trades:
        print("No trades found in the specified range.")
        return
        
    # Calculate continuous equity and drawdown
    initial_equity = 50000.0
    current_equity = initial_equity
    equity_curve = [initial_equity]
    
    peak_equity = initial_equity
    max_dd_usd = 0.0
    max_dd_pct = 0.0
    
    trade_metrics = []
    
    for i, t in enumerate(filtered_trades):
        pnl = t.get('pnl_usd', 0.0)
        current_equity += pnl
        equity_curve.append(current_equity)
        
        if current_equity > peak_equity:
            peak_equity = current_equity
            
        dd_usd = peak_equity - current_equity
        dd_pct = (dd_usd / peak_equity) * 100 if peak_equity > 0 else 0.0
        
        if dd_usd > max_dd_usd:
            max_dd_usd = dd_usd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
            
        t['equity_after'] = current_equity
        t['dd_usd'] = dd_usd
        t['dd_pct'] = dd_pct
        
    # Group by month
    monthly_data = defaultdict(list)
    for t in filtered_trades:
        month_key = t['date'][:7] # YYYY-MM
        monthly_data[month_key].append(t)
        
    # Month-by-month stats
    monthly_stats = {}
    running_equity = initial_equity
    
    for month in sorted(monthly_data.keys()):
        m_trades = monthly_data[month]
        m_wins = [t for t in m_trades if t.get('pnl_usd', 0.0) > 0]
        m_losses = [t for t in m_trades if t.get('pnl_usd', 0.0) <= 0]
        
        m_gross_win = sum(t.get('pnl_usd', 0.0) for t in m_wins)
        m_gross_loss = sum(t.get('pnl_usd', 0.0) for t in m_losses)
        m_net_pnl = sum(t.get('pnl_usd', 0.0) for t in m_trades)
        
        start_equity = running_equity
        end_equity = running_equity + m_net_pnl
        running_equity = end_equity
        
        # Win Rate
        m_wr = (len(m_wins) / len(m_trades) * 100) if m_trades else 0.0
        
        # Profit Factor
        m_pf = (m_gross_win / abs(m_gross_loss)) if m_gross_loss != 0 else float('inf')
        
        # Avg Win & Avg Loss
        avg_win = (m_gross_win / len(m_wins)) if m_wins else 0.0
        avg_loss = (m_gross_loss / len(m_losses)) if m_losses else 0.0
        
        # Avg R
        valid_r_trades = [t for t in m_trades if abs(t.get('entry', 0.0) - t.get('stop', 0.0)) >= 0.25]
        m_avg_r = 0.0
        if valid_r_trades:
            m_avg_r = sum(t.get('pnl_ticks', 0.0) / (abs(t.get('entry', 0.0) - t.get('stop', 0.0)) / 0.25)
                          for t in valid_r_trades) / len(valid_r_trades)
                          
        # Max Drawdown within the month
        m_peak = start_equity
        m_max_dd = 0.0
        m_curr = start_equity
        for t in m_trades:
            m_curr += t.get('pnl_usd', 0.0)
            if m_curr > m_peak:
                m_peak = m_curr
            dd = m_peak - m_curr
            if dd > m_max_dd:
                m_max_dd = dd
                
        monthly_stats[month] = {
            'start_equity': start_equity,
            'end_equity': end_equity,
            'net_pnl': m_net_pnl,
            'return_pct': (m_net_pnl / start_equity) * 100,
            'total_trades': len(m_trades),
            'wins': len(m_wins),
            'losses': len(m_losses),
            'win_rate': m_wr,
            'profit_factor': m_pf,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_r': m_avg_r,
            'max_dd_usd': m_max_dd,
            'max_dd_pct': (m_max_dd / start_equity) * 100
        }
        
    # Global metrics
    total_wins = [t for t in filtered_trades if t.get('pnl_usd', 0.0) > 0]
    total_losses = [t for t in filtered_trades if t.get('pnl_usd', 0.0) <= 0]
    global_gross_win = sum(t.get('pnl_usd', 0.0) for t in total_wins)
    global_gross_loss = sum(t.get('pnl_usd', 0.0) for t in total_losses)
    global_pnl = sum(t.get('pnl_usd', 0.0) for t in filtered_trades)
    global_wr = len(total_wins) / len(filtered_trades) * 100
    global_pf = global_gross_win / abs(global_gross_loss) if global_gross_loss != 0 else float('inf')
    
    valid_r_global = [t for t in filtered_trades if abs(t.get('entry', 0.0) - t.get('stop', 0.0)) >= 0.25]
    global_avg_r = 0.0
    if valid_r_global:
        global_avg_r = sum(t.get('pnl_ticks', 0.0) / (abs(t.get('entry', 0.0) - t.get('stop', 0.0)) / 0.25)
                           for t in valid_r_global) / len(valid_r_global)
                           
    # Pattern Analysis: Wins vs Losses
    # 1. Setup Type
    setup_analysis = defaultdict(lambda: {'count': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0, 'avg_r': 0.0})
    for t in filtered_trades:
        s = t.get('setup_type', 'unknown')
        pnl = t.get('pnl_usd', 0.0)
        setup_analysis[s]['count'] += 1
        setup_analysis[s]['pnl'] += pnl
        if pnl > 0:
            setup_analysis[s]['wins'] += 1
        else:
            setup_analysis[s]['losses'] += 1
            
    # Calculate R for setups
    for s, data in setup_analysis.items():
        s_trades = [t for t in filtered_trades if t.get('setup_type') == s]
        s_valid_r = [t for t in s_trades if abs(t.get('entry', 0.0) - t.get('stop', 0.0)) >= 0.25]
        if s_valid_r:
            data['avg_r'] = sum(t.get('pnl_ticks', 0.0) / (abs(t.get('entry', 0.0) - t.get('stop', 0.0)) / 0.25)
                                for t in s_valid_r) / len(s_valid_r)
                                
    # 2. Direction
    dir_analysis = defaultdict(lambda: {'count': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0, 'avg_r': 0.0})
    for t in filtered_trades:
        d = t.get('direction', 'unknown')
        pnl = t.get('pnl_usd', 0.0)
        dir_analysis[d]['count'] += 1
        dir_analysis[d]['pnl'] += pnl
        if pnl > 0:
            dir_analysis[d]['wins'] += 1
        else:
            dir_analysis[d]['losses'] += 1
            
    for d, data in dir_analysis.items():
        d_trades = [t for t in filtered_trades if t.get('direction') == d]
        d_valid_r = [t for t in d_trades if abs(t.get('entry', 0.0) - t.get('stop', 0.0)) >= 0.25]
        if d_valid_r:
            data['avg_r'] = sum(t.get('pnl_ticks', 0.0) / (abs(t.get('entry', 0.0) - t.get('stop', 0.0)) / 0.25)
                                for t in d_valid_r) / len(d_valid_r)

    # 3. Confidence Score Analysis
    conf_analysis = defaultdict(lambda: {'count': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0, 'avg_r': 0.0})
    for t in filtered_trades:
        c = t.get('final_confidence', 0)
        # Bin the confidence into bands: <80, 80-85, 86-90, >90
        if c < 80:
            band = "< 80"
        elif c <= 85:
            band = "80-85"
        elif c <= 90:
            band = "86-90"
        else:
            band = "> 90"
            
        pnl = t.get('pnl_usd', 0.0)
        conf_analysis[band]['count'] += 1
        conf_analysis[band]['pnl'] += pnl
        if pnl > 0:
            conf_analysis[band]['wins'] += 1
        else:
            conf_analysis[band]['losses'] += 1
            
    for b, data in conf_analysis.items():
        if b == "< 80":
            b_trades = [t for t in filtered_trades if t.get('final_confidence', 0) < 80]
        elif b == "80-85":
            b_trades = [t for t in filtered_trades if 80 <= t.get('final_confidence', 0) <= 85]
        elif b == "86-90":
            b_trades = [t for t in filtered_trades if 86 <= t.get('final_confidence', 0) <= 90]
        else:
            b_trades = [t for t in filtered_trades if t.get('final_confidence', 0) > 90]
            
        b_valid_r = [t for t in b_trades if abs(t.get('entry', 0.0) - t.get('stop', 0.0)) >= 0.25]
        if b_valid_r:
            data['avg_r'] = sum(t.get('pnl_ticks', 0.0) / (abs(t.get('entry', 0.0) - t.get('stop', 0.0)) / 0.25)
                                for t in b_valid_r) / len(b_valid_r)

    # 4. Exit Reasons Analysis
    exit_analysis = defaultdict(lambda: {'count': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0})
    for t in filtered_trades:
        reason = t.get('exit_reason', 'unknown')
        if reason.startswith('early_'):
            reason_key = 'early_exit'
        elif reason.startswith('trailing_stop'):
            reason_key = 'trailing_stop'
        else:
            reason_key = reason
            
        pnl = t.get('pnl_usd', 0.0)
        exit_analysis[reason_key]['count'] += 1
        exit_analysis[reason_key]['pnl'] += pnl
        if pnl > 0:
            exit_analysis[reason_key]['wins'] += 1
        else:
            exit_analysis[reason_key]['losses'] += 1

    # 5. Entry Time Analysis (Hour of day)
    time_analysis = defaultdict(lambda: {'count': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0})
    for t in filtered_trades:
        entry_time_str = t.get('entry_time')
        if entry_time_str:
            try:
                # e.g., "2025-05-01T14:37:00+00:00"
                dt = datetime.fromisoformat(entry_time_str)
                hour_key = f"{dt.hour:02d}:00"
            except Exception:
                hour_key = "unknown"
        else:
            hour_key = "unknown"
            
        pnl = t.get('pnl_usd', 0.0)
        time_analysis[hour_key]['count'] += 1
        time_analysis[hour_key]['pnl'] += pnl
        if pnl > 0:
            time_analysis[hour_key]['wins'] += 1
        else:
            time_analysis[hour_key]['losses'] += 1

    # 6. Stop size (Risk) wins vs losses
    win_stop_sizes = []
    loss_stop_sizes = []
    for t in filtered_trades:
        stop_size = abs(t.get('entry', 0.0) - t.get('stop', 0.0))
        if t.get('pnl_usd', 0.0) > 0:
            win_stop_sizes.append(stop_size)
        else:
            loss_stop_sizes.append(stop_size)
            
    avg_win_stop = sum(win_stop_sizes) / len(win_stop_sizes) if win_stop_sizes else 0.0
    avg_loss_stop = sum(loss_stop_sizes) / len(loss_stop_sizes) if loss_stop_sizes else 0.0

    # Write report details to stdout or a json file to read
    results = {
        'global': {
            'initial_equity': initial_equity,
            'ending_equity': current_equity,
            'net_pnl': global_pnl,
            'return_pct': (global_pnl / initial_equity) * 100,
            'total_trades': len(filtered_trades),
            'wins': len(total_wins),
            'losses': len(total_losses),
            'win_rate': global_wr,
            'profit_factor': global_pf,
            'avg_r': global_avg_r,
            'max_dd_usd': max_dd_usd,
            'max_dd_pct': max_dd_pct,
            'avg_win_stop_distance': avg_win_stop,
            'avg_loss_stop_distance': avg_loss_stop
        },
        'monthly': monthly_stats,
        'setup': dict(setup_analysis),
        'direction': dict(dir_analysis),
        'confidence': dict(conf_analysis),
        'exit': dict(exit_analysis),
        'time': dict(time_analysis)
    }
    
    with open('scratch_analysis_results.json', 'w') as out_f:
        json.dump(results, out_f, indent=2)
        
    print("Analysis finished and saved to scratch_analysis_results.json")

if __name__ == '__main__':
    run_analysis()
