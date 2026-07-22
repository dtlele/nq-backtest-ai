import pandas as pd
import os
import json
from pathlib import Path

def export_trades_to_csv(trades_list, output_filepath):
    """
    Export list of ClosedTrade / trade dicts to standardized OOS CSV format.
    """
    records = []
    for t in trades_list:
        if isinstance(t, dict):
            entry_time = t.get('entry_time')
            exit_time = t.get('exit_time', entry_time)
            direction = t.get('direction', '').upper()
            entry = t.get('entry', 0.0)
            stop = t.get('stop', 0.0)
            target = t.get('target', 0.0)
            exit_price = t.get('exit_price', entry)
            exit_reason = t.get('exit_reason', 'unknown')
            pnl_usd = t.get('pnl_usd', 0.0)
            pnl_r = pnl_usd / 50.0
            mfe_r = t.get('mfe_r', 0.0)
            mae_r = t.get('mae_r', 0.0)
            veto_reason = t.get('veto_reason', 'none')
            regime = t.get('regime', 'RUNNER_3.5R')
        else:
            entry_time = str(t.entry_time)
            exit_time = str(getattr(t, 'exit_time', entry_time))
            direction = str(t.direction).upper()
            entry = float(t.entry)
            stop = float(t.stop)
            target = float(t.target)
            exit_price = float(t.exit_price)
            exit_reason = str(t.exit_reason)
            pnl_usd = float(t.pnl_usd)
            pnl_r = pnl_usd / 50.0
            mfe_r = getattr(t, 'mfe_r', 0.0)
            mae_r = getattr(t, 'mae_r', 0.0)
            veto_reason = getattr(t, 'veto_reason', 'none')
            regime = getattr(t, 'regime', 'RUNNER_3.5R')
            
        try:
            e_dt = pd.to_datetime(entry_time)
            x_dt = pd.to_datetime(exit_time)
            duration_min = round((x_dt - e_dt).total_seconds() / 60.0, 1)
        except:
            duration_min = 0.0
            
        records.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'direction': direction,
            'entry_price': entry,
            'stop_price': stop,
            'target_price': target,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_usd': pnl_usd,
            'realized_r': round(pnl_r, 2),
            'mfe_r': round(mfe_r, 2),
            'mae_r': round(mae_r, 2),
            'duration_min': duration_min,
            'veto_reason': veto_reason,
            'regime': regime
        })
        
    df = pd.DataFrame(records)
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    df.to_csv(output_filepath, index=False, encoding='utf-8')
    print(f"  [OOS EXPORTER] Saved {len(records)} trades to {output_filepath}")
    return df
