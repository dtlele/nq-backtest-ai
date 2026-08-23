#!/usr/bin/env python3
"""
download_mbo_data.py — Databento MBO/TBBO downloader per DeepPrint Pro.

Scarica dati TBBO (trades + BBO) da Databento per NQ futures front-month,
li salva in cache_ticks/YYYYMMDD.parquet, e valida incrociata con cache_ohlc/.

⚠️  Costo API: Databento addebita per byte. Usa --confirm-batch per batch > 1 giorno.
⚠️  Prima esegui: pip install databento pandas pyarrow

Usage:
    python scripts/download_mbo_data.py --date 2025-01-02
    python scripts/download_mbo_data.py --all --confirm-batch
    python scripts/download_mbo_data.py --date 2025-01-02 --dry-run
    python scripts/download_mbo_data.py --validate 2025-01-02

Config:
    env DATABENTO_API_KEY       (obbligatorio per download)
    env NQ_CACHE_OHLC_DIR       (default: cache_ohlc/)
    env NQ_CACHE_TICKS_DIR      (default: cache_ticks/)
"""
import argparse
import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

CACHE_OHLC_DIR  = Path(os.environ.get('NQ_CACHE_OHLC_DIR',  _PROJECT_ROOT / 'cache_ohlc'))
CACHE_TICKS_DIR = Path(os.environ.get('NQ_CACHE_TICKS_DIR', _PROJECT_ROOT / 'cache_ticks'))
TICK_SIZE = 0.25
MAX_TICK_ERROR = 2


def _get_available_ohlc_dates() -> list:
    dates = []
    for f in sorted(CACHE_OHLC_DIR.glob('*.csv')):
        stem = f.stem
        if len(stem) == 8 and stem.isdigit():
            dates.append(f"{stem[:4]}-{stem[4:6]}-{stem[6:8]}")
    return dates


def _ohlc_date_to_path(date: str) -> Path:
    return CACHE_OHLC_DIR / f"{date.replace('-', '')}.csv"


def download_date(date: str, dry_run: bool = False) -> Path | None:
    """Scarica un giorno di dati TBBO da Databento. Salva in cache_ticks/YYYYMMDD.parquet."""
    api_key = os.environ.get('DATABENTO_API_KEY', '')
    if not api_key:
        print("[ERROR] DATABENTO_API_KEY non impostata.")
        return None

    date_str = date.replace('-', '')
    out_path = CACHE_TICKS_DIR / f"{date_str}.parquet"

    if out_path.exists() and not dry_run:
        print(f"[SKIP] {out_path} esiste già. Usa --force per riscaricare.")
        return out_path

    if dry_run:
        print(f"[DRY RUN] Scaricherei TBBO per {date} → {out_path}")
        return out_path

    CACHE_TICKS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        import databento as db
    except ImportError:
        print("[ERROR] 'databento' non installato. Esegui: pip install databento")
        return None

    print(f"[DOWNLOAD] {date} — Connessione a Databento...")
    client = db.Historical(api_key)
    start = pd.Timestamp(date, tz='America/New_York').strftime('%Y-%m-%dT09:00:00')
    end   = pd.Timestamp(date, tz='America/New_York').strftime('%Y-%m-%dT17:00:00')

    try:
        df = client.timeseries.get_range(
            dataset='GLBX.MDP3', schema='tbbo', symbol='NQ.c.0',
            start=start, end=end,
        ).to_df()
    except Exception as e:
        print(f"[ERROR] Databento download fallito per {date}: {e}")
        return None

    if df.empty:
        print(f"[WARN] Nessun dato per {date}")
        return None

    required = {'ts_event', 'action', 'side', 'price', 'size'}
    missing = required - set(df.columns)
    if missing:
        print(f"[ERROR] Colonne mancanti: {missing}")
        return None

    out = df[list(required)].copy()
    out['ts_event'] = pd.to_datetime(out['ts_event'], utc=True)
    out.to_parquet(out_path, index=False, compression='zstd')
    n = len(out)
    print(f"[OK] {date}: {n:,} righe → {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")
    return out_path


def validate_cross(date: str, verbose: bool = True) -> dict:
    """Validazione incrociata tick→M1 vs cache_ohlc."""
    date_str = date.replace('-', '')
    tick_path = CACHE_TICKS_DIR / f"{date_str}.parquet"
    ohlc_path = _ohlc_date_to_path(date)
    result = {'date': date, 'max_diff_open': 0, 'max_diff_high': 0,
              'max_diff_low': 0, 'max_diff_close': 0, 'max_diff_volume': 0,
              'n_bars': 0, 'n_mismatch': 0, 'errors': []}

    if not tick_path.exists():
        result['errors'].append(f"Tick file non trovato: {tick_path}")
        return result
    if not ohlc_path.exists():
        result['errors'].append(f"OHLC file non trovato: {ohlc_path}")
        return result

    df = pd.read_parquet(tick_path)
    df = df[df['action'] == 'T'].copy()
    df['ts_event'] = pd.to_datetime(df['ts_event'], utc=True)
    df = df.set_index('ts_event').sort_index()
    df['buy_vol'] = np.where(df['side'] == 'A', df['size'], 0)
    df['sell_vol'] = np.where(df['side'] == 'B', df['size'], 0)
    df['dollar'] = df['price'] * df['size']
    g = df.resample('1min')
    ohlcv = g['price'].ohlc()
    vol = g['size'].sum()
    result['n_bars'] = len(ohlcv)

    ref = pd.read_csv(ohlc_path)
    ref['timestamp'] = pd.to_datetime(ref['timestamp'], utc=True)
    ref = ref.set_index('timestamp').sort_index()
    common = ohlcv.index.intersection(ref.index)
    if len(common) == 0:
        result['errors'].append("Nessun timestamp comune")
        return result

    for col, oc in [('open', 'open'), ('high', 'high'), ('low', 'low'), ('close', 'close')]:
        d = (ohlcv.loc[common, col] - ref.loc[common, oc]).abs()
        result[f'max_diff_{col}'] = round(d.max() if not d.empty else 0, 2)

    vd = (vol.loc[common] - ref.loc[common, 'volume']).abs() if 'volume' in ref.columns else pd.Series([0])
    result['max_diff_volume'] = int(vd.max()) if not vd.empty else 0

    h_ok = result['max_diff_high'] <= MAX_TICK_ERROR * TICK_SIZE
    l_ok = result['max_diff_low'] <= MAX_TICK_ERROR * TICK_SIZE
    result['n_mismatch'] = (0 if h_ok else 1) + (0 if l_ok else 1)

    if verbose:
        print(f"\n=== Validazione: {date} ===")
        print(f"  Barre: {len(common)}")
        print(f"  Max ΔO: {result['max_diff_open']:.2f}  ΔH: {result['max_diff_high']:.2f} {'⚠️' if not h_ok else '✅'}  ΔL: {result['max_diff_low']:.2f} {'⚠️' if not l_ok else '✅'}  ΔC: {result['max_diff_close']:.2f}")
        if result['errors']:
            for e in result['errors']:
                print(f"  ⚠️  {e}")
    return result


