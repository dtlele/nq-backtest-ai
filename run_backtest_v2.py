#!/usr/bin/env python
"""
V2.0 — Backtest runner deterministico (no LLM).
Uso:
  python run_backtest_v2.py --start 2025-02-03 --end 2025-02-28
  python run_backtest_v2.py --days 3            # prime N date disponibili
Output: output/v2/trades_v2_<start>_<end>.csv + summary_v2_*.json
Tutti i numeri sono prodotti dal motore — nessuna metrica manuale.
"""
import sys
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
import argparse, json
from pathlib import Path
from datetime import date

import pandas as pd

from src.v2.config import Config
from src.v2.loader import DayLoader
from src.v2.engine import BacktestEngine

TRADES_DIR = 'C:/Users/Mauro/Documents/databento-data'


def trades_to_rows(trades, date_str):
    rows = []
    for t in trades:
        rows.append({
            'date': date_str,
            'setup': t.setup,
            'direction': t.direction.value,
            'entry': t.entry,
            'stop_initial': t.stop_initial,
            'target1': t.target1,
            'exit_price': t.exit_price,
            'exit_reason': t.exit_reason,
            'ts_entry': str(t.ts_entry),
            'ts_exit': str(t.ts_exit),
            'contracts': t.contracts,
            'pnl_usd': t.pnl_usd,
            'pnl_points': t.pnl_points,
            'r_multiple': t.r_multiple,
            'gex_regime': t.gex_regime,
        })
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--start', default=None, help='YYYY-MM-DD')
    p.add_argument('--end', default=None, help='YYYY-MM-DD')
    p.add_argument('--days', type=int, default=0, help='prime N date (se no start/end)')
    p.add_argument('--intrabar', default='stop_first', choices=['stop_first', 'target_first'])
    p.add_argument('--slippage-mult', type=float, default=1.0)
    p.add_argument('--config', default=None)
    args = p.parse_args()

    cfg = Config.load(args.config)
    loader = DayLoader(TRADES_DIR, data_dir=cfg.data_dir)
    dates = loader.list_dates()
    if args.start:
        dates = [d for d in dates if d >= args.start]
    if args.end:
        dates = [d for d in dates if d <= args.end]
    if args.days:
        dates = dates[:args.days]
    if not dates:
        print('Nessuna data trovata.')
        return

    eng = BacktestEngine(cfg, llm_policy=None,
                         intrabar_policy=args.intrabar,
                         slippage_mult=args.slippage_mult)

    all_rows, day_stats = [], []
    for d in dates:
        ctx, bars = loader.load(d)
        if not bars:
            continue
        res = eng.run_day(ctx, bars)
        rows = trades_to_rows(res.trades, d)
        all_rows += rows
        pnl = sum(r['pnl_usd'] for r in rows)
        day_stats.append({'date': d, 'n_signals': res.n_signals,
                          'n_trades': len(rows), 'pnl_usd': round(pnl, 2)})
        print(f"{d}: segnali={res.n_signals:3d} trade={len(rows)} pnl=${pnl:9.2f}")

    out_dir = Path(cfg.output_dir) / 'v2'
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"{dates[0]}_{dates[-1]}"
    df = pd.DataFrame(all_rows)
    csv_path = out_dir / f'trades_v2_{tag}.csv'
    df.to_csv(csv_path, index=False)

    pnl = df['pnl_usd'] if len(df) else pd.Series(dtype=float)
    wins = (pnl > 0).sum() if len(df) else 0
    gp = pnl[pnl > 0].sum() if len(df) else 0.0
    gl = -pnl[pnl < 0].sum() if len(df) else 0.0
    summary = {
        'engine': 'v2.0 deterministic (no LLM)',
        'intrabar_policy': args.intrabar,
        'slippage_mult': args.slippage_mult,
        'period': {'start': dates[0], 'end': dates[-1], 'days': len(day_stats)},
        'n_trades': len(df),
        'win_rate': round(wins / len(df), 3) if len(df) else None,
        'pnl_usd': round(pnl.sum(), 2) if len(df) else 0.0,
        'profit_factor': round(gp / gl, 2) if gl > 0 else None,
        'avg_r': round(df['r_multiple'].mean(), 2) if len(df) else None,
        'by_exit_reason': df['exit_reason'].value_counts().to_dict() if len(df) else {},
        'by_setup': df.groupby('setup')['pnl_usd'].agg(['count', 'sum']).round(2).to_dict() if len(df) else {},
        'days': day_stats,
    }
    json_path = out_dir / f'summary_v2_{tag}.json'
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print('\n=== SUMMARY ===')
    print(json.dumps({k: v for k, v in summary.items() if k != 'days'}, indent=2, ensure_ascii=False))
    print(f"\nCSV: {csv_path}\nJSON: {json_path}")


if __name__ == '__main__':
    main()
