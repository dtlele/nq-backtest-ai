# Day-Similarity Engine — Findings & How To Use

## TL;DR

Out of 230 days of out-of-sample testing on 1-minute NQ bars:

| Target (10:00 → 10:30 ET) | Predictable? | Correlation | RMSE vs baseline |
|---|---|---|---|
| **Range (size of the move)** | ✅ **YES** | **+0.55** | **+5% better** |
| Direction (sign) | ❌ NO | −0.13 | worse than baseline |
| Max favorable excursion (MFE) | ⚠ weak | +0.28 | no improvement |
| Max adverse excursion (MAE) | ❌ NO | +0.06 | worse |
| End-of-day return | ❌ NO | −0.05 | no signal |

**The honest answer**: the 30-minute **range** after the Initial Balance is
genuinely predictable from the pre-market + IB signature. The **direction**
is not. The system therefore predicts a *distribution of outcomes* (range,
P10/P90 band, path fan) rather than a point forecast of direction.

## What's built

```
src/day_similarity/
  config.py           # structural constants only, NO hardcoded prices
  tpo.py              # TPO profile (substitute for volume profile)
  data_loader.py      # cache_ohlc → tidy 1-min bars
  features.py         # per-day feature engineering (62 features)
  embeddings/contrastive.py  # outcome-supervised contrastive (32-D)
  predict.py          # main predictor API
scripts/similarity/
  build_features.py            # day_features.parquet
  cluster_unsupervised.py      # UMAP + HDBSCAN + GMM
  train_contrastive.py         # contrastive embedder
  save_models.py               # joblib artefacts
data/similarity/               # 230 days × 64 features + models
app_dashboard.py               # Streamlit dashboard
```

## Quick start

```bash
# Build everything from scratch
python scripts/similarity/build_features.py
python scripts/similarity/cluster_unsupervised.py
python scripts/similarity/train_contrastive.py
python scripts/similarity/save_models.py

# Launch the dashboard
streamlit run app_dashboard.py
```

## Programmatic API

```python
from src.day_similarity.predict import DaySimilarityPredictor
from src.day_similarity.data_loader import (
    bars_for_date, load_all_bars, slice_phase
)

predictor = DaySimilarityPredictor()
predictor.load("data/similarity")
predictor.bars = load_all_bars("cache_ohlc")

day = bars_for_date(predictor.bars, pd.Timestamp("2026-06-17"))
pre = slice_phase(day, 0, 9*60+30)
ib  = slice_phase(day, 9*60+30, 10*60)
result = predictor.predict_for_today(
    pd.Timestamp("2026-06-17"), pre, ib=ib, k_similar=7, fan_n_paths=30
)
result.show()        # textual summary
result.path_fan      # dict with 'times_min', 'paths', 'p10', 'p50', 'p90'
```

## What the dashboard shows

1. **Overview**: UMAP regime map (every day is a dot, color = cluster or
   outcome). Histograms of the 30m return / range / direction.
2. **Predict (live)**: pick a date → see top-7 similar historical days,
   predicted range with P10-P90, soft cluster probabilities, and notes.
3. **Path fan**: the actual 10:00→10:30 paths of the K most similar days,
   with P10/P50/P90 bands and the actual outcome overlaid.
4. **Backtest**: walk-forward validation table and a scatter of
   predicted vs actual range.
5. **Findings**: the text of this document, in dashboard form.

## Methodology notes

- All features are **% / ratio / z-score**. No hardcoded price levels.
  NQ went from ~21k to ~30k during the dataset, and the engine has no
  notion of an "absolute level".
- TPO (Time-Price-Opportunity) profile is used in place of a true
  volume profile, because the 1-min cache has no per-side volume.
  Adding tick data would unlock delta / footprint / big-trade features.
- The contrastive embedding adds little over plain features on 230 days.
  With more data it should start to dominate.
- Soft cluster assignment (GMM on UMAP) gives interpretable regime
  probabilities without forcing every day into one bucket.

## Limitations

- 230 days is **small** for deep learning. Most of the lift comes from
  feature engineering + simple ML (GBR / Ridge / k-NN).
- The dashboard is in Italian-friendly English. A future task is to
  add FOMC / CPI / OPEX / turn-of-month flags with proper calendar data.
- The system is **a probability engine**, not a strategy. The trader
  decides what to do with the range prediction (size, strike width, stop).
