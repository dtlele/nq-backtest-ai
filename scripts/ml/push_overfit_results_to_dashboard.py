"""Push 5-day overfit-check results to dashboard (synclive killed so won't be overwritten)."""
import os
import json
import sys
import importlib.util
import datetime as dt
import pickle
import pytz

ET = pytz.timezone('America/New_York')
UTC = pytz.UTC
sys.path.insert(0, r'C:\Users\Mauro\Documents\nq-backtest-clean')

# Import the simulator
spec = importlib.util.spec_from_file_location(
    "sim", r"C:\Users\Mauro\Documents\nq-backtest-clean\scripts\ml\test_20250303_new_rules.py")
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)

TEST_DAYS = ['20250218', '20250219', '20250211', '20250204', '20250303']
LIVE_DATE = '20250303'

# Run simulator on each day
all_trades = []
all_sessions = []
all_reasonings = []
trade_id = 0

for d in TEST_DAYS:
    cache = rf'C:\Users\Mauro\Documents\nq-backtest-clean\output\walkforward\day_bars_{d}.pkl'
    if not os.path.exists(cache):
        bars = sim.load_day_bars(d)
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, 'wb') as f:
            pickle.dump(bars, f)
    else:
        with open(cache, 'rb') as f:
            bars = pickle.load(f)
    if not bars:
        print(f'{d}: no bars, skip')
        continue
    sim.DATE = d
    new_trades, skipped, bias_log = sim.run_new_system(bars)
    pnl_total = sum(t.get('pnl_usd', 0) for t in new_trades)
    wins = sum(1 for t in new_trades if t.get('pnl_pts', 0) > 0)
    losses = len(new_trades) - wins

    # Build dashboard trade entries
    for t in new_trades:
        trade_id += 1
        etime = t.get('entry_time_et', '00:00')
        xetime = t.get('exit_time_et', '00:00')
        date_yyyy = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        all_trades.append({
            'date': date_yyyy,
            'entry_time': f"{date_yyyy}T{etime}:00+00:00",
            'exit_time': f"{date_yyyy}T{xetime}:00+00:00",
            'direction': t['direction'],
            'entry': t['entry'],
            'stop': t['entry'] - 8 if t['direction'] == 'long' else t['entry'] + 8,
            'target': t['entry'] + 16 if t['direction'] == 'long' else t['entry'] - 16,
            'exit_price': t['exit'],
            'exit_reason': t['exit_reason'],
            'pnl_usd': t['pnl_usd'],
            'pnl_ticks': t['pnl_pts'] * 4,
            'r_ratio': 2.0,
            'setup_type': 'pullback',
            'final_confidence': 75,
            'fabio_reasoning': t['llm_reason'],
            'andrea_reasoning': 'simulated_no_llm',
            'contracts': 1,
            'source': 'OVERFIT_CHECK_5D',
            'bias_regime': t['bias_regime'],
            'bias_score': t['bias_score'],
        })

    all_sessions.append({
        'date': date_yyyy,
        'trades': len(new_trades),
        'wins': wins,
        'losses': losses,
        'pnl': pnl_total,
        'proposals': 0,
        'source': 'OVERFIT_CHECK_5D',
    })

    # Reasonings: per ogni M5 bar processato
    for b in bias_log:
        all_reasonings.append({
            'date': date_yyyy,
            'bar_time_et': b['time_et'],
            'fabio_confidence': 75 if b['bias_regime'] in ('drive_down', 'drive_up') else 50,
            'fabio_direction': ('short' if b['bias_score'] < 0 else 'long') if abs(b['bias_score']) > 15 else 'none',
            'session_bias': ('short' if b['bias_score'] < -15 else 'long' if b['bias_score'] > 15 else 'none'),
            'fabio_imbalance_phase': 'expansive' if abs(b['bias_score']) > 30 else 'none',
            'fabio_reasoning': b['drivers'][:200],
            'amt_day_profile': f"Bias={b['bias_regime']} score={b['bias_score']:+.0f}",
            'source': 'OVERFIT_CHECK_5D',
        })

    print(f'{d}: {len(new_trades)} trade, PnL {pnl_total:+.0f}$ (W{wins}/L{losses})')

# Build status.json
total_pnl = sum(s['pnl'] for s in all_sessions)
total_n = sum(s['trades'] for s in all_sessions)
total_w = sum(s['wins'] for s in all_sessions)
print(f'\nTOTALE: {total_n} trade, PnL {total_pnl:+.0f}$, WR {100*total_w/total_n:.0f}%')

status = {
    'LIVE_SESSION_STATE': {
        'date': LIVE_DATE,
        'ib_high': 0,
        'ib_low': 0,
    },
    'ANALYZED_DATES': [f"{d[:4]}-{d[4:6]}-{d[6:8]}" for d in TEST_DAYS],
    'ALL_TRADES': all_trades,
    'ALL_REASONINGS': all_reasonings,
    'LATEST_REASONING': all_reasonings[-1] if all_reasonings else None,
    'MOCK_SESSIONS': all_sessions,
    'ALL_PROPOSALS': all_trades,
    'updated_at': dt.datetime.now().isoformat(),
    'source_note': 'OVERFIT_CHECK_5D: stesso ruleset Python applicato a 5 giorni diversi, zero tuning per-day. Synclive disattivato per mostrare i risultati.',
}

out_path = r'C:\Users\Mauro\Documents\nq-backtest-clean\dashboard\public\data\status.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(status, f, indent=2, default=str)

print(f'\nScritto {out_path}')
print(f'Trade totali: {len(all_trades)}, Reasonings: {len(all_reasonings)}')
