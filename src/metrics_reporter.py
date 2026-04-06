import json
from pathlib import Path
from src import ClosedTrade

def compute_metrics(trades: list) -> dict:
    if not trades:
        return {'total_trades': 0, 'wins': 0, 'losses': 0,
                'win_rate': 0.0, 'profit_factor': 0.0,
                'total_pnl_usd': 0.0, 'avg_r': 0.0}
    wins   = [t for t in trades if t.pnl_usd > 0]
    losses = [t for t in trades if t.pnl_usd <= 0]
    gross_profit = sum(t.pnl_usd for t in wins)
    gross_loss   = abs(sum(t.pnl_usd for t in losses))
    valid_r_trades = [t for t in trades if abs(t.entry - t.stop) >= 0.25]
    if len(valid_r_trades) < len(trades):
        invalid_count = len(trades) - len(valid_r_trades)
        import warnings
        warnings.warn(f"{invalid_count} trade(s) have entry==stop and are excluded from avg_r")
    avg_r = (sum(t.pnl_ticks / (abs(t.entry - t.stop) / 0.25)
                 for t in valid_r_trades) / len(valid_r_trades)
             if valid_r_trades else 0.0)
    return {
        'total_trades':   len(trades),
        'wins':           len(wins),
        'losses':         len(losses),
        'win_rate':       len(wins) / len(trades),
        'profit_factor':  round(gross_profit / gross_loss, 2) if gross_loss else 0.0,
        'total_pnl_usd':  round(sum(t.pnl_usd for t in trades), 2),
        'avg_pnl_usd':    round(sum(t.pnl_usd for t in trades) / len(trades), 2),
        'avg_r':          round(avg_r, 2),
        'by_setup':       _by_setup(trades),
    }

def _by_setup(trades: list) -> dict:
    result = {}
    for t in trades:
        s = t.setup_type
        result.setdefault(s, {'count': 0, 'pnl_usd': 0.0, 'wins': 0})
        result[s]['count']   += 1
        result[s]['pnl_usd'] += t.pnl_usd
        if t.pnl_usd > 0:
            result[s]['wins'] += 1
    return result

def save_report(metrics: dict, trades: list, output_dir: str, date_str: str) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    # JSON metrics
    with open(out / f'metrics_{date_str}.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    # Per-trade reasoning log
    log_path = out / f'trades_{date_str}.jsonl'
    with open(log_path, 'w', encoding='utf-8') as f:
        for t in trades:
            f.write(json.dumps({
                'entry_time':   t.entry_time.isoformat(),
                'exit_time':    t.exit_time.isoformat(),
                'direction':    t.direction,
                'entry':        t.entry,
                'exit_price':   t.exit_price,
                'exit_reason':  t.exit_reason,
                'pnl_usd':      t.pnl_usd,
                'setup_type':   t.setup_type,
                'confidence':   t.final_confidence,
                'r_ratio':      t.r_ratio,
                'fabio':        t.fabio_reasoning,
                'andrea':       t.andrea_reasoning,
            }) + '\n')
