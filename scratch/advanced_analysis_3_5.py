import json
from collections import defaultdict
import re

def analyze_trades():
    trades = []
    with open('agent_memory/trades_log.jsonl', 'r') as f:
        for line in f:
            if not line.strip():
                continue
            trades.append(json.loads(line))
            
    print(f"Loaded {len(trades)} trades.")
    
    total_pnl = 0.0
    wins = []
    losses = []
    breakeven = []
    
    for t in trades:
        pnl = t.get('pnl_usd', 0.0)
        total_pnl += pnl
        if pnl > 0:
            wins.append(t)
        elif pnl < 0:
            losses.append(t)
        else:
            breakeven.append(t)
            
    win_rate = (len(wins) / len(trades)) * 100 if trades else 0
    total_win_pnl = sum(t.get('pnl_usd', 0.0) for t in wins)
    total_loss_pnl = sum(t.get('pnl_usd', 0.0) for t in losses)
    avg_win = total_win_pnl / len(wins) if wins else 0
    avg_loss = total_loss_pnl / len(losses) if losses else 0
    profit_factor = abs(total_win_pnl / total_loss_pnl) if total_loss_pnl != 0 else float('inf')
    
    print("\n==================================================")
    print("           OVERALL TRADING PERFORMANCE            ")
    print("==================================================")
    print(f"Total Trades:       {len(trades)}")
    print(f"Wins:               {len(wins)} ({win_rate:.1f}%)")
    print(f"Losses:             {len(losses)} ({((len(losses)/len(trades))*100):.1f}%)")
    print(f"Breakeven:          {len(breakeven)} ({((len(breakeven)/len(trades))*100):.1f}%)")
    print(f"Net PnL:            ${total_pnl:.2f}")
    print(f"Profit Factor:      {profit_factor:.2f}")
    print(f"Average Win:        ${avg_win:.2f}")
    print(f"Average Loss:       ${avg_loss:.2f}")
    print(f"Risk/Reward Ratio (Avg Win/Avg Loss): {abs(avg_win/avg_loss) if avg_loss != 0 else 0:.2f}")
    
    # Setup Type performance
    setups = defaultdict(list)
    for t in trades:
        setups[t.get('setup_type', 'unknown')].append(t)
        
    print("\n==================================================")
    print("             PERFORMANCE BY SETUP TYPE            ")
    print("==================================================")
    print(f"{'Setup Type':<20} | {'Trades':<6} | {'Win %':<6} | {'Net PnL':<10} | {'Avg PnL':<8}")
    print("-" * 60)
    for s_type, s_trades in setups.items():
        s_wins = [t for t in s_trades if t.get('pnl_usd', 0.0) > 0]
        s_wr = (len(s_wins) / len(s_trades)) * 100
        s_pnl = sum(t.get('pnl_usd', 0.0) for t in s_trades)
        s_avg = s_pnl / len(s_trades)
        print(f"{s_type:<20} | {len(s_trades):<6} | {s_wr:>5.1f}% | ${s_pnl:>8.2f} | ${s_avg:>7.2f}")

    # Directional Performance
    directions = defaultdict(list)
    for t in trades:
        directions[t.get('direction', 'unknown')].append(t)
        
    print("\n==================================================")
    print("            PERFORMANCE BY DIRECTION              ")
    print("==================================================")
    print(f"{'Direction':<12} | {'Trades':<6} | {'Win %':<6} | {'Net PnL':<10} | {'Avg PnL':<8}")
    print("-" * 50)
    for d, d_trades in directions.items():
        d_wins = [t for t in d_trades if t.get('pnl_usd', 0.0) > 0]
        d_wr = (len(d_wins) / len(d_trades)) * 100
        d_pnl = sum(t.get('pnl_usd', 0.0) for t in d_trades)
        d_avg = d_pnl / len(d_trades)
        print(f"{d:<12} | {len(d_trades):<6} | {d_wr:>5.1f}% | ${d_pnl:>8.2f} | ${d_avg:>7.2f}")

    # Stop Loss Distance Analysis
    # Let's group stop distance in bins: <=20, 20-30, 30-40, 40-50, >50 points
    def get_stop_distance(trade):
        entry = trade.get('entry')
        stop = trade.get('stop')
        if entry and stop:
            return abs(entry - stop)
        return 0
        
    stop_bins = [
        ("<= 20 pts", lambda dist: dist <= 20),
        ("20 - 30 pts", lambda dist: 20 < dist <= 30),
        ("30 - 40 pts", lambda dist: 30 < dist <= 40),
        ("40 - 50 pts", lambda dist: 40 < dist <= 50),
        ("> 50 pts", lambda dist: dist > 50)
    ]
    
    print("\n==================================================")
    print("         STOP LOSS DISTANCE ANALYSIS              ")
    print("==================================================")
    print(f"{'Stop Distance':<15} | {'Trades':<6} | {'Win %':<6} | {'Net PnL':<10} | {'Avg PnL':<8}")
    print("-" * 55)
    for bin_name, bin_fn in stop_bins:
        bin_trades = [t for t in trades if bin_fn(get_stop_distance(t))]
        if not bin_trades:
            continue
        bin_wins = [t for t in bin_trades if t.get('pnl_usd', 0.0) > 0]
        bin_wr = (len(bin_wins) / len(bin_trades)) * 100
        bin_pnl = sum(t.get('pnl_usd', 0.0) for t in bin_trades)
        bin_avg = bin_pnl / len(bin_trades)
        print(f"{bin_name:<15} | {len(bin_trades):<6} | {bin_wr:>5.1f}% | ${bin_pnl:>8.2f} | ${bin_avg:>7.2f}")

    # Exit Reason Analysis
    exit_reasons = defaultdict(list)
    for t in trades:
        raw_reason = t.get('exit_reason', 'unknown')
        # Standardize exit reasons
        if raw_reason.startswith('early'):
            reason = 'early_exit'
        elif raw_reason == 'stop':
            reason = 'stop_loss'
        elif raw_reason == 'target':
            reason = 'target_hit'
        elif raw_reason == 'trailing_stop':
            reason = 'trailing_stop'
        else:
            reason = raw_reason
        exit_reasons[reason].append(t)
        
    print("\n==================================================")
    print("            PERFORMANCE BY EXIT REASON            ")
    print("==================================================")
    print(f"{'Exit Reason':<18} | {'Trades':<6} | {'Net PnL':<10} | {'Avg PnL':<8}")
    print("-" * 50)
    for r, r_trades in exit_reasons.items():
        r_pnl = sum(t.get('pnl_usd', 0.0) for t in r_trades)
        r_avg = r_pnl / len(r_trades)
        print(f"{r:<18} | {len(r_trades):<6} | ${r_pnl:>8.2f} | ${r_avg:>7.2f}")

    # Confidence Correlation
    # Let's bin confidence: <80, 80-85, 86-90, >90
    conf_bins = [
        ("< 80", lambda c: c < 80),
        ("80 - 85", lambda c: 80 <= c <= 85),
        ("86 - 90", lambda c: 86 <= c <= 90),
        ("> 90", lambda c: c > 90)
    ]
    
    print("\n==================================================")
    print("           CONFIDENCE SCORE CORRELATION           ")
    print("==================================================")
    print(f"{'Confidence':<12} | {'Trades':<6} | {'Win %':<6} | {'Net PnL':<10} | {'Avg PnL':<8}")
    print("-" * 50)
    for bin_name, bin_fn in conf_bins:
        bin_trades = [t for t in trades if bin_fn(t.get('final_confidence', 0))]
        if not bin_trades:
            continue
        bin_wins = [t for t in bin_trades if t.get('pnl_usd', 0.0) > 0]
        bin_wr = (len(bin_wins) / len(bin_trades)) * 100
        bin_pnl = sum(t.get('pnl_usd', 0.0) for t in bin_trades)
        bin_avg = bin_pnl / len(bin_trades)
        print(f"{bin_name:<12} | {len(bin_trades):<6} | {bin_wr:>5.1f}% | ${bin_pnl:>8.2f} | ${bin_avg:>7.2f}")

    # Time of Day (Hour ET)
    def get_hour(trade):
        time_str = trade.get('entry_time', '')
        if time_str and len(time_str) >= 13:
            return time_str[11:13]
        return "Unknown"
        
    hours = defaultdict(list)
    for t in trades:
        hours[get_hour(t)].append(t)
        
    print("\n==================================================")
    print("            PERFORMANCE BY TIME OF DAY            ")
    print("==================================================")
    print(f"{'Hour (ET)':<10} | {'Trades':<6} | {'Win %':<6} | {'Net PnL':<10} | {'Avg PnL':<8}")
    print("-" * 50)
    for h in sorted(hours.keys()):
        h_trades = hours[h]
        h_wins = [t for t in h_trades if t.get('pnl_usd', 0.0) > 0]
        h_wr = (len(h_wins) / len(h_trades)) * 100
        h_pnl = sum(t.get('pnl_usd', 0.0) for t in h_trades)
        h_avg = h_pnl / len(h_trades)
        print(f"{h + ':00':<10} | {len(h_trades):<6} | {h_wr:>5.1f}% | ${h_pnl:>8.2f} | ${h_avg:>7.2f}")

    # Semantic Keyword Analysis on Fabio's and Andrea's reasoning
    # We want to identify terms associated with wins vs losses
    print("\n==================================================")
    print("       SEMANTIC REASONING WORDS ASSOCIATIONS      ")
    print("==================================================")
    
    # We will tokenize reasoning and find words that are significantly more frequent in wins vs losses
    # Stop words to exclude
    stop_words = {'the', 'is', 'at', 'to', 'and', 'a', 'in', 'of', 'for', 'with', 'on', 'this', 'that', 'by', 'from', 'it', 'above', 'below', 'recent', 'an', 'are', 'was', 'were', 'be', 'as', 'but', 'or', 'at', 'has', 'have', 'had', 'been', 'show', 'shows', 'showing', 'confirm', 'confirms', 'placed', 'stop', 'target', 'price', 'entry', 'exit', 'trade', 'trades', 'market', 'trend', 'level', 'levels', 'zone', 'zones', 'contracts'}
    
    win_words = defaultdict(int)
    loss_words = defaultdict(int)
    
    for t in wins:
        reasoning = (t.get('fabio_reasoning', '') + " " + t.get('andrea_reasoning', '')).lower()
        words = re.findall(r'\b[a-z]{3,}\b', reasoning)
        unique_words = set(words) - stop_words
        for w in unique_words:
            win_words[w] += 1
            
    for t in losses:
        reasoning = (t.get('fabio_reasoning', '') + " " + t.get('andrea_reasoning', '')).lower()
        words = re.findall(r'\b[a-z]{3,}\b', reasoning)
        unique_words = set(words) - stop_words
        for w in unique_words:
            loss_words[w] += 1
            
    # Calculate win bias
    word_stats = []
    all_words = set(win_words.keys()) | set(loss_words.keys())
    for w in all_words:
        w_count = win_words[w]
        l_count = loss_words[w]
        w_pct = (w_count / len(wins)) * 100 if wins else 0
        l_pct = (l_count / len(losses)) * 100 if losses else 0
        delta = w_pct - l_pct
        total_occurrences = w_count + l_count
        if total_occurrences >= 5: # filter out rare words
            word_stats.append((w, w_pct, l_pct, delta, total_occurrences))
            
    # Sort by delta descending (strongest win bias)
    word_stats.sort(key=lambda x: x[3], reverse=True)
    
    print("Top 12 Words with WIN BIAS (more frequent in wins):")
    print(f"{'Word':<15} | {'Win %':<8} | {'Loss %':<8} | {'Delta':<8} | {'Total'}")
    print("-" * 55)
    for w, w_pct, l_pct, delta, tot in word_stats[:12]:
        print(f"{w:<15} | {w_pct:>6.1f}% | {l_pct:>6.1f}% | {delta:>+7.1f}% | {tot}")
        
    print("\nTop 12 Words with LOSS BIAS (more frequent in losses):")
    print(f"{'Word':<15} | {'Win %':<8} | {'Loss %':<8} | {'Delta':<8} | {'Total'}")
    print("-" * 55)
    for w, w_pct, l_pct, delta, tot in word_stats[-12:]:
        print(f"{w:<15} | {w_pct:>6.1f}% | {l_pct:>6.1f}% | {delta:>+7.1f}% | {tot}")

    # Let's perform a forensic analysis of the worst trades
    # (Losses > $100)
    print("\n==================================================")
    print("            FORENSIC ON MAJOR LOSSES              ")
    print("==================================================")
    major_losses = [t for t in losses if t.get('pnl_usd', 0.0) < -100]
    print(f"Found {len(major_losses)} major losses (< -$100):")
    for idx, t in enumerate(major_losses):
        print(f"{idx+1}. Date: {t.get('date')} | PnL: ${t.get('pnl_usd'):.2f} | Direction: {t.get('direction')} | Stop: {get_stop_distance(t):.1f} pts | Conf: {t.get('final_confidence')}%")
        print(f"   Reasoning: {t.get('fabio_reasoning')[:150]}...")
        print(f"   Andrea:    {t.get('andrea_reasoning')}")

if __name__ == "__main__":
    analyze_trades()
