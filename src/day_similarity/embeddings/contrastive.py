"""Outcome-supervised contrastive day embedding.

The standard unsupervised UMAP clusters the *features*.  We add a small MLP
that is trained with a *supervised contrastive* loss on the actual next-30m
return: days with similar future returns should be close in the embedding.

The output is a 32-dim embedding per day.  When we add it to the unsupervised
view we can rank days by *either* shape-similarity or predicted-outcome
similarity.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class EmbeddingConfig:
    input_dim: int
    hidden_dim: int = 64
    out_dim: int = 32
    dropout: float = 0.30
    lr: float = 1e-3
    weight_decay: float = 1e-4
    epochs: int = 60
    batch_size: int = 64
    temperature: float = 0.10   # softmax temperature for the contrastive loss
    outcome_sigma: float = 0.20  # in the *target* space, return % units


class DayEmbedder(nn.Module):
    def __init__(self, cfg: EmbeddingConfig):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(cfg.input_dim, cfg.hidden_dim),
            nn.GELU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(cfg.hidden_dim, cfg.hidden_dim),
            nn.GELU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(cfg.hidden_dim, cfg.out_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def _supervised_contrastive_loss(
    z: torch.Tensor, y: torch.Tensor, temperature: float, sigma: float
) -> torch.Tensor:
    """Supervised contrastive loss: pull together days whose outcome
    (continuous) is within ``sigma`` of each other, push apart otherwise.

    z: (B, D) normalized embeddings
    y: (B,)   continuous target (next-30m return, in %)
    """
    z = F.normalize(z, dim=-1)
    sim = z @ z.T / max(temperature, 1e-6)  # (B, B)
    # Pairwise outcome distance
    dy = (y[:, None] - y[None, :]).abs()
    pos_mask = (dy < sigma).float()
    # Exclude self
    self_mask = torch.eye(z.size(0), device=z.device)
    pos_mask = pos_mask - self_mask
    pos_mask = pos_mask.clamp(min=0.0)

    # For numerical stability, subtract the per-anchor max
    sim_max = sim.max(dim=1, keepdim=True).values.detach()
    sim = sim - sim_max
    exp_sim = torch.exp(sim)
    # Mask self
    exp_sim = exp_sim * (1.0 - self_mask)
    denom = exp_sim.sum(dim=1, keepdim=True) + 1e-9
    log_prob = sim - torch.log(denom)
    pos_count = pos_mask.sum(dim=1)
    # Anchors with at least one positive neighbor contribute
    valid = (pos_count > 0).float()
    loss = -(pos_mask * log_prob).sum(dim=1) / pos_count.clamp(min=1.0)
    return (loss * valid).sum() / valid.sum().clamp(min=1.0)


def train_embedder(
    X: np.ndarray,
    y: np.ndarray,
    cfg: EmbeddingConfig | None = None,
    seed: int = 42,
    device: str | None = None,
) -> tuple:
    """Train ``DayEmbedder`` with the supervised contrastive loss.

    Returns (model, history dict with train losses).
    """
    torch.manual_seed(seed)
    np.random.seed(seed)
    if cfg is None:
        cfg = EmbeddingConfig(input_dim=X.shape[1])
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")

    X_t = torch.from_numpy(X).float().to(device)
    y_t = torch.from_numpy(y).float().to(device)

    model = DayEmbedder(cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cfg.epochs)

    history = {"loss": []}
    n = X_t.size(0)
    for epoch in range(cfg.epochs):
        model.train()
        perm = torch.randperm(n, device=device)
        ep_loss = 0.0
        n_batches = 0
        for start in range(0, n, cfg.batch_size):
            idx = perm[start:start + cfg.batch_size]
            xb, yb = X_t[idx], y_t[idx]
            z = model(xb)
            loss = _supervised_contrastive_loss(z, yb, cfg.temperature, cfg.outcome_sigma)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            ep_loss += float(loss.detach().item())
            n_batches += 1
        sched.step()
        avg = ep_loss / max(n_batches, 1)
        history["loss"].append(avg)
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"   epoch {epoch+1:3d}/{cfg.epochs}  loss={avg:.4f}")
    return model, history


@torch.no_grad()
def embed(model: DayEmbedder, X: np.ndarray, device: str | None = None) -> np.ndarray:
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model.eval()
    X_t = torch.from_numpy(X).float().to(device)
    return model(X_t).cpu().numpy()
