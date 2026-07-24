"""Save the fitted GMM and UMAP models as joblib artefacts so the
predictor can use them in production.  Re-fits them on the feature
matrix (deterministic seed) — this is independent of the
``cluster_unsupervised.py`` run, so we don't need a re-run.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


def pick_features(df: pd.DataFrame) -> list:
    out = []
    for c in df.columns:
        if c == "date":
            continue
        if not pd.api.types.is_numeric_dtype(df[c]):
            continue
        if any(tok in c for tok in ("ret_pct", "mfe_pct", "mae_pct", "range_pct", "dir_sign")):
            continue
        out.append(c)
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--features", default="data/similarity/day_features.parquet")
    p.add_argument("--out", default="data/similarity")
    p.add_argument("--gmm-k", type=int, default=10)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.features).sort_values("date").reset_index(drop=True)
    feat_cols = pick_features(df)
    X = df[feat_cols].to_numpy(dtype=float)
    X = pd.DataFrame(X).fillna(pd.DataFrame(X).median()).to_numpy()
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds[stds == 0] = 1.0
    Xz = (X - means) / stds

    # Also fit a range predictor (Gradient Boosting)
    from sklearn.ensemble import GradientBoostingRegressor
    print("Fitting range model (GBR) ...")
    y = df["range_pct_next_30m"].to_numpy(dtype=float)
    mask = np.isfinite(y)
    range_model = GradientBoostingRegressor(
        n_estimators=200, max_depth=3, learning_rate=0.05, random_state=args.seed
    )
    range_model.fit(Xz[mask], y[mask])
    joblib.dump({"model": range_model, "feat_cols": feat_cols, "mean": means, "std": stds},
                out_dir / "range.joblib")
    print("   range model saved.")

    # UMAP
    import umap
    print("Fitting UMAP ...")
    reducer = umap.UMAP(
        n_neighbors=15, min_dist=0.1, n_components=2, random_state=args.seed,
    )
    emb = reducer.fit_transform(Xz)
    joblib.dump({"model": reducer, "feat_cols": feat_cols, "mean": means, "std": stds},
                out_dir / "umap.joblib")
    print("   UMAP saved.")

    # GMM on UMAP
    from sklearn.mixture import GaussianMixture
    print(f"Fitting GMM(k={args.gmm_k}) ...")
    gmm = GaussianMixture(n_components=args.gmm_k, covariance_type="full",
                          random_state=args.seed, n_init=5)
    gmm.fit(emb)
    joblib.dump({"model": gmm, "feat_cols": feat_cols, "mean": means, "std": stds},
                out_dir / "gmm.joblib")
    print("   GMM saved.")

    # Cross-val score for the range model
    from sklearn.model_selection import KFold
    preds = np.zeros_like(y)
    kf = KFold(n_splits=5, shuffle=False)
    for tr, te in kf.split(Xz):
        if not mask[tr].any():
            continue
        m = GradientBoostingRegressor(
            n_estimators=200, max_depth=3, learning_rate=0.05, random_state=args.seed
        )
        m.fit(Xz[tr][mask[tr]], y[tr][mask[tr]])
        preds[te] = m.predict(Xz[te])
    valid = mask & np.isfinite(preds)
    cor = np.corrcoef(y[valid], preds[valid])[0, 1]
    rmse = np.sqrt(((y[valid] - preds[valid]) ** 2).mean())
    rmse0 = np.sqrt(((y[valid] - y[valid].mean()) ** 2).mean())
    print(f"5-fold CV: cor={cor:+.3f}  rmse={rmse:.4f}  base={rmse0:.4f}  "
          f"improvement={(rmse0 - rmse) / rmse0 * 100:+.1f}%")


if __name__ == "__main__":
    main()
