#!/usr/bin/env python
"""
HONEST RE-SIMULATION — NQ Feb 2025, fascia 10:00-10:59 ET
==========================================================
Prerequisiti di onesta':
- Entry set: SOLO trade realmente registrati nei log JSONL del motore
  (output/backup_suspended_run/agent_memory_backup/trades_log.jsonl
   + agent_memory/feb_w3 + agent_memory/feb_w4). Nessun trade inventato.
- Prezzi: tick-by-tick reali Databento (glbx-mdp3-*.trades.csv).
- Causale: si parte dall'entry_time, mai prima. Stop check PRIMA del target
  sullo stesso tick (conservativo).
- MFE/MAE VERI: tracciati su TUTTA la finestra entry -> EOD (16:00 ET),
  indipendentemente dall'uscita simulata. Serve per valutare il "runner effect".
- Strategia A: all-in target fisso k*R (grid 2.5/3.0/3.5/4.0/4.5), stop iniziale
  invariato, time-stop 11:30 ET.
- Strategia B (legacy): risultato REALE osservato nei log originali
  (partial 50% a 1R + BE + trail), sommando le linee parziali per entry.
- Slippage: 1 tick (0.25 pt) su entry e su stop; commissioni $4/rt incluse nel PnL$.
- Rischio $50/trade => contracts = 50 / (risk_points * $20/pt).
Output: output/honest_resim/trades_honest.csv + summary_honest.json
"""
import sys, json, glob
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd
from pathlib import Path

DATA_DIR = Path('C:/Users/Mauro/Documents/databento-data')
OUT_DIR  = Path('output/honest_resim')
RISK_USD = 50.0
USD_PER_POINT = 20.0          # NQ
TICK = 0.25
SLIP_TICKS = 1
COMM_RT = 4.0
TIME_STOP_ET = (11, 30)
EOD_ET = (16, 0)
TARGET_GRID = [2.5, 3.0, 3.5, 4.0, 4.5]

# ── 1) Entry set reale ─────────────────────────────────────────────
def load_real_entries():
    entries = {}
    # Run originale (feb 3-6) + run successive (feb 17, 24, 25)
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
                continue  # esclude il trade anomalo 2026-01-09 (nessun dato tick)
            key = (et, t['entry'])
            if key not in entries:
                entries[key] = {
                    'entry_time': et,
                    'date': et[:10],
                    'direction': t['direction'].lower(),
                    'entry': float(t['entry']),
                    'stop': float(t['stop']),
                    'legacy_pnl_usd': 0.0,
                }
            entries[key]['legacy_pnl_usd'] += float(t.get('pnl_usd', 0.0))
    df = pd.DataFrame(entries.values()).sort_values('entry_time').reset_index(drop=True)
    # solo fascia 10:00-10:59 ET (Feb = EST = UTC-5)
    et_ts = pd.to_datetime(df['entry_time']).dt.tz_convert('America/New_York')
    df['et_hour'] = et_ts.dt.hour
    return df

# ── 2) Simulazione tick-by-tick ────────────────────────────────────
def simulate(trade, prices: pd.Series):
    """prices: pd.Series price index=ts (UTC), gia' filtrata >= entry_time."""
    direction = trade['direction']
    entry = trade['entry'] + (SLIP_TICKS*TICK if direction == 'long' else -SLIP_TICKS*TICK)
    stop = trade['stop']
    risk = abs(trade['entry'] - stop)
    sign = 1 if direction == 'long' else -1
    risk_usd = risk * USD_PER_POINT

    # MFE/MAE veri su tutta la finestra fino a EOD
    fav, adv = 0.0, 0.0
    results = {}
    exits = {k: None for k in TARGET_GRID}
    et_offset = pd.Timedelta(hours=5)  # Feb: EST

    for ts, px in prices.items():
        et = ts - et_offset
        if et.hour > EOD_ET[0] or (et.hour == EOD_ET[0] and et.minute >= EOD_ET[1]):
            break
        move = sign * (px - entry)
        if move > fav: fav = move
        if -move > adv: adv = -move
        # stop sempre controllato per primo (conservativo)
        stopped = (px <= stop) if direction == 'long' else (px >= stop)
        for k in TARGET_GRID:
            if exits[k] is not None:
                continue
            tgt = entry + sign * k * risk
            hit_tgt = (px >= tgt) if direction == 'long' else (px <= tgt)
            if stopped:
                fill = stop - sign * SLIP_TICKS * TICK
                exits[k] = ('stop', fill, ts)
            elif hit_tgt:
                exits[k] = ('target', tgt, ts)
            elif et.hour > TIME_STOP_ET[0] or (et.hour == TIME_STOP_ET[0] and et.minute >= TIME_STOP_ET[1]):
                exits[k] = ('time_stop', px, ts)

    last_ts, last_px = prices.index[-1], prices.iloc[-1]
    out = {'mfe_r': round(fav / risk, 3), 'mae_r': round(adv / risk, 3)}
    for k in TARGET_GRID:
        reason, fill, ts_exit = exits[k] if exits[k] else ('eod', last_px, last_ts)
        pnl_pts = sign * (fill - entry)
        contracts = max(RISK_USD / risk_usd, 0.01)
        pnl_usd = pnl_pts * USD_PER_POINT * contracts - COMM_RT * contracts
        out[f'k{k}'] = {
            'exit_reason': reason,
            'exit_price': round(fill, 2),
            'ts_exit': str(ts_exit),
            'pnl_usd': round(pnl_usd, 2),
            'r_multiple': round(pnl_pts / risk, 2),
        }
    return out

