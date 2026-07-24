"""V2 audit validation — checks V2 verdicts against known trade outcomes.

Use case: given a list of historical trades (from V8b, V15, V16 logs), test
whether the V2 audit would have caught the bad ones and kept the good ones.

This is the smoking gun for V2's value: catch disasters, keep winners.
"""
import os
import sys
import csv
import datetime as dt
from collections import defaultdict
import pandas as pd

sys.path.insert(0, r'C:\Users\Mauro\Documents\nq-backtest-clean')
from scripts.ml.audit_v2_simulator import (
    load_day_bars, apply_v2_audit, V8B_TRADES, compute_big_trades_by_side
)
import joblib
import pytz

ET = pytz.timezone('America/New_York')
UTC = pytz.UTC

CSV_FEATURES = r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml\features_230d.csv'
OUT = r'C:\Users\Mauro\Documents\nq-backtest-clean\output\walkforward\v2_validation.md'


# Known trades extracted from V8b, V14, V15, V16 logs.
# Format: (date, time_et, direction, outcome, run_id)
# outcome: 'win' (target hit), 'stop' (stop loss), 'be' (breakeven), 'trail_be' (trail at BE)
KNOWN_TRADES = [
    # V8b (best run, +$666)
    ('20250204', '12:25', 'short', 'stop', 'V8b'),
    ('20250211', '09:35', 'long', 'be', 'V8b'),
    ('20250211', '10:50', 'long', 'win', 'V8b'),  # +$766

    # V15 (10-18 Feb, 18 trades all STOP/BE, ML filter 0.6)
    ('20250210', '15:00', 'short', 'stop', 'V15'),  # approx
    ('20250211', '11:00', 'long', 'stop', 'V15'),
    ('20250212', '14:00', 'short', 'trail_be', 'V15'),
    ('20250213', '10:00', 'short', 'trail_be', 'V15'),
    ('20250214', '10:00', 'short', 'trail_be', 'V15'),
    ('20250217', '10:00', 'long', 'trail_be', 'V15'),
    ('20250218', '10:00', 'short', 'stop', 'V15'),

    # V14 (10-18 Feb, 9 trades)
    ('20250210', '10:00', 'short', 'stop', 'V14'),
    ('20250211', '10:30', 'long', 'be', 'V14'),
    ('20250212', '11:00', 'short', 'stop', 'V14'),
    ('20250213', '14:00', 'short', 'trail_be', 'V14'),
    ('20250214', '10:00', 'long', 'be', 'V14'),
]


