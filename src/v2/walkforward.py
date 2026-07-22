"""V2.0 — Walk-forward validation.

REGOLE ANTI-OVERFITTING:
1. Ogni parametro HYPOTHESIS (ib_extension_k, soglia calibrazione) è fittato
   SOLO su train e applicato congelato a test.
2. Trade intra-day, nessuna posizione overnight → nessun purge necessario;
   embargo di 1 giorno tra train e test per prudenza (statistiche TOD).
3. Il report finale usa SOLO il concatenamento dei test (mai l'in-sample).
4. Bootstrap CI sul PF: se CI_5% < 1.3 → NON TRADABLE, punto.
5. Sensitivity: intrabar stop_first/target_first, slippage ±50%.
   Un edge che muore con stop_first o +1 tick di slippage non è un edge.
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from statistics import median

from .engine import BacktestEngine
from .config import Config
from .calibration import ConfidenceCalibrator
from .policy_llm import LLMPolicy


@dataclass
class Fold:
    train_dates: list
    test_dates: list


def iter_folds(dates: list, train_n: int = 40, test_n: int = 10,
               step: int = 10, embargo: int = 1) -> list:
    folds, i = [], 0
    while i + train_n + embargo + test_n <= len(dates):
        folds.append(Fold(
            train_dates=dates[i:i + train_n],
            test_dates=dates[i + train_n + embargo: i + train_n + embargo + test_n]))
        i += step
    return folds


def estimate_ib_extension_k(train_days_data: dict, cfg: Config) -> float:
    """Stima k del Protection Level da breakout IB validi NEI SOLI dati train.
    Per ogni breakout (body close fuori IB + volume >= 4k + delta allineato):
    MFE entro 90 min in multipli di IB range. k = mediana. Causale: solo train."""
    from .state import SessionState
    ratios = []
    for date, (day_ctx, bars) in train_days_data.items():
        state = SessionState(day_ctx, cfg)
        broke = None
        for j, bar in enumerate(bars):
            state.update(bar)
            if broke is None and state.ib_complete and state.ib_range > 0:
                if bar.close > state.ib_high and bar.delta > 0 and bar.volume >= cfg.detection.participation_m1_trend:
                    broke = ("up", j, state.ib_high, state.ib_range)
                elif bar.close < state.ib_low and bar.delta < 0 and bar.volume >= cfg.detection.participation_m1_trend:
                    broke = ("dn", j, state.ib_low, state.ib_range)
            elif broke is not None:
                direction, j0, edge, ib_r = broke
                if j - j0 > 90:
                    break
        if broke is not None:
            direction, j0, edge, ib_r = broke
            post = bars[j0: j0 + 90]
            if direction == "up" and post:
                mfe = max(b.high for b in post) - edge
            elif post:
                mfe = edge - min(b.low for b in post)
            else:
                continue
            if ib_r > 0:
                ratios.append(mfe / ib_r)
    return round(median(ratios), 2) if ratios else 1.0


def compute_metrics(trades: list) -> dict:
    if not trades:
        return {"n": 0, "pf": 0.0, "wr": 0.0, "max_dd": 0.0, "avg_r": 0.0, "net": 0.0}
    wins = [t for t in trades if t.pnl_usd > 0]
    losses = [t for t in trades if t.pnl_usd <= 0]
    gp = sum(t.pnl_usd for t in wins)
    gl = abs(sum(t.pnl_usd for t in losses))
    eq, peak, max_dd = 0.0, 0.0, 0.0
    for t in trades:
        eq += t.pnl_usd
        peak = max(peak, eq)
        max_dd = max(max_dd, peak - eq)
    return {
        "n": len(trades),
        "pf": round(gp / gl, 2) if gl > 0 else float("inf"),
        "wr": round(len(wins) / len(trades), 3),
        "max_dd": round(max_dd, 2),
        "avg_r": round(sum(t.r_multiple for t in trades) / len(trades), 2),
        "net": round(sum(t.pnl_usd for t in trades), 2),
    }


def bootstrap_pf(trades: list, n_iter: int = 5000, seed: int = 42) -> tuple:
    rng = random.Random(seed)
    pnls = [t.pnl_usd for t in trades]
    if len(pnls) < 10:
        return 0.0, 0.0
    pfs = []
    for _ in range(n_iter):
        sample = [rng.choice(pnls) for _ in pnls]
        gp = sum(x for x in sample if x > 0)
        gl = abs(sum(x for x in sample if x <= 0))
        pfs.append(gp / gl if gl > 0 else 99.0)
    pfs.sort()
    return round(pfs[int(0.05 * n_iter)], 2), round(pfs[int(0.95 * n_iter)], 2)


def run_walkforward(dates: list, load_day_data, cfg: Config,
                    use_llm: bool = False) -> dict:
    """load_day_data(date) -> (DayContext, bars). Ritorna report OOS completo."""
    folds = iter_folds(dates)
    all_test_trades = []
    fold_reports = []

    for fi, fold in enumerate(folds):
        # ── FIT SOLO SU TRAIN ──
        train_data = {d: load_day_data(d) for d in fold.train_dates}
        k = estimate_ib_extension_k(train_data, cfg)

        cal = ConfidenceCalibrator(min_trades=cfg.llm.veto_only_until_n_trades)
        llm = None
        if use_llm:
            llm = LLMPolicy(cfg, cal)
            # calibrazione fittata su trade TRAIN (con LLM attivo)
            train_trades = []
            eng_tr = BacktestEngine(cfg, llm_policy=llm, ib_extension_k=k)
            for d in fold.train_dates:
                day_ctx, bars = train_data[d]
                eng_tr.run_day(day_ctx, bars)
            for r in [eng_tr]:
                pass
            # raccogli conf/win dai trade train per il fit isotonico
            confs, wins = [], []
            for d in fold.train_dates:
                day_ctx, bars = train_data[d]
                res = eng_tr.run_day(day_ctx, bars)
                for t in res.trades:
                    if t.confidence > 0:
                        confs.append(t.confidence)
                        wins.append(t.pnl_usd > 0)
            cal.fit(confs, wins)

        # ── TEST CON PARAMETRI CONGELATI ──
        eng = BacktestEngine(cfg, llm_policy=llm, ib_extension_k=k)
        fold_trades = []
        for d in fold.test_dates:
            day_ctx, bars = load_day_data(d)
            res = eng.run_day(day_ctx, bars)
            fold_trades.extend(res.trades)

        m = compute_metrics(fold_trades)
        fold_reports.append({"fold": fi, "k_ib_ext": k, "test_metrics": m,
                             "test_dates": (fold.test_dates[0], fold.test_dates[-1])})
        all_test_trades.extend(fold_trades)
        print(f"  [WF] fold {fi}: k={k} | test n={m['n']} PF={m['pf']} net=${m['net']}")

    overall = compute_metrics(all_test_trades)
    ci_lo, ci_hi = bootstrap_pf(all_test_trades)

    # ── SENSITIVITY (sul test completo, parametri congelati al valore mediano) ──
    sens = {}
    k_med = median([f["k_ib_ext"] for f in fold_reports]) if fold_reports else 1.0
    for policy in ("stop_first", "target_first"):
        for slip in (1.0, 1.5):
            eng = BacktestEngine(cfg, llm_policy=None, ib_extension_k=k_med,
                                 intrabar_policy=policy, slippage_mult=slip)
            trades = []
            for fold in folds:
                for d in fold.test_dates:
                    day_ctx, bars = load_day_data(d)
                    trades.extend(eng.run_day(day_ctx, bars).trades)
            sens[f"{policy}/slip{slip}"] = compute_metrics(trades)

    return {
        "overall_oos": overall,
        "pf_bootstrap_ci": (ci_lo, ci_hi),
        "folds": fold_reports,
        "sensitivity": sens,
        "verdict": ("TRADABLE" if overall["pf"] >= 1.5 and ci_lo >= 1.3
                    and overall["max_dd"] <= cfg.risk.daily_loss_limit_usd * 3
                    else "NOT TRADABLE — edge non dimostrato OOS"),
    }
