"""Addestra Random Forest per predire WIN/LOSS di candele M5 NQ.

Features: ~25 features orderflow estratte da 230 giorni
Target: WIN (1) se movimento > 20pt in 30min in una direzione, LOSS (0)
"""
import csv
import os
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report, confusion_matrix

CSV_PATH = r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml\features_230d.csv'
MODEL_OUT = r'C:\Users\Mauro\Documents\nq-backtest-clean\data\ml\rf_v1.pkl'

# Carica features
df = pd.read_csv(CSV_PATH)
print(f'Dataset: {len(df)} righe, {df.columns.tolist()}')
print(f'Label distribution: WIN={df["label"].sum()} ({100*df["label"].mean():.1f}%), LOSS={len(df)-df["label"].sum()}')

# Rimuovi colonne non-features
FEATURE_COLS = [c for c in df.columns if c not in ('date', 'time_et', 'label')]
print(f'Features ({len(FEATURE_COLS)}): {FEATURE_COLS}')

# Converti in X, y
X = df[FEATURE_COLS].fillna(0).values
y = df['label'].values

# Train/test split TEMPORALE (no shuffle!)
SPLIT_PCT = 0.8
split_idx = int(len(df) * SPLIT_PCT)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]
print(f'\nTrain: {len(X_train)} ({y_train.sum()} WIN)')
print(f'Test:  {len(X_test)} ({y_test.sum()} WIN)')

# Time series CV per robustezza
print('\n=== TIME SERIES CROSS-VALIDATION ===')
tscv = TimeSeriesSplit(n_splits=5)
aucs = []
accs = []
for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
    Xt, Xv = X[train_idx], X[val_idx]
    yt, yv = y[train_idx], y[val_idx]
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_split=50,
        min_samples_leaf=20,
        max_features='sqrt',
        n_jobs=-1,
        random_state=42,
    )
    model.fit(Xt, yt)
    proba = model.predict_proba(Xv)[:, 1]
    auc = roc_auc_score(yv, proba)
    acc = accuracy_score(yv, (proba > 0.5).astype(int))
    aucs.append(auc)
    accs.append(acc)
    print(f'  Fold {fold + 1}: AUC={auc:.3f}, Acc={acc:.3f}, WIN rate={yv.mean():.3f}')

print(f'\nCV Mean AUC: {np.mean(aucs):.3f} (+/- {np.std(aucs):.3f})')
print(f'CV Mean Acc: {np.mean(accs):.3f} (+/- {np.std(accs):.3f})')

# Train finale su tutto
print('\n=== TRAIN FINALE ===')
model = RandomForestClassifier(
    n_estimators=300,
    max_depth=10,
    min_samples_split=30,
    min_samples_leaf=15,
    max_features='sqrt',
    n_jobs=-1,
    random_state=42,
)
model.fit(X_train, y_train)

# Eval finale
proba_test = model.predict_proba(X_test)[:, 1]
auc_test = roc_auc_score(y_test, proba_test)
acc_test = accuracy_score(y_test, (proba_test > 0.5).astype(int))
print(f'Test set AUC: {auc_test:.3f}')
print(f'Test set Acc: {acc_test:.3f}')

# Confusion matrix
y_pred = (proba_test > 0.5).astype(int)
cm = confusion_matrix(y_test, y_pred)
print(f'\nConfusion matrix:')
print(f'  TN={cm[0,0]}, FP={cm[0,1]}')
print(f'  FN={cm[1,0]}, TP={cm[1,1]}')

# Per "edge" valutiamo: se filtriamo solo score > 0.6, migliora?
print('\n=== ANALISI EDGE (soglie di filtro) ===')
for thresh in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75]:
    mask = proba_test > thresh
    if mask.sum() < 10:
        continue
    y_sel = y_test[mask]
    if len(y_sel) == 0:
        continue
    win_rate = y_sel.mean()
    print(f'  Threshold {thresh:.2f}: n_trades={mask.sum()}, win_rate={win_rate:.3f} (vs base {y_test.mean():.3f})')

# Feature importance
print('\n=== TOP 15 FEATURE IMPORTANCE ===')
fi = pd.DataFrame({'feature': FEATURE_COLS, 'importance': model.feature_importances_})
fi = fi.sort_values('importance', ascending=False)
print(fi.head(15).to_string(index=False))

# Salva modello
import joblib
os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)
joblib.dump({
    'model': model,
    'feature_cols': FEATURE_COLS,
    'cv_auc': np.mean(aucs),
    'test_auc': auc_test,
    'test_acc': acc_test,
}, MODEL_OUT)
print(f'\nModello salvato in {MODEL_OUT}')
