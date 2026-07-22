"""
NQ Backtest v2.0 — Entry point

Uso:
    python scripts/v2/run_backtest_v2.py --no-llm              # solo deterministico (veloce)
    python scripts/v2/run_backtest_v2.py --days 30             # ultimi 30 giorni
    python scripts/v2/run_backtest_v2.py --date 2025-04-30     # giorno singolo
    python scripts/v2/run_backtest_v2.py --dates 2025-01-01 2025-06-30  # range
    python scripts/v2/run_backtest_v2.py --walk-forward        # validazione OOS

Variabili d'ambiente:
    OPENROUTER_API_KEY   richiesta se --no-llm NON è specificato
    NQ_TRADES_DIR        override del percorso dati (default: C:/Users/Mauro/Documents/databento-data)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.v2.config import Config
from src.v2.engine import BacktestEngine
from src.v2.loader import DayLoader
from src.v2.walkforward import compute_metrics, bootstrap_pf

DEFAULT_TRADES_DIR = r"C:\Users\Mauro\Documents\databento-data"
DEFAULT_OUTPUT_DIR = BASE_DIR / "output"


def parse_args():
    p = argparse.ArgumentParser(description="NQ Backtest v2.0")
    p.add_argument("--no-llm", action="store_true", help="Skip LLM calls (deterministico puro)")
    p.add_argument("--days", type=int, default=0, help="Ultimi N giorni (0 = tutti)")
    p.add_argument("--date", type=str, help="Giorno singolo YYYY-MM-DD")
    p.add_argument("--dates", type=str, nargs=2, metavar=("FROM", "TO"),
                   help="Range di date YYYY-MM-DD YYYY-MM-DD")
    p.add_argument("--walk-forward", action="store_true", help="Esegui walk-forward validation")
    p.add_argument("--trades-dir", type=str,
                   default=os.environ.get("NQ_TRADES_DIR", DEFAULT_TRADES_DIR))
    p.add_argument("--config", type=str, default=None, help="Path config JSON opzionale")
    p.add_argument("--quiet", action="store_true", help="Meno output")
    return p.parse_args()


def select_dates(loader: DayLoader, args) -> list[str]:
    all_dates = loader.list_dates()
    if not all_dates:
        print(f"[ERROR] Nessun file .trades.csv trovato in: {loader.trades_dir}")
        sys.exit(1)

    if args.date:
        return [args.date]

    if args.dates:
        from_d = date.fromisoformat(args.dates[0])
        to_d   = date.fromisoformat(args.dates[1])
        return [d for d in all_dates if from_d.isoformat() <= d <= to_d.isoformat()]

    if args.days and args.days > 0:
        cutoff = (date.today() - timedelta(days=args.days)).isoformat()
        return [d for d in all_dates if d >= cutoff]

    return all_dates


def run_backtest(dates: list[str], loader: DayLoader, cfg: Config,
                 no_llm: bool, quiet: bool) -> list:
    """Esegue il backtest su una lista di date. Ritorna tutti i ClosedTrade."""

    llm_policy = None
    if not no_llm and cfg.llm.enabled:
        try:
            from src.v2.calibration import ConfidenceCalibrator
            from src.v2.policy_llm import LLMPolicy
            cal = ConfidenceCalibrator(min_trades=cfg.llm.veto_only_until_n_trades)
            llm_policy = LLMPolicy(cfg, cal)
        except Exception as e:
            print(f"[WARN] LLM non disponibile: {e} — procedo senza")

    engine = BacktestEngine(cfg, llm_policy=llm_policy)

    all_trades = []
    skipped = 0

    for date_str in dates:
        try:
            day_ctx, bars = loader.load(date_str)
        except Exception as e:
            if not quiet:
                print(f"  [SKIP] {date_str}: errore loader — {e}")
            skipped += 1
            continue

        if not bars:
            if not quiet:
                print(f"  [SKIP] {date_str}: nessuna barra RTH")
            skipped += 1
            continue

        # Salta Venerdì (FABIO: rule_fabio_avoid_times)
        if cfg.session.skip_friday:
            d = date.fromisoformat(date_str)
            if d.weekday() == 4:   # venerdì
                if not quiet:
                    print(f"  [SKIP] {date_str}: Friday (rule_fabio_avoid_times)")
                skipped += 1
                continue

        try:
            result = engine.run_day(day_ctx, bars)
        except Exception as e:
            print(f"  [ERROR] {date_str}: {e}")
            continue

        if not quiet:
            n_t = len(result.trades)
            pnl = sum(t.pnl_usd for t in result.trades)
            print(f"  {date_str} | segnali={result.n_signals:2d} | "
                  f"trade={n_t} | PnL=${pnl:+,.0f} | "
                  f"GEX={day_ctx.gex_regime[:3].upper()}")

        all_trades.extend(result.trades)

    print(f"\n[loader] Date: {len(dates)} | Skippate: {skipped} | "
          f"Giorni tradati: {len(dates)-skipped}")
    return all_trades


def print_report(trades: list, label: str = "REPORT") -> None:
    if not trades:
        print(f"\n[{label}] Nessun trade.")
        return

    m = compute_metrics(trades)
    pf_med, pf_5pct = bootstrap_pf(trades)

    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    print(f"  Trade totali  : {m['n']}")
    print(f"  Win rate      : {m['wr']*100:.1f}%")
    print(f"  Profit Factor : {m['pf']:.2f}  [bootstrap CI 5%: {pf_5pct:.2f}]")
    print(f"  Avg R         : {m['avg_r']:.2f}R")
    print(f"  Max DD        : ${m['max_dd']:,.0f}")
    print(f"  Net PnL       : ${m['net']:,.0f}")

    # Breakdown per setup
    by_setup: dict = {}
    for t in trades:
        s = t.setup
        by_setup.setdefault(s, []).append(t)
    print(f"\n  Per setup:")
    for setup, ts in sorted(by_setup.items()):
        sm = compute_metrics(ts)
        print(f"    {setup:25s} n={sm['n']:3d} WR={sm['wr']*100:4.0f}% PF={sm['pf']:.2f}")

    # Breakdown per GEX regime
    by_gex: dict = {}
    for t in trades:
        g = getattr(t, "gex_regime", "unknown")
        by_gex.setdefault(g, []).append(t)
    if len(by_gex) > 1:
        print(f"\n  Per GEX regime:")
        for regime, ts in sorted(by_gex.items()):
            sm = compute_metrics(ts)
            print(f"    {regime:12s} n={sm['n']:3d} WR={sm['wr']*100:4.0f}% PF={sm['pf']:.2f}")

    print(f"\n  Verdetto: ", end="")
    if m['pf'] >= 1.5 and pf_5pct >= 1.3 and m['max_dd'] <= 7500:
        print("TRADABLE ✓")
    else:
        reasons = []
        if m['pf'] < 1.5:   reasons.append(f"PF {m['pf']:.2f}<1.5")
        if pf_5pct < 1.3:   reasons.append(f"CI5% {pf_5pct:.2f}<1.3")
        if m['max_dd'] > 7500: reasons.append(f"DD ${m['max_dd']:,.0f}>$7.500")
        print(f"NOT TRADABLE ({', '.join(reasons)})")
    print(f"{'='*55}")


def save_trades(trades: list, output_dir: Path, label: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = output_dir / f"trades_v2_{label}_{ts}.json"
    data = []
    for t in trades:
        d = {
            "date": t.date,
            "setup": t.setup,
            "direction": t.direction.value,
            "entry": t.entry,
            "exit_price": t.exit_price,
            "stop_initial": t.stop_initial,
            "target1": t.target1,
            "contracts": t.contracts,
            "pnl_usd": round(t.pnl_usd, 2),
            "r_multiple": round(t.r_multiple, 3),
            "exit_reason": t.exit_reason,
            "ts_entry": t.ts_entry.isoformat(),
            "ts_exit": t.ts_exit.isoformat(),
            "confidence": t.confidence,
            "gex_regime": t.gex_regime,
        }
        data.append(d)
    out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"\n  Trade salvati: {out}")


def main():
    args = parse_args()
    cfg  = Config.load(args.config)

    if args.no_llm:
        from dataclasses import replace
        cfg = Config(
            instrument=cfg.instrument,
            session=cfg.session,
            risk=cfg.risk,
            detection=cfg.detection,
            gex=cfg.gex,
            llm=type(cfg.llm)(
                **{**cfg.llm.__dict__, "enabled": False}
            ) if hasattr(cfg.llm, "__dict__") else cfg.llm,
        )

    print("=" * 55)
    print("  NQ BACKTEST v2.0")
    print(f"  Trades dir: {args.trades_dir}")
    print(f"  LLM: {'OFF' if args.no_llm else cfg.llm.model}")
    print("=" * 55)

    loader = DayLoader(trades_dir=args.trades_dir)
    dates  = select_dates(loader, args)

    if not dates:
        print("[ERROR] Nessuna data selezionata.")
        sys.exit(1)

    print(f"\nDate selezionate: {len(dates)} ({dates[0]} → {dates[-1]})\n")

    if args.walk_forward:
        # Walk-forward: usa walkforward.py di Kimi K3
        from src.v2.walkforward import iter_folds
        folds = iter_folds(dates, train_n=40, test_n=10, step=10)
        if not folds:
            print("[ERROR] Dati insufficienti per walk-forward (min 51 giorni)")
            sys.exit(1)
        print(f"Walk-forward: {len(folds)} fold (train=40, test=10, step=10)\n")
        oos_trades = []
        for i, fold in enumerate(folds):
            print(f"  Fold {i+1}/{len(folds)}: train {fold.train_dates[0]}→{fold.train_dates[-1]}")
            test_t = run_backtest(fold.test_dates, loader, cfg, args.no_llm, quiet=True)
            oos_trades.extend(test_t)
            print(f"            test  {fold.test_dates[0]}→{fold.test_dates[-1]}: "
                  f"{len(test_t)} trade")
        print_report(oos_trades, label="WALK-FORWARD OOS")
        save_trades(oos_trades, DEFAULT_OUTPUT_DIR, "wf_oos")
    else:
        trades = run_backtest(dates, loader, cfg, args.no_llm, quiet=args.quiet)
        print_report(trades, label="FULL SAMPLE")
        if trades:
            save_trades(trades, DEFAULT_OUTPUT_DIR, "full")


if __name__ == "__main__":
    main()