def write_validation_report(results: list[dict]):
    report_path = CACHE_TICKS_DIR / '_validation_report.md'
    passed = sum(1 for r in results if r['n_mismatch'] == 0 and not r['errors'])
    lines = [
        f"# Validazione Incrociata Ticks vs OHLC\n\n",
        f"Generato: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n",
        f"## Riepilogo\n\n",
        f"- Date validate: {len(results)}\n",
        f"- Passate: {passed}\n",
        f"- Fallite: {len(results) - passed}\n",
        f"- Tolleranza: ±{MAX_TICK_ERROR} tick su H/L\n\n",
        f"| Data | Barre | Max ΔO | Max ΔH | Max ΔL | Max ΔC | Esito |\n",
        f"|------|-------|--------|--------|--------|--------|-------|\n",
    ]
    for r in results:
        ok = r['n_mismatch'] == 0 and not r['errors']
        err = '; '.join(r['errors'])
        lines.append(
            f"| {r['date']} | {r['n_bars']} | "
            f"{r['max_diff_open']:.2f} | {r['max_diff_high']:.2f} | "
            f"{r['max_diff_low']:.2f} | {r['max_diff_close']:.2f} | "
            f"{'✅' if ok else '⚠️'} {err} |\n"
        )
    report_path.write_text(''.join(lines), encoding='utf-8')
    print(f"[REPORT] {report_path}")


def main():
    parser = argparse.ArgumentParser(description='Databento TBBO downloader')
    parser.add_argument('--date', type=str, help='Data YYYY-MM-DD')
    parser.add_argument('--all', action='store_true', help='Scarica tutte le date cache_ohlc')
    parser.add_argument('--confirm-batch', action='store_true', help='Conferma batch')
    parser.add_argument('--dry-run', action='store_true', help='Solo simulazione')
    parser.add_argument('--force', action='store_true', help='Riscarica se esiste')
    parser.add_argument('--validate', type=str, help='Solo validazione YYYY-MM-DD')
    parser.add_argument('--validate-all', action='store_true', help='Valida tutte in cache_ticks/')
    args = parser.parse_args()

    if args.validate:
        write_validation_report([validate_cross(args.validate, verbose=True)])
        return

    if args.validate_all:
        results = []
        for f in sorted(CACHE_TICKS_DIR.glob('*.parquet')):
            ds = f"{f.stem[:4]}-{f.stem[4:6]}-{f.stem[6:8]}"
            results.append(validate_cross(ds, verbose=False))
        write_validation_report(results)
        for r in results:
            ok = r['n_mismatch'] == 0 and not r['errors']
            print(f"  {r['date']}: {'✅' if ok else '⚠️'}  ΔH={r['max_diff_high']:.2f}  ΔL={r['max_diff_low']:.2f}")
        return

    dates = []
    if args.date:
        dates = [args.date]
    elif args.all:
        dates = _get_available_ohlc_dates()
        print(f"Trovate {len(dates)} date in cache_ohlc/")
    else:
        parser.print_help()
        return

    if not args.force:
        todo = []
        for d in dates:
            p = CACHE_TICKS_DIR / f"{d.replace('-', '')}.parquet"
            if not p.exists():
                todo.append(d)
            else:
                print(f"[SKIP] {d} — già scaricato")
        dates = todo

    if not dates:
        print("[OK] Tutte già scaricate.")
        return

    if len(dates) > 1 and not args.confirm_batch and not args.dry_run:
        print(f"⚠️  {len(dates)} giorni da scaricare (~${len(dates)*0.3:.1f} stima).")
        if input("Procedere? (s/N): ").lower() != 's':
            print("Annullato.")
            return

    results = []
    for d in dates:
        p = download_date(d, dry_run=args.dry_run)
        if p and not args.dry_run:
            r = validate_cross(d, verbose=False)
            results.append(r)
            ok = r['n_mismatch'] == 0 and not r['errors']
            print(f"  {d}: {'✅' if ok else '⚠️'}  ΔH={r['max_diff_high']:.2f}  ΔL={r['max_diff_low']:.2f}")

    if results:
        write_validation_report(results)

    if args.dry_run:
        print(f"[DRY RUN] {len(dates)} date simulate. Nessun dato scaricato.")


if __name__ == '__main__':
    main()