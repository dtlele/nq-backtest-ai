#!/usr/bin/env python
"""
MFE/MAE HONEST MEASUREMENT — Feb 2025
Misura l'escursione reale tick-by-tick dopo ogni entry registrata nei log.
Nessuna simulazione di target: con MFE/MAE veri ogni strategia di uscita
e' calcolabile a posteriori offline.
Output: output/honest_resim/mfe_mae_feb.csv
"""
import sys, json, glob
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
from pathlib import Path

DATA_DIR = Path('C:/Users/Mauro/Documents/databento-data')
OUT_DIR = Path('output/honest_resim')

def load_real_entries():
    entries = {}
    paths = ['output/backup_suspended_run/agent_memory_backup/trades_log.jsonl']
    paths += glob.glob('agent_memory/feb_w*/trades_log.jsonl')
    for p in paths:
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if not line:
                continue
            t = json.loads(line)
            et = t.get('entry_time', '')
            if not et.startswith('2025-02'):
                continue
            key = (et, t['entry'])
            if key not in entries:
                entries[key] = {
                    'entry_time': et, 'date': et[:10],
                    'direction': t['direction'].lower(),
                    'entry': float(t['entry']), 'stop': float(t['stop']),
                    'legacy_pnl_usd': 0.0,
                    'setup_type': t.get('setup_type', ''),
                    'confidence': t.get('final_confidence', None),
                }
            entries[key]['legacy_pnl_usd'] += float(t.get('pnl_usd', 0.0))
    df = pd.DataFrame(entries.values()).sort_values('entry_time').reset_index(drop=True)
    et_ts = pd.to_datetime(df['entry_time']).dt.tz_convert('America/New_York')
    df['et_hour'] = et_ts.dt.hour
    df['et_minute'] = et_ts.dt.minute
    return df

def measure(trade, prices: pd.Series):
    """MFE/MAE veri dalla entry fino a 16:00 ET + tempo al picco MFE."""
    sign = 1 if trade['direction'] == 'long' else -1
    risk = abs(trade['entry'] - trade['stop'])
    fav = adv = 0.0
    t_mfe = None
    last_px = None
    for ts, px in prices.items():
        et = ts - pd.Timedelta(hours=5)
        if et.hour >= 16:
            break
        move = sign * (px - trade['entry'])
        if move > fav:
            fav = move; t_mfe = ts
        if -move > adv:
            adv = -move
        last_px = px
    close_r = sign * (last_px - trade['entry']) / risk if last_px else 0.0
    mins_to_mfe = (t_mfe - pd.to_datetime(trade['entry_time'], utc=True)).total_seconds()/60 if t_mfe is not None else None
    return fav/risk, adv/risk, close_r, mins_to_mfe

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = load_real_entries()
    day_cache, rows = {}, []
    for _, tr in entries.iterrows():
        dstr = tr['date'].replace('-', '')
        if dstr not in day_cache:
            f = DATA_DIR / f'glbx-mdp3-{dstr}.trades.csv'
            df = pd.read_csv(f, usecols=['ts_event', 'price', 'symbol'])
            # FIX CONTAMINAZIONE: i file contengono spread (NQH5-NQM5, prezzi ~200)
            # e altre scadenze. Solo il front contract outright piu' scambiato.
            outright = df[~df['symbol'].str.contains('-', na=False)]
            front = outright['symbol'].value_counts().idxmax()
            df = outright[outright['symbol'] == front]
            df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
            day_cache[dstr] = df.set_index('ts_event')['price']
            print(f"caricato {tr['date']}: {len(df):,} tick ({front})")
        prices = day_cache[dstr]
        prices = prices[prices.index >= pd.to_datetime(tr['entry_time'], utc=True)]
        mfe, mae, close_r, t_mfe = measure(tr, prices)
        rows.append({**tr.to_dict(),
                     'mfe_r_true': round(mfe, 2), 'mae_r_true': round(mae, 2),
                     'close_eod_r': round(close_r, 2),
                     'min_to_mfe': round(t_mfe, 1) if t_mfe else None})
    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / 'mfe_mae_feb.csv', index=False)
    w = out[out['et_hour'] == 10]
    print(f"\n=== {len(out)} trade totali feb | {len(w)} nella fascia 10:00-10:59 ET ===")
    cols = ['date','direction','entry','stop','mfe_r_true','mae_r_true','close_eod_r','legacy_pnl_usd','min_to_mfe']
    print(w[cols].to_string(index=False))
    print("\n--- MFE vero (fascia 10:00): mean/median/max ---")
    print(w['mfe_r_true'].describe()[['mean','50%','max']].round(2).to_string())
    print(f"P(MFE >= 3.5R) = {(w['mfe_r_true']>=3.5).mean():.1%}  |  P(MFE >= 2R) = {(w['mfe_r_true']>=2).mean():.1%}")
    print(f"Legacy PnL reale totale (10am): ${w['legacy_pnl_usd'].sum():.2f}")

if __name__ == '__main__':
    main()
