#!/usr/bin/env python
"""
CLI entry point.
Usage:
  python run_backtest.py                     # run all 106 days
  python run_backtest.py --days 5            # first 5 days
  python run_backtest.py --days 1 --dry-run  # no API calls, just detect candidates
"""
import argparse
from src.backtest_runner import run_backtest, DATA_DIR
from src.metrics_reporter import compute_metrics, save_report

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--days',    type=int, default=0, help='0=all')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--data-dir', default=DATA_DIR)
    p.add_argument('--output',   default='output/reports')
    args = p.parse_args()

    trades = run_backtest(args.data_dir, args.days, args.dry_run)
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
