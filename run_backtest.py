#!/usr/bin/env python
"""
CLI entry point.
Usage:
  python run_backtest.py                     # run all 106 days
  python run_backtest.py --days 5            # first 5 days
  python run_backtest.py --days 1 --dry-run  # no API calls, just detect candidates
"""
import argparse
from dotenv import load_dotenv
load_dotenv()
from src.backtest_runner import run_backtest, DATA_DIR
from src.metrics_reporter import compute_metrics, save_report

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--days',    type=int, default=0, help='0=all')
    p.add_argument('--start-date', type=str, default=None, help='YYYYMMDD start date')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--quiet', '-q', action='store_true',
                   help='Compact output: 1 line per candidate, verbose only on trades')
    p.add_argument('--data-dir', default=DATA_DIR)
    p.add_argument('--output',   default='output/reports')
    p.add_argument('--fabio-only', action='store_true', help='Skip Andrea confirmation consensus')
    p.add_argument('--reset-equity', action='store_true', help='Reset equity to 50000.0 before starting')
    args = p.parse_args()

    if args.reset_equity:
        from src.agent_memory import force_reset_equity
        force_reset_equity(50000.0)
        print("  [SYSTEM] Equity forcibly reset to $50,000.00 for this run.")

    trades = run_backtest(args.data_dir, args.days, args.dry_run, args.quiet, args.start_date, fabio_only=args.fabio_only)
    if not trades:
        print("No trades generated.")
        return
    metrics = compute_metrics(trades)
    print("\n=== BACKTEST RESULTS ===")
    print(f"Total trades:   {metrics['total_trades']}")
    print(f"Win rate:       {metrics['win_rate']:.1%}")
    print(f"Profit factor:  {metrics['profit_factor']:.2f}")
    print(f"Total P&L:      ${metrics['total_pnl_usd']:,.2f}")
    print(f"Avg R:          {metrics['avg_r']:.2f}")
    if not args.dry_run:
        save_report(metrics, trades, args.output, 'full')

if __name__ == '__main__':
    main()
