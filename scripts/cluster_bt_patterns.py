"""
cluster_bt_patterns.py
======================
Hybrid analysis on enriched bt_sequences.json:
  1. Flatten each sequence into a numeric feature vector
  2. K-Means clustering (find similar institutional patterns)
  3. Decision Tree (find rules that predict profitable excursions)
  4. Print report + save cluster_report.json for Graphify labeling

Usage:
    python scripts/cluster_bt_patterns.py
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent.parent
SEQ_FILE = BASE / "knowledge" / "trader_lessons_graph" / "graphify-out" / "sequences" / "bt_sequences.json"
OUT_FILE  = BASE / "knowledge" / "trader_lessons_graph" / "graphify-out" / "sequences" / "cluster_report.json"

# ── Encoding maps ─────────────────────────────────────────────────────────────
SIDE_MAP      = {"B": 1, "A": -1}
POS_MAP       = {"above": 1, "at": 0, "below": -1}
IB_MAP        = {"above_ib": 2, "ib_upper_half": 1, "ib_lower_half": -1, "below_ib": -2}
IB_EXT_MAP    = {"above": 1, "inside": 0, "below": -1, "unknown": 0}
PHASE_MAP     = {"pre_market": 0, "ib_forming": 1, "morning": 2,
                 "midday": 3, "afternoon": 4, "close": 5}

def encode_step(step: dict, step_idx: int, prefix: str = "") -> dict:
    p = f"{prefix}s{step_idx}_"
    return {
        p+"volume":          step.get("volume", 0),
        p+"side":            SIDE_MAP.get(step.get("dominant_side", "B"), 0),
        p+"consec":          step.get("consecutive_same_side", 1),
        p+"elapsed_mins":    step.get("elapsed_mins", 0),
        p+"price_change":    step.get("price_change", 0),
        p+"cum_delta":       step.get("cumulative_delta", 0),
        p+"max_exc":         step.get("max_excursion", 0) or 0,
        p+"min_exc":         step.get("min_excursion", 0) or 0,
        p+"session_cvd":     step.get("session_cvd", 0),
        p+"divergence":      int(step.get("delta_divergence", False)),
        p+"mins_since_open": step.get("mins_since_open", 0),
        p+"phase":           PHASE_MAP.get(step.get("session_phase", "morning"), 2),
        p+"vs_vwap":         POS_MAP.get(step.get("price_vs_vwap"), 0),
        p+"vwap_ticks":      step.get("vwap_ticks") or 0,
        p+"vs_poc":          POS_MAP.get(step.get("price_vs_poc"), 0),
        p+"poc_ticks":       step.get("poc_ticks") or 0,
        p+"vs_val":          POS_MAP.get(step.get("price_vs_val"), 0),
        p+"vs_vah":          POS_MAP.get(step.get("price_vs_vah"), 0),
        p+"ib_pos":          IB_MAP.get(step.get("ib_position"), 0),
        p+"ib_ext":          IB_EXT_MAP.get(step.get("ib_ext_side"), 0),
        p+"vs_prev_close":   POS_MAP.get(step.get("price_vs_prev_close"), 0),
        p+"vs_prev_poc":     POS_MAP.get(step.get("price_vs_prev_poc"), 0),
    }

PATTERN_MAP = {
    "accumulation_breakup":    3,
    "distribution_breakdown": -3,
    "trending_up":             2,
    "trending_down":          -2,
    "reversal_buy":            1,
    "reversal_sell":          -1,
    "failed_reversal":         0,
    "chop":                    0,
    "unknown":                 0,
}
GAP_MAP    = {"narrowing": -1, "stable": 0, "widening": 1}
VOL_MAP    = {"decreasing": -1, "stable": 0, "increasing": 1}
PROX_MAP   = {"close": 0, "medium": 1, "far": 2}

def flatten_sequence(seq: dict) -> dict | None:
    steps = seq.get("steps", [])
    if len(steps) < 2:
        return None
    row = {
        "seq_id":       seq["sequence_id"],
        "date":         seq["date"],
        "start_time":   seq.get("start_time", ""),
        "target_delta": seq["target_price_delta"],
        "target_mins":  seq["target_time_delta_mins"],
        "outcome":      ("long" if seq["is_profitable_long"]
                         else "short" if seq["is_profitable_short"]
                         else "neutral"),
        "abs_excursion": abs(seq["target_price_delta"]),
        # Sequence-level pattern features
        "seq_pattern":        PATTERN_MAP.get(seq.get("seq_pattern", "chop"), 0),
        "seq_all_same_side":  int(seq.get("seq_all_same_side", False)),
        "seq_gap_trend":      GAP_MAP.get(seq.get("seq_gap_trend", "stable"), 0),
        "seq_price_accel":    seq.get("seq_price_accel", 0) or 0,
        "seq_vol_trend":      VOL_MAP.get(seq.get("seq_vol_trend", "stable"), 0),
    }
    for i, step in enumerate(steps):
        row.update(encode_step(step, i))
        row[f"s{i}_proximity"]      = PROX_MAP.get(step.get("node_proximity"), 1)
        row[f"s{i}_dir_consistent"] = int(step.get("direction_consistent") or False)
    return row

def main():
    if not SEQ_FILE.exists():
        print(f"ERROR: {SEQ_FILE} not found. Run extract_bt_sequences.py first.")
        sys.exit(1)

    with open(SEQ_FILE, encoding="utf-8") as f:
        sequences = json.load(f)

    if not sequences:
        print("ERROR: bt_sequences.json is empty.")
        sys.exit(1)

    print(f"Loaded {len(sequences)} sequences.")

    # ── Build DataFrame ───────────────────────────────────────────────────────
    rows = [flatten_sequence(s) for s in sequences]
    rows = [r for r in rows if r is not None]
    df = pd.DataFrame(rows)

    print(f"Feature matrix: {df.shape[0]} rows x {df.shape[1]} cols\n")

    # ── Outcome distribution ──────────────────────────────────────────────────
    print("=== DISTRIBUZIONE ESITI ===")
    outcome_counts = df["outcome"].value_counts()
    total = len(df)
    for k, v in outcome_counts.items():
        print(f"  {k:10s}: {v} ({v/total*100:.1f}%)")

    print(f"\n  Escursione media LONG : +{df[df.outcome=='long']['target_delta'].mean():.1f} pt in {df[df.outcome=='long']['target_mins'].mean():.0f} min")
    print(f"  Escursione media SHORT: {df[df.outcome=='short']['target_delta'].mean():.1f} pt in {df[df.outcome=='short']['target_mins'].mean():.0f} min")

    # ── Feature columns for ML ────────────────────────────────────────────────
    meta_cols = ["seq_id", "date", "start_time", "target_delta", "target_mins",
                 "outcome", "abs_excursion"]
    feat_cols = [c for c in df.columns if c not in meta_cols]
    X = df[feat_cols].fillna(0).values
    y_outcome = df["outcome"].values

    # ── K-Means Clustering ────────────────────────────────────────────────────
    N_CLUSTERS = 8
    print(f"\n=== K-MEANS CLUSTERING ({N_CLUSTERS} cluster) ===")
    km = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    df["cluster"] = km.fit_predict(X)

    cluster_summary = []
    for c in range(N_CLUSTERS):
        cdf = df[df["cluster"] == c]
        n = len(cdf)
        n_long   = (cdf["outcome"] == "long").sum()
        n_short  = (cdf["outcome"] == "short").sum()
        n_neutral= (cdf["outcome"] == "neutral").sum()
        avg_exc  = cdf["abs_excursion"].mean()
        best_outcome = "long" if n_long > n_short else "short" if n_short > n_long else "neutral"
        win_rate = max(n_long, n_short) / n * 100

        # Most common features in this cluster
        last_side = "BUY" if cdf["s0_side"].mean() > 0 else "SELL"
        avg_vol   = cdf["s0_volume"].mean()
        avg_phase = cdf["s0_phase"].mean()
        phase_name = ["pre_mkt","ib_forming","morning","midday","afternoon","close"][int(round(avg_phase))]
        ib_pos_avg = cdf["s0_ib_pos"].mean()
        ib_label  = "above IB" if ib_pos_avg > 1 else "inside IB upper" if ib_pos_avg > 0 else "inside IB lower" if ib_pos_avg > -1 else "below IB"
        vwap_avg  = cdf["s0_vs_vwap"].mean()
        vwap_label= "above VWAP" if vwap_avg > 0.3 else "below VWAP" if vwap_avg < -0.3 else "at VWAP"
        consec    = cdf["s0_consec"].mean()

        summary = {
            "cluster": c,
            "n_sequences": n,
            "win_rate_pct": round(win_rate, 1),
            "best_outcome": best_outcome,
            "n_long": int(n_long),
            "n_short": int(n_short),
            "n_neutral": int(n_neutral),
            "avg_excursion_pts": round(avg_exc, 1),
            "dominant_side": last_side,
            "avg_volume": round(avg_vol, 0),
            "session_phase": phase_name,
            "ib_position": ib_label,
            "vwap_position": vwap_label,
            "avg_consecutive_same_side": round(consec, 1),
        }
        cluster_summary.append(summary)

        print(f"\n  Cluster {c} ({n} seq) | WinRate: {win_rate:.0f}% {best_outcome.upper()}")
        print(f"    Fase: {phase_name} | {ib_label} | {vwap_label}")
        print(f"    Lato: {last_side} | Vol medio: {avg_vol:.0f} | Consec: {consec:.1f}")
        print(f"    Escursione media: {avg_exc:.1f} pt | Long:{n_long} Short:{n_short} Neutral:{n_neutral}")

    # ── Decision Tree ──────────────────────────────────────────────────────────
    print("\n=== DECISION TREE - Regole per LONG profittevole ===")
    y_long = (y_outcome == "long").astype(int)
    dt_long = DecisionTreeClassifier(max_depth=4, min_samples_leaf=15, random_state=42)
    dt_long.fit(X, y_long)
    rules_long = export_text(dt_long, feature_names=feat_cols, max_depth=4)
    # Print only the most predictive branches
    lines = rules_long.split("\n")
    print("Top regole Long (rami con >= 60% win rate):")
    for i, line in enumerate(lines[:60]):
        print("  " + line)

    print("\n=== DECISION TREE - Regole per SHORT profittevole ===")
    y_short = (y_outcome == "short").astype(int)
    dt_short = DecisionTreeClassifier(max_depth=4, min_samples_leaf=15, random_state=42)
    dt_short.fit(X, y_short)
    rules_short = export_text(dt_short, feature_names=feat_cols, max_depth=4)
    print("Top regole Short (rami con >= 60% win rate):")
    for i, line in enumerate(rules_short.split("\n")[:60]):
        print("  " + line)

    # ── Feature importance ─────────────────────────────────────────────────────
    print("\n=== TOP 10 FEATURE PIU' IMPORTANTI (per Long) ===")
    importance_long = pd.Series(dt_long.feature_importances_, index=feat_cols)
    top10 = importance_long.nlargest(10)
    for feat, imp in top10.items():
        print(f"  {feat:35s}: {imp:.3f}")

    print("\n=== TOP 10 FEATURE PIU' IMPORTANTI (per Short) ===")
    importance_short = pd.Series(dt_short.feature_importances_, index=feat_cols)
    top10s = importance_short.nlargest(10)
    for feat, imp in top10s.items():
        print(f"  {feat:35s}: {imp:.3f}")

    # ── Best clusters by excursion ─────────────────────────────────────────────
    print("\n=== TOP 3 CLUSTER PER ESCURSIONE MEDIA ===")
    sorted_clusters = sorted(cluster_summary, key=lambda x: x["avg_excursion_pts"], reverse=True)
    for c in sorted_clusters[:3]:
        print(f"\n  Cluster {c['cluster']} - {c['avg_excursion_pts']} pt medi | WinRate {c['win_rate_pct']}% {c['best_outcome'].upper()}")
        print(f"    -> {c['session_phase']} | {c['ib_position']} | {c['vwap_position']} | {c['dominant_side']} x{c['avg_consecutive_same_side']:.0f}")

    # ── Save report ────────────────────────────────────────────────────────────
    report = {
        "total_sequences": len(df),
        "outcome_distribution": outcome_counts.to_dict(),
        "clusters": cluster_summary,
        "feature_importance_long":  importance_long.nlargest(15).to_dict(),
        "feature_importance_short": importance_short.nlargest(15).to_dict(),
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    print(f"\nReport salvato in {OUT_FILE}")

if __name__ == "__main__":
    main()
