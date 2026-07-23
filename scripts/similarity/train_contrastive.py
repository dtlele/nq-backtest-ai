"""Train the outcome-supervised contrastive day embedder.

Writes:
  data/similarity/contrastive_emb.parquet  (date, emb_<i> for i in 0..31)
  data/similarity/contrastive_model.pt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.day_similarity.embeddings.contrastive import (
    EmbeddingConfig, embed, train_embedder,
)


def pick_features(df: pd.DataFrame) -> list:
    """Same logic as the unsupervised script — pre-market + IB + context features,
    drop outcomes and date."""
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
    p.add_argument("--target", default="ret_pct_next_30m",
                   help="Which outcome to align the embedding to")
    p.add_argument("--sigma", type=float, default=0.20,
                   help="Outcome distance threshold (in target units, e.g. %) "
                        "below which days are pulled together")
    p.add_argument("--epochs", type=int, default=60)
    p.add_argument("--out-dim", type=int, default=32)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(args.features).sort_values("date").reset_index(drop=True)
    feat_cols = pick_features(df)
    print(f"Using {len(feat_cols)} features, target={args.target}, "
          f"sigma={args.sigma}")

    X = df[feat_cols].to_numpy(dtype=float)
    X = pd.DataFrame(X).fillna(pd.DataFrame(X).median()).to_numpy()
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds[stds == 0] = 1.0
    Xz = (X - means) / stds

    y = df[args.target].to_numpy(dtype=float)
    # Replace NaN targets with the mean (rare) and keep a mask
    nan_mask = ~np.isfinite(y)
    if nan_mask.any():
        y[nan_mask] = np.nanmean(y)
    print(f"   target mean={y.mean():.3f}  std={y.std():.3f}  n={len(y)}  "
          f"({int(nan_mask.sum())} imputed)")

    cfg = EmbeddingConfig(
        input_dim=Xz.shape[1],
        hidden_dim=64,
        out_dim=args.out_dim,
        dropout=0.30,
        lr=1e-3,
        weight_decay=1e-4,
        epochs=args.epochs,
        batch_size=64,
        temperature=0.10,
        outcome_sigma=args.sigma,
    )
    print("Training embedder ...")
    model, history = train_embedder(Xz, y, cfg, seed=args.seed)

    emb = embed(model, Xz)
    emb_df = pd.DataFrame({"date": df["date"]})
    for i in range(args.out_dim):
        emb_df[f"emb_{i}"] = emb[:, i]
    emb_df.to_parquet(out_dir / "contrastive_emb.parquet", index=False)

    # Save a small bundle (model + scaler params)
    import torch
    bundle = {
        "state_dict": model.state_dict(),
        "cfg": cfg.__dict__,
        "feat_cols": feat_cols,
        "mean": means.tolist(),
        "std": stds.tolist(),
    }
    torch.save(bundle, out_dir / "contrastive_model.pt")
    print(f"Wrote embeddings ({emb.shape}) and model bundle to {out_dir}")


if __name__ == "__main__":
    main()
