"""Unsupervised regime discovery on the per-day feature matrix.

Pipeline:
  features (numeric, z-scored) -> UMAP (2-D) -> HDBSCAN + GMM

Writes:
  data/similarity/umap_2d.parquet         (date, x, y)
  data/similarity/hdbscan_labels.parquet  (date, label_hdbscan)
  data/similarity/gmm_labels.parquet      (date, gmm_k, label_gmm, p_<i>_gmm)
  data/similarity/regime_summary.csv      (cluster sizes + outcome stats)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


# Features we feed to the embedding: drop the outcomes, drop "date".
FEATURE_PREFIXES = ("pm_", "ib_", "ctx_", "z_", "dow", "week_of_month", "is_")
OUTCOME_TOKENS = ("ret_pct", "mfe_pct", "mae_pct", "range_pct", "dir_sign")


def pick_features(df: pd.DataFrame) -> list:
    cols = []
    for c in df.columns:
        if c == "date":
            continue
        if any(tok in c for tok in OUTCOME_TOKENS):
            continue
        if not pd.api.types.is_numeric_dtype(df[c]):
            continue
        cols.append(c)
    return cols


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--features", default="data/similarity/day_features.parquet")
    p.add_argument("--out", default="data/similarity")
    p.add_argument("--umap-neighbors", type=int, default=15)
    p.add_argument("--umap-min-dist", type=float, default=0.1)
    p.add_argument("--gmm-k", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.features).sort_values("date").reset_index(drop=True)
    feat_cols = pick_features(df)
    print(f"Using {len(feat_cols)} features for embedding")

    X = df[feat_cols].to_numpy(dtype=float)
    # Median impute (defensive) and z-score
    X = pd.DataFrame(X).fillna(pd.DataFrame(X).median()).to_numpy()
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds[stds == 0] = 1.0
    Xz = (X - means) / stds

    # ----- UMAP -----
    import umap
    print("Fitting UMAP ...")
    reducer = umap.UMAP(
        n_neighbors=args.umap_neighbors,
        min_dist=args.umap_min_dist,
        n_components=2,
        random_state=args.seed,
        metric="euclidean",
    )
    emb2d = reducer.fit_transform(Xz)
    pd.DataFrame({"date": df["date"], "x": emb2d[:, 0], "y": emb2d[:, 1]}).to_parquet(
        out_dir / "umap_2d.parquet", index=False
    )
    print(f"UMAP done. Embedding shape: {emb2d.shape}")

    # ----- HDBSCAN -----
    import hdbscan
    print("Fitting HDBSCAN ...")
    clusterer = hdbscan.HDBSCAN(min_cluster_size=15, min_samples=5)
    labels = clusterer.fit_predict(emb2d)
    pd.DataFrame({"date": df["date"], "label_hdbscan": labels}).to_parquet(
        out_dir / "hdbscan_labels.parquet", index=False
    )
    n_clusters = len(set(labels) - {-1})
    n_noise = int((labels == -1).sum())
    print(f"HDBSCAN: {n_clusters} clusters, {n_noise} noise points "
          f"({n_noise/len(labels)*100:.1f}%)")

    # ----- GMM on UMAP -----
    from sklearn.mixture import GaussianMixture
    print(f"Fitting GMM(k={args.gmm_k}) ...")
    gmm = GaussianMixture(n_components=args.gmm_k, covariance_type="full",
                          random_state=args.seed, n_init=5, max_iter=300)
    gmm_labels = gmm.fit_predict(emb2d)
    probs = gmm.predict_proba(emb2d)
    gmm_df = pd.DataFrame({"date": df["date"], "label_gmm": gmm_labels})
    for i in range(args.gmm_k):
        gmm_df[f"p_{i}_gmm"] = probs[:, i]
    gmm_df.to_parquet(out_dir / "gmm_labels.parquet", index=False)
    bic = gmm.bic(emb2d)
    aic = gmm.aic(emb2d)
    print(f"GMM BIC={bic:.0f} AIC={aic:.0f}")

    # ----- Regime summary -----
    out_cols = ["ret_pct_next_30m", "mfe_pct_next_30m", "mae_pct_next_30m",
                "range_pct_next_30m", "dir_sign_next_30m",
                "ret_pct_eod", "dir_sign_eod"]
    rows = []
    for label in sorted(set(labels)):
        mask = labels == label
        n = int(mask.sum())
        row = {"regime": label, "n_days": n}
        for c in out_cols:
            if c in df.columns:
                vals = df.loc[mask, c].dropna()
                if len(vals) == 0:
                    row[f"{c}_mean"] = float("nan")
                    row[f"{c}_std"] = float("nan")
                else:
                    row[f"{c}_mean"] = float(vals.mean())
                    row[f"{c}_std"] = float(vals.std())
        rows.append(row)
    summary = pd.DataFrame(rows).sort_values("n_days", ascending=False)
    summary.to_csv(out_dir / "regime_summary.csv", index=False)
    print("\nRegime summary (top 15):")
    print(summary.head(15).to_string(index=False))


if __name__ == "__main__":
    main()
