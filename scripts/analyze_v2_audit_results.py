"""Analyze V2 audit results vs V8b expected trades.

V8b known trades (from docs/):
  2025-02-04 12:25 SHORT 21555 -> -$50 (STOP)
  2025-02-11 09:35 LONG  21781 -> BE
  2025-02-11 10:50 LONG  21867 -> +$766 (TRAILING STOP)

V2 audit should:
  - REJECT 04 Feb 12:25 SHORT (prevent -$50 loss)
  - CONFIRM 11 Feb 10:50 LONG (keep +$766 winner)
  - KEEP 11 Feb 09:35 LONG BE (no harm)

This script reads agent_memory/ and produces a report.
"""
import os
import json
import sys
from collections import defaultdict

# V8b expected
V8B_EXPECTED = [
    {'date': '2025-02-04', 'time_et': '12:25', 'direction': 'short', 'pnl_usd': -50,
     'expected_v2': 'REJECT', 'rationale': 'prevent loss'},
    {'date': '2025-02-11', 'time_et': '09:35', 'direction': 'long', 'pnl_usd': 0,
     'expected_v2': 'CONFIRM', 'rationale': 'no harm (BE)'},
    {'date': '2025-02-11', 'time_et': '10:50', 'direction': 'long', 'pnl_usd': 766,
     'expected_v2': 'CONFIRM', 'rationale': 'keep winner'},
]

# V2 audit rules from docs/AUDIT_PROMPT_V2.md
V2_RULES = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6']