def get_v2_verdict(date_str, time_str, direction, df, day_bars, bar_lookup):
    """Run V2 audit on a specific bar and return verdict."""
    row_match = df[(df.date == date_str) & (df.time_et == time_str)]
    if len(row_match) == 0:
        return None, None, 'no features row'
    row = row_match.iloc[0]
    if row.score < 0.5:
        return None, None, f'score {row.score:.2f} < 0.5'
    et_time = dt.datetime.strptime(time_str, '%H:%M').time()
    et_dt = ET.localize(dt.datetime.combine(dt.datetime.strptime(date_str, '%Y%m%d').date(), et_time))
    minute = (et_dt.minute // 5) * 5
    et_dt = et_dt.replace(minute=minute, second=0, microsecond=0)
    bar_ts = et_dt.astimezone(UTC).replace(second=0, microsecond=0)
    bar = bar_lookup.get((date_str, bar_ts))
    if not bar:
        return None, None, 'no bar'
    bars_today = day_bars.get(date_str, [])
    try:
        cur_idx = bars_today.index(bar)
    except ValueError:
        return None, None, 'no bar in list'
    prev_bars = bars_today[:cur_idx]
    day_open = bars_today[:cur_idx + 1]
    return apply_v2_audit(bar, prev_bars, day_open, row, direction)


def main():
    print('=== V2 AUDIT VALIDATION AGAINST KNOWN TRADES ===\n')

    # Load features
    df = pd.read_csv(CSV_FEATURES, dtype={'date': str})
    df = df.sort_values(['date', 'time_et']).reset_index(drop=True)
    bundle = joblib.load(r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml\rf_v1.pkl')
    model = bundle['model']
    feats = bundle['feature_cols']
    df['score'] = model.predict_proba(df[feats].fillna(0).values)[:, 1]

    # Get unique dates from KNOWN_TRADES
    dates = sorted(set(t[0] for t in KNOWN_TRADES))
    print(f'Loading bars for {len(dates)} dates...')
    day_bars = {d: load_day_bars(d) for d in dates}
    bar_lookup = {}
    for d, bars in day_bars.items():
        for b in bars:
            ts = b.timestamp.astimezone(UTC).replace(minute=(b.timestamp.minute // 5) * 5, second=0, microsecond=0)
            bar_lookup[(d, ts)] = b
    print(f'  Loaded {sum(1 for v in day_bars.values() if v)}/{len(dates)} days')
    print()

    # Run validation
    print(f'{"run":>4}  {"date":>10}  {"time":>5}  {"dir":>5}  {"score":>5}  {"outcome":>9}  {"verdict":>8}  {"rule":>4}  {"correct":>7}')
    print('-' * 90)
    n_total = 0
    n_correct = 0
    n_skipped = 0
    skip_reasons = []
    by_outcome = defaultdict(lambda: {'total': 0, 'caught': 0, 'passed': 0, 'skipped': 0})
    by_run = defaultdict(lambda: {'total': 0, 'caught': 0, 'passed': 0, 'skipped': 0})

    for date_str, time_str, direction, outcome, run_id in KNOWN_TRADES:
        verdict, rule, reason = get_v2_verdict(date_str, time_str, direction, df, day_bars, bar_lookup)
        # Find row for score
        row_match = df[(df.date == date_str) & (df.time_et == time_str)]
        score = row_match.iloc[0].score if len(row_match) > 0 else 0

        if verdict is None:
            n_skipped += 1
            skip_reasons.append((run_id, date_str, time_str, reason))
            by_outcome[outcome]['skipped'] += 1
            by_run[run_id]['skipped'] += 1
            print(f'{run_id:>4}  {date_str}  {time_str}  {direction:>5}  {score:>5.2f}  {outcome:>9}  {"SKIP":>8}  {"-":>4}  reason={reason}')
            continue

        n_total += 1
        # CORRECT if: STOP/BE outcomes get REJECT, WIN outcomes get CONFIRM
        is_correct = (verdict == 'reject' and outcome in ('stop', 'be', 'trail_be')) or \
                     (verdict == 'confirm' and outcome == 'win')
        marker = '✓' if is_correct else '✗'
        if is_correct:
            n_correct += 1
            by_outcome[outcome]['caught' if verdict == 'reject' else 'passed'] += 1
            by_run[run_id]['caught' if verdict == 'reject' else 'passed'] += 1
        else:
            by_outcome[outcome]['passed' if verdict == 'confirm' else 'caught'] += 1
            by_run[run_id]['passed' if verdict == 'confirm' else 'caught'] += 1
        by_outcome[outcome]['total'] += 1
        by_run[run_id]['total'] += 1
        print(f'{run_id:>4}  {date_str}  {time_str}  {direction:>5}  {score:>5.2f}  {outcome:>9}  {verdict:>8}  {rule:>4}  {marker:>7}')

    print()
    print(f'Total: {n_total + n_skipped} ({n_total} validated, {n_skipped} skipped)')
    print(f'Correct: {n_correct}/{n_total} ({n_correct/max(n_total,1):.1%})')
    print()

    # Per-outcome breakdown
    print('=== PER-OUTCOME BREAKDOWN ===')
    print(f'{"outcome":>10}  {"total":>5}  {"caught":>6}  {"passed":>6}  {"skip":>4}  {"catch_rate":>10}')
    for outcome, stats in sorted(by_outcome.items()):
        total = stats['total']
        caught = stats['caught']
        passed = stats['passed']
        skipped = stats['skipped']
        catch_rate = caught / total if total > 0 else 0
        print(f'{outcome:>10}  {total:>5}  {caught:>6}  {passed:>6}  {skipped:>4}  {catch_rate:>10.1%}')

    print()
    print('=== PER-RUN BREAKDOWN ===')
    print(f'{"run":>5}  {"total":>5}  {"caught":>6}  {"passed":>6}  {"skip":>4}')
    for run, stats in sorted(by_run.items()):
        print(f'{run:>5}  {stats["total"]:>5}  {stats["caught"]:>6}  {stats["passed"]:>6}  {stats["skipped"]:>4}')

    # Save report
    with open(OUT, 'w') as f:
        f.write('# V2 Audit Validation Report\n\n')
        f.write('## Summary\n\n')
        f.write(f'- Total trades tested: {n_total + n_skipped}\n')
        f.write(f'- Validated (score>0.5): {n_total}\n')
        f.write(f'- Skipped (no data / score<=0.5): {n_skipped}\n')
        f.write(f'- Correct verdicts: {n_correct}/{n_total} ({n_correct/max(n_total,1):.1%})\n\n')
        f.write('## Per-outcome breakdown\n\n')
        f.write('| Outcome | Total | Caught (REJECT) | Passed (CONFIRM) | Catch rate |\n')
        f.write('|---|---|---|---|---|\n')
        for outcome, stats in sorted(by_outcome.items()):
            catch_rate = stats['caught'] / stats['total'] if stats['total'] > 0 else 0
            f.write(f'| {outcome} | {stats["total"]} | {stats["caught"]} | {stats["passed"]} | {catch_rate:.0%} |\n')
        f.write('\n## Per-run breakdown\n\n')
        f.write('| Run | Total | Caught | Passed | Skip |\n')
        f.write('|---|---|---|---|---|\n')
        for run, stats in sorted(by_run.items()):
            f.write(f'| {run} | {stats["total"]} | {stats["caught"]} | {stats["passed"]} | {stats["skipped"]} |\n')

    print(f'\nReport saved: {OUT}')


if __name__ == '__main__':
    main()