# ── 3) Main ────────────────────────────────────────────────────────
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    entries = load_real_entries()
    print(f"Entry reali caricate (tutto feb): {len(entries)}")
    in_window = entries[entries['et_hour'] == 10]
    print(f"Di cui nella fascia 10:00-10:59 ET: {len(in_window)}")

    day_cache = {}
    rows = []
    for _, tr in entries.iterrows():
        dstr = tr['date'].replace('-', '')
        if dstr not in day_cache:
            f = DATA_DIR / f'glbx-mdp3-{dstr}.trades.csv'
            if not f.exists():
                print(f"  !! dati mancanti per {tr['date']} — trade saltato")
                day_cache[dstr] = None
                continue
            df = pd.read_csv(f, usecols=['ts_event', 'price', 'symbol'])
            df = df[~df['symbol'].str.contains('-', na=False)]
            front = df['symbol'].value_counts().idxmax()
            df = df[df['symbol'] == front]
            df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
            day_cache[dstr] = df.set_index('ts_event')['price']
            print(f"  caricato {tr['date']}: {len(df):,} tick")
        prices_all = day_cache[dstr]
        if prices_all is None:
            continue
        prices = prices_all[prices_all.index >= pd.to_datetime(tr['entry_time'], utc=True)]
        if len(prices) < 10:
            print(f"  !! pochi tick dopo entry {tr['entry_time']}")
            continue
        sim = simulate(tr, prices)
        row = {
            'entry_time': tr['entry_time'], 'date': tr['date'],
            'direction': tr['direction'], 'entry': tr['entry'], 'stop': tr['stop'],
            'risk_pts': round(abs(tr['entry'] - tr['stop']), 2),
            'in_10am_window': bool(tr['et_hour'] == 10),
            'legacy_pnl_usd_real': round(tr['legacy_pnl_usd'], 2),
            'mfe_r_true': sim['mfe_r'], 'mae_r_true': sim['mae_r'],
        }
        for k in TARGET_GRID:
            r = sim[f'k{k}']
            row[f'k{k}_exit'] = r['exit_reason']
            row[f'k{k}_pnl_usd'] = r['pnl_usd']
            row[f'k{k}_r'] = r['r_multiple']
        rows.append(row)

    out = pd.DataFrame(rows)
    out.to_csv(OUT_DIR / 'trades_honest.csv', index=False)

    # ── 4) Summary (solo finestra 10:00 ET) ──
    w = out[out['in_10am_window']]
    summary = {'n_trades_total_feb': len(out), 'n_trades_10am_window': len(w), 'strategies': {}}
    for k in TARGET_GRID:
        pnl = w[f'k{k}_pnl_usd']
        wins = (pnl > 0).sum()
        gp = pnl[pnl > 0].sum(); gl = -pnl[pnl < 0].sum()
        summary['strategies'][f'fixed_{k}R'] = {
            'n': len(w), 'wins': int(wins), 'win_rate': round(wins / max(len(w),1), 3),
            'pnl_usd': round(pnl.sum(), 2),
            'profit_factor': round(gp / gl, 2) if gl > 0 else None,
        }
    lp = w['legacy_pnl_usd_real']
    lw = (lp > 0).sum()
    gp = lp[lp > 0].sum(); gl = -lp[lp < 0].sum()
    summary['strategies']['legacy_partial_trail_REAL'] = {
        'n': len(w), 'wins': int(lw), 'win_rate': round(lw / max(len(w),1), 3),
        'pnl_usd': round(lp.sum(), 2),
        'profit_factor': round(gp / gl, 2) if gl > 0 else None,
    }
    summary['mfe_true_stats_10am'] = {
        'mean': round(w['mfe_r_true'].mean(), 2),
        'median': round(w['mfe_r_true'].median(), 2),
        'max': round(w['mfe_r_true'].max(), 2),
        'pct_ge_3_5R': round((w['mfe_r_true'] >= 3.5).mean(), 3),
    }
    with open(OUT_DIR / 'summary_honest.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
