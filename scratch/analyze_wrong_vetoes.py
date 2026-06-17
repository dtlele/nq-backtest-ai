import json
from collections import Counter, defaultdict

def main():
    try:
        with open('scratch/veto_simulation_results.json', 'r', encoding='utf-8') as f:
            results = json.load(f)
    except Exception as e:
        print(f"Error loading file: {e}")
        return
        
    wins = [r for r in results if r.get('sim_is_win') is True]
    print(f"Total wrong vetoes (wins): {len(wins)}")
    
    # 1. Analyze by Day Type or Setup
    setups = Counter([w.get('setup_type', 'unknown') for w in wins])
    reasons = Counter()
    
    # Analyze by veto reason categories
    # Typical veto reasons: "kill zone", "wick rejection", "historical WR", "low volume/toxic", "FOMO"
    reason_categories = defaultdict(list)
    
    print("\nDetailed list of wrong vetoes (Wins):")
    for idx, w in enumerate(wins):
        reason = w.get('no_trade_reason', '').lower()
        category = 'other'
        if 'kill zone' in reason:
            category = 'kill_zone_1015'
        elif 'body did not close' in reason or 'wick rejection' in reason or 'no body close' in reason:
            category = 'wick_rejection'
        elif 'win rate' in reason or 'wr' in reason or 'poor stats' in reason:
            category = 'historical_wr_stats'
        elif 'volume' in reason or 'thin' in reason or 'toxic' in reason:
            category = 'thin_volume_toxic'
        elif 'fomo' in reason or 'extended' in reason:
            category = 'anti_fomo'
            
        reason_categories[category].append(w)
        
        # Print first 10 wins
        if idx < 10:
            print(f"Date: {w.get('date')} {w.get('timestamp')}")
            print(f"  Setup: {w.get('setup_type')} | {w.get('direction').upper()} @ {w.get('entry')}")
            print(f"  Andrea's Veto: *{w.get('no_trade_reason')}*")
            print(f"  Outcome: +${w.get('sim_pnl_usd'):.2f}")
            print("-" * 50)
            
    print("\n--- Summary of Veto Categories for Wins ---")
    for cat, items in reason_categories.items():
        total_pnl = sum(item.get('sim_pnl_usd', 0) for item in items)
        print(f"Category: {cat} -> {len(items)} wins (Total PnL: ${total_pnl:.2f})")
        
    # Let's count the losses in the same categories to check their win rate!
    losses = [r for r in results if r.get('sim_is_win') is False]
    loss_categories = defaultdict(list)
    for l in losses:
        reason = l.get('no_trade_reason', '').lower()
        category = 'other'
        if 'kill zone' in reason:
            category = 'kill_zone_1015'
        elif 'body did not close' in reason or 'wick rejection' in reason or 'no body close' in reason:
            category = 'wick_rejection'
        elif 'win rate' in reason or 'wr' in reason or 'poor stats' in reason:
            category = 'historical_wr_stats'
        elif 'volume' in reason or 'thin' in reason or 'toxic' in reason:
            category = 'thin_volume_toxic'
        elif 'fomo' in reason or 'extended' in reason:
            category = 'anti_fomo'
        loss_categories[category].append(l)
        
    print("\n--- Win Rate and PnL by Veto Category ---")
    all_cats = set(reason_categories.keys()) | set(loss_categories.keys())
    for cat in all_cats:
        w_count = len(reason_categories[cat])
        l_count = len(loss_categories[cat])
        total = w_count + l_count
        wr = (w_count / total * 100) if total else 0
        w_pnl = sum(item.get('sim_pnl_usd', 0) for item in reason_categories[cat])
        l_pnl = sum(item.get('sim_pnl_usd', 0) for item in loss_categories[cat])
        net_pnl = w_pnl + l_pnl
        print(f"Category: {cat}")
        print(f"  Vetoed Trades: {total} (Wins: {w_count}, Losses: {l_count})")
        print(f"  Hypothetical Win Rate: {wr:.2f}%")
        print(f"  Hypothetical Net PnL: ${net_pnl:.2f} (Wins: ${w_pnl:.2f}, Losses: ${l_pnl:.2f})")
        print(f"  Andrea's Savings: ${-net_pnl:.2f} (If positive, Andrea saved us money by vetoing. If negative, she cost us money)")
        print("-" * 30)

if __name__ == '__main__':
    main()
