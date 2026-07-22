"""V2.0 — Calibrazione isotonica (PAVA) della confidence LLM.
Fit SOLO su trade di train. Se n_trades < soglia → veto-only mode."""
from __future__ import annotations


def fit_isotonic(xs: list, ys: list) -> list:
    """Pool Adjacent Violators. Ritorna blocchi [(x_max, y_hat)] monotoni crescenti."""
    if not xs:
        return []
    pts = sorted(zip(xs, ys))
    blocks = []  # [x_min, x_max, sum_y, w]
    for x, y in pts:
        blocks.append([x, x, y, 1.0])
        while len(blocks) >= 2:
            b2, b1 = blocks[-1], blocks[-2]
            m1 = b1[2] / b1[3]
            m2 = b2[2] / b2[3]
            if m1 > m2:
                merged = [b1[0], b2[1], b1[2] + b2[2], b1[3] + b2[3]]
                blocks = blocks[:-2] + [merged]
            else:
                break
    return [(b[1], b[2] / b[3]) for b in blocks]


def predict_isotonic(blocks: list, x: float) -> float:
    if not blocks:
        return 0.5
    if x <= blocks[0][0]:
        return blocks[0][1]
    if x >= blocks[-1][0]:
        return blocks[-1][1]
    for i in range(1, len(blocks)):
        if x <= blocks[i][0]:
            x0, y0 = blocks[i - 1]
            x1, y1 = blocks[i]
            w = (x - x0) / (x1 - x0) if x1 > x0 else 0.5
            return y0 + w * (y1 - y0)
    return blocks[-1][1]


class ConfidenceCalibrator:
    def __init__(self, min_trades: int = 80):
        self.blocks: list = []
        self.n = 0
        self.min_trades = min_trades

    def fit(self, confidences: list, wins: list) -> None:
        self.n = len(confidences)
        self.blocks = fit_isotonic(confidences, [float(w) for w in wins])

    def prob(self, confidence: float) -> float:
        return predict_isotonic(self.blocks, confidence)

    @property
    def active(self) -> bool:
        return self.n >= self.min_trades and len(self.blocks) >= 2
