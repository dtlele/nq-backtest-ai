"""Overfit check: run the same simulator on multiple days with ZERO tuning.
If the same rules work on 2025-03-03 (+$3975) and 2025-02-11 / 2025-03-04 / 2025-02-04,
then the system has real edge, not curve-fit.

Key rule: this script is a SEPARATE runner that does NOT touch
scripts/ml/test_20250303_new_rules.py. Same rules, multiple days.
"""
import os
import sys
import datetime as dt
import importlib.util

# Load the simulator module
spec = importlib.util.spec_from_file_location(
    "sim", r"C:\Users\Mauro\Documents\nq-backtest-clean\scripts\ml\test_20250303_new_rules.py")
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)

TEST_DAYS = [
    '20250218',  # USER REQUESTED: blind test, zero tuning
    '20250219',  # Day after for context
    '20250211',  # V8b known-win day (+$666) for sanity
    '20250204',  # V8b known-loss day
    '20250303',  # The one we "tuned" on (sanity check)
]

print('=' * 80)
print('OVERFIT CHECK: same rules, multiple days, zero tuning')
print('=' * 80)
print(f'Rules fixed from 2025-03-03 tuning:')
print(f'  - cap 1 winning trade per direction (re-entry after loss allowed)')
print(f'  - cooldown 30 min after loss')
print(f'  - LONG: delta>250 + close>last3_low+2 + wall>=50 (downtrend bounce)')
print(f'  - SHORT: close<min(prior 6 L)-3 + bias in (rot,lean,dr_down) + close<VWAP')
print(f'  - trailing: 50% ratchet after 8pt profit, never widens')
print()

results = []
for d in TEST_DAYS:
    print(f'\n--- {d} ---')
    cache = rf'C:\Users\Mauro\Documents\nq-backtest-clean\output\walkforward\day_bars_{d}.pkl'
    if not os.path.exists(cache):
        try:
            bars = sim.load_day_bars(d)
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            import pickle
            with open(cache, 'wb') as f:
                pickle.dump(bars, f)
        except Exception as e:
            print(f'  ERR load: {e}')
            continue
    else:
        import pickle
        with open(cache, 'rb') as f:
            bars = pickle.load(f)
    if not bars:
        print(f'  no bars')
        continue
    # Patch DATE in the module
    sim.DATE = d
    new_trades, skipped, bias_log = sim.run_new_system(bars)
    pnl_total = sum(t.get('pnl_usd', 0) for t in new_trades)
    n_wins = sum(1 for t in new_trades if t.get('pnl_pts', 0) > 0)
    n_losses = sum(1 for t in new_trades if t.get('pnl_pts', 0) <= 0)
    print(f'  trades: {len(new_trades)} (W:{n_wins} L:{n_losses})  PnL: {pnl_total:+.0f}$')
    for t in new_trades:
        h = t.get('entry_time_et', '?')
        d_ = t.get('direction', '?')
        e = t.get('entry', 0)
        ex = t.get('exit', 0)
        p = t.get('pnl_usd', 0)
        reason = t.get('llm_reason', '')[:40]
        print(f'    {h} {d_} @ {e:.0f} -> {ex:.0f}  {p:+.0f}$  ({reason})')
    results.append({'date': d, 'n': len(new_trades), 'pnl': pnl_total,
                    'wins': n_wins, 'losses': n_losses})

print('\n' + '=' * 80)
print('SUMMARY (no tuning, same rules)')
print('=' * 80)
print(f'{"date":>10}  {"#trade":>6}  {"W":>2}  {"L":>2}  {"PnL$":>8}')
print('-' * 40)
total_pnl = 0
total_n = 0
total_w = 0
for r in results:
    sign = '+' if r['pnl'] >= 0 else ''
    print(f'{r["date"]:>10}  {r["n"]:>6}  {r["wins"]:>2}  {r["losses"]:>2}  {sign}{r["pnl"]:>7.0f}$')
    total_pnl += r['pnl']
    total_n += r['n']
    total_w += r['wins']
print('-' * 40)
sign = '+' if total_pnl >= 0 else ''
print(f'{"TOTALE":>10}  {total_n:>6}  {total_w:>2}  {total_n-total_w:>2}  {sign}{total_pnl:>7.0f}$')
print()
print(f'Avg PnL/day: {total_pnl/len(results):+.0f}$')
print(f'Win rate: {100*total_w/total_n:.1f}%' if total_n else 'no trades')