def main():
    reasoning_path = r'C:\Users\Mauro\Documents\nq-backtest-clean\agent_memory\reasoning_log.jsonl'
    trades_path = r'C:\Users\Mauro\Documents\nq-backtest-clean\agent_memory\trades_log.jsonl'

    if not os.path.exists(reasoning_path):
        print(f'ERROR: {reasoning_path} not found. Run V2 audit backtest first.')
        return

    # Load all reasonings for the V8b period
    v8b_dates = ['2025-02-04', '2025-02-05', '2025-02-06', '2025-02-07',
                 '2025-02-10', '2025-02-11']
    reasonings = []
    with open(reasoning_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            try:
                r = json.loads(line)
                if r.get('date') in v8b_dates:
                    reasonings.append(r)
            except:
                pass

    # Load trades
    trades = []
    if os.path.exists(trades_path):
        with open(trades_path, encoding='utf-8', errors='replace') as f:
            for line in f:
                try:
                    t = json.loads(line)
                    if t.get('date') in v8b_dates:
                        trades.append(t)
                except:
                    pass

    print('=' * 80)
    print(f'V2 AUDIT RESULTS — V8b PERIOD (2025-02-04 to 2025-02-11)')
    print('=' * 80)
    print(f'Total reasonings (V8b period): {len(reasonings)}')
    print(f'Total trades taken (V8b period): {len(trades)}')

    # Group reasonings by date and time
    by_datetime = defaultdict(list)
    for r in reasonings:
        d = r.get('date', '')
        t = r.get('bar_time_et', '')
        by_datetime[(d, t)].append(r)

    # Count audit decisions
    audit_decisions = []
    for r in reasonings:
        fr = r.get('fabio_reasoning', '') or ''
        decision = r.get('decision', '')
        if 'AUDIT REJECT' in fr or 'DEEP AUDIT REJECTED' in fr:
            # Extract which rule
            for rule in V2_RULES:
                if f'rule={rule}' in fr or f'{rule}:' in fr:
                    audit_decisions.append((r.get('date'), r.get('bar_time_et'),
                                            'REJECT', rule, fr[:100]))
                    break
        elif 'AUDIT CONFIRM' in fr or 'DEEP AUDIT CONFIRMED' in fr:
            audit_decisions.append((r.get('date'), r.get('bar_time_et'),
                                    'CONFIRM', '-', fr[:100]))

    print(f'\nAudit decisions: {len(audit_decisions)}')
    print(f'  REJECT: {sum(1 for x in audit_decisions if x[2] == "REJECT")}')
    print(f'  CONFIRM: {sum(1 for x in audit_decisions if x[2] == "CONFIRM")}')

    # By rule
    by_rule = defaultdict(int)
    for d, t, dec, rule, _ in audit_decisions:
        if dec == 'REJECT':
            by_rule[rule] += 1
    print(f'\nReject by rule:')
    for rule, n in sorted(by_rule.items(), key=lambda x: -x[1]):
        print(f'  {rule}: {n}')

    # V8b expected check
    print('\n' + '=' * 80)
    print('V8b EXPECTED TRADES — what did V2 audit do?')
    print('=' * 80)
    for exp in V8B_EXPECTED:
        d = exp['date']
        t = exp['time_et']
        # Find the closest bar
        candidates = [(k, v) for k, v in by_datetime.items() if k[0] == d]
        if not candidates:
            print(f'  {d} {t}: NO reasonings found (V2 audit not reached this day yet)')
            continue
        # Find by time match (allow 1-2 min tolerance)
        matching = []
        for (dd, tt), rs in candidates:
            try:
                h, m = map(int, tt.split(':'))
                eh, em = map(int, t.split(':'))
                diff = abs((h*60+m) - (eh*60+em))
                if diff <= 2:
                    matching.extend(rs)
            except:
                pass
        if not matching:
            print(f'  {d} {t}: NO bar at this time found (might be skipped as low-vol)')
            continue
        # Find the most relevant reasoning (with fabio_direction = exp direction)
        relevant = [r for r in matching if r.get('fabio_direction') == exp['direction']]
        if not relevant:
            print(f'  {d} {t}: LLM did not propose {exp["direction"]} (proposed: {set(r.get("fabio_direction") for r in matching)})')
            continue
        r = relevant[0]
        fr = r.get('fabio_reasoning', '') or ''
        if 'AUDIT REJECT' in fr or 'DEEP AUDIT REJECTED' in fr:
            actual = 'REJECT'
            rule = next((rl for rl in V2_RULES if f'rule={rl}' in fr or f'{rl}:' in fr), '?')
        elif 'AUDIT CONFIRM' in fr or 'DEEP AUDIT CONFIRMED' in fr:
            actual = 'CONFIRM'
            rule = '-'
        else:
            actual = 'NEITHER'
            rule = '-'
        # Check vs expected
        ok = '✓' if actual == exp['expected_v2'] else '✗'
        print(f'  {d} {t} {exp["direction"].upper():5} expected: {exp["expected_v2"]:7} '
              f'actual: {actual:7} rule={rule:3} {ok} ({exp["rationale"]})')

    # Trade summary
    print('\n' + '=' * 80)
    print('TRADES TAKEN ON V8b PERIOD (V2 audit confirmed)')
    print('=' * 80)
    if not trades:
        print('  (no trades taken)')
    else:
        total_pnl = 0
        for t in trades:
            et = t.get('entry_time','')[11:16] if t.get('entry_time') else '?'
            pnl = t.get('pnl_usd', 0)
            total_pnl += pnl
            print(f'  {t.get("date")} {et} {t.get("direction","?"):>5} '
                  f'entry={t.get("entry",0):.0f} exit={t.get("exit_price",0):.0f} '
                  f'pnl={pnl:+.0f}$ reason={t.get("fabio_reasoning","")[:50]}')
        print(f'\n  TOTAL PnL: {total_pnl:+.0f}$')

    # V8b baseline (expected without audit)
    print('\n' + '=' * 80)
    print('V8b BASELINE (without audit, expected PnL)')
    print('=' * 80)
    print(f'  -50$ (04 Feb 12:25 SHORT) + 0$ (11 Feb 09:35 LONG) + 766$ (11 Feb 10:50 LONG)')
    print(f'  TOTAL: +716$ (with assumption of taking the 3 known V8b trades)')

    if trades:
        # Compute "what if we had the V8b audit catch + V2 confirm only"
        baseline = -50 + 0 + 766
        new_pnl = sum(t.get('pnl_usd', 0) for t in trades)
        print(f'\n  ACTUAL V2 (audit): {new_pnl:+.0f}$')
        print(f'  Delta vs baseline: {new_pnl - baseline:+.0f}$')


if __name__ == '__main__':
    main()
