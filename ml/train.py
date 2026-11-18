"""Train, compare and save the models.

    python -m ml.train                # simulate data and train
    python -m ml.train --csv my.csv   # train on your own table (feature columns + targets)

Artifacts written to models/: clv_model.joblib, churn_model.joblib, metadata.json
"""
import argparse
import json
import time
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import (GradientBoostingRegressor, HistGradientBoostingClassifier,
                              HistGradientBoostingRegressor, RandomForestRegressor)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, mean_absolute_error, mean_squared_error,
                             r2_score, roc_auc_score)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import (DATA_DIR, FEATURES, FEATURE_NAMES, MODEL_DIR, TARGET_ORDERS, TARGET_REVENUE)
from .generate_data import generate

VERSION = "1.0.0"


def regressors(seed):
    models = {
        "Linear Regression": make_pipeline(StandardScaler(), LinearRegression()),
        "Random Forest": RandomForestRegressor(n_estimators=150, min_samples_leaf=10, n_jobs=-1, random_state=seed),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=300, learning_rate=0.05, max_depth=3,
                                                       subsample=0.8, random_state=seed),
        "Hist Gradient Boosting": HistGradientBoostingRegressor(max_iter=300, learning_rate=0.06, random_state=seed),
    }
    try:  # optional extras if installed
        from xgboost import XGBRegressor
        models["XGBoost"] = XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=4, subsample=0.8, random_state=seed)
    except ImportError:
        pass
    try:
        from lightgbm import LGBMRegressor
        models["LightGBM"] = LGBMRegressor(n_estimators=300, learning_rate=0.05, verbose=-1, random_state=seed)
    except ImportError:
        pass
    return models


def train(n=8000, seed=42, csv=None, verbose=True):
    log = print if verbose else (lambda *a, **k: None)
    df = pd.read_csv(csv) if csv else generate(n, seed)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not csv:
        df.to_csv(DATA_DIR / "synthetic_customers.csv", index=False)
    X, y = df[FEATURE_NAMES], df[TARGET_REVENUE]
    active = (df[TARGET_ORDERS] > 0).astype(int)
    Xtr, Xte, ytr, yte, atr, ate = train_test_split(X, y, active, test_size=0.2, random_state=seed)
    log(f"Training on {len(Xtr)} customers, testing on {len(Xte)}")

    # ---- 1. revenue regression ----
    rows, fitted = [], {}
    for name, model in regressors(seed).items():
        t0 = time.time()
        cv = -cross_val_score(model, Xtr, ytr, cv=3, scoring="neg_root_mean_squared_error").mean()
        model.fit(Xtr, ytr)
        pred = np.clip(model.predict(Xte), 0, None)
        rows.append({"name": name, "rmse": float(np.sqrt(mean_squared_error(yte, pred))),
                     "mae": float(mean_absolute_error(yte, pred)), "r2": float(r2_score(yte, pred)),
                     "cv_rmse": float(cv), "seconds": round(time.time() - t0, 1)})
        fitted[name] = model
        log(f"  {name:24s} RMSE {rows[-1]['rmse']:8.2f}  MAE {rows[-1]['mae']:8.2f}  R2 {rows[-1]['r2']:.3f}")
    best = min(rows, key=lambda r: r["cv_rmse"])["name"]   # choose on CV, report on the held-out test set
    reg = fitted[best]
    log(f"Best regressor: {best}")

    pi = permutation_importance(reg, Xte, yte, n_repeats=5, random_state=seed,
                                scoring="neg_root_mean_squared_error")
    imp = np.clip(pi.importances_mean, 0, None)
    imp = imp / imp.sum() if imp.sum() > 0 else imp
    labels = {f["name"]: f["label"] for f in FEATURES}
    importance = sorted(({"feature": n, "label": labels[n], "share": float(s)}
                         for n, s in zip(FEATURE_NAMES, imp)), key=lambda d: -d["share"])

    # ---- 2. retention classifier (will the customer order again in the next 12 months?) ----
    clfs = {"Logistic Regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
            "Hist Gradient Boosting": HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06, random_state=seed)}
    crow = []
    for name, m in clfs.items():
        cv = cross_val_score(m, Xtr, atr, cv=3, scoring="roc_auc").mean()
        m.fit(Xtr, atr)
        p = m.predict_proba(Xte)[:, 1]
        crow.append({"name": name, "roc_auc": float(roc_auc_score(ate, p)),
                     "accuracy": float(accuracy_score(ate, p >= 0.5)), "f1": float(f1_score(ate, p >= 0.5)),
                     "cv_auc": float(cv)})
        log(f"  {name:24s} AUC {crow[-1]['roc_auc']:.3f}  acc {crow[-1]['accuracy']:.3f}")
    cbest = max(crow, key=lambda r: r["cv_auc"])["name"]

    # ---- 3. metadata used by the API and UI ----
    rev_train = np.clip(reg.predict(Xtr), 0, None)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(Xte), size=min(200, len(Xte)), replace=False)
    pte = np.clip(reg.predict(Xte), 0, None)
    meta = {
        "version": VERSION, "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_samples": int(len(df)), "seed": seed, "data_source": csv or "simulated",
        "features": [{**f, "default": float(X[f["name"]].median())} for f in FEATURES],
        "regressors": rows, "best_regressor": best, "classifiers": crow, "best_classifier": cbest,
        "importance": importance, "target_mean": float(y.mean()), "active_rate": float(active.mean()),
        "quantiles": {"q50": float(np.quantile(rev_train, 0.5)), "q80": float(np.quantile(rev_train, 0.8))},
        "scatter": [[round(float(yte.iloc[i]), 1), round(float(pte[i]), 1)] for i in idx],
    }
    joblib.dump(reg, MODEL_DIR / "clv_model.joblib")
    joblib.dump(clfs[cbest], MODEL_DIR / "churn_model.joblib")
    (MODEL_DIR / "metadata.json").write_text(json.dumps(meta, indent=2))
    log(f"Saved models to {MODEL_DIR}")
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Train the Custora AI models")
    ap.add_argument("--n", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--csv", help="train on your own CSV instead of simulated data")
    a = ap.parse_args()
    train(a.n, a.seed, a.csv)
