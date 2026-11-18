"""Loads the trained models and turns raw customer features into predictions."""
import json
import re

import joblib
import numpy as np
import pandas as pd

from ml.config import FEATURE_NAMES, MODEL_DIR

ALIASES = {
    "recency": ("recency", "dayssince", "lastorder"),
    "frequency": ("frequency", "orders"),
    "aov": ("aov", "avgorder", "averageorder", "monetary", "ordervalue"),
    "tenure": ("tenure", "monthsas", "customerage"),
    "discount_rate": ("discount",),
    "sessions": ("session", "visit"),
    "email_click_rate": ("emailclick", "clickrate", "email"),
    "cart_abandon_rate": ("cartabandon", "abandon"),
    "support_tickets": ("ticket", "support"),
}


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


class Predictor:
    def __init__(self):
        if not (MODEL_DIR / "metadata.json").exists():
            from ml.train import train
            train(n=6000, verbose=False)          # first run: train automatically
        self.meta = json.loads((MODEL_DIR / "metadata.json").read_text())
        self.reg = joblib.load(MODEL_DIR / "clv_model.joblib")
        self.clf = joblib.load(MODEL_DIR / "churn_model.joblib")
        self.spec = {f["name"]: f for f in self.meta["features"]}
        self.q50 = self.meta["quantiles"]["q50"]
        self.q80 = self.meta["quantiles"]["q80"]

    # ---------- input handling ----------
    def clean(self, raw):
        """Fill missing values with the training median and clamp to the supported range."""
        out = {}
        for name in FEATURE_NAMES:
            f = self.spec[name]
            try:
                v = float((raw or {}).get(name))
                if v != v:
                    raise ValueError
            except (TypeError, ValueError):
                v = f["default"]
            out[name] = min(max(v, f["min"]), f["max"])
        return out

    def map_columns(self, columns):
        """Match CSV headers to model features. Returns (feature->column, id column)."""
        cols = {c: norm(c) for c in columns}
        used, mapping = set(), {}
        for feat in FEATURE_NAMES:
            for c, n in cols.items():
                if c not in used and any(a in n for a in ALIASES[feat]):
                    mapping[feat] = c
                    used.add(c)
                    break
        idcol = next((c for c, n in cols.items() if c not in used and
                      (n in ("id", "name", "customer") or n.startswith("customer") or n.endswith("id"))), None)
        return mapping, idcol

    # ---------- scoring ----------
    def _frame(self, rows):
        return pd.DataFrame([[r[n] for n in FEATURE_NAMES] for r in rows], columns=FEATURE_NAMES)

    def segment(self, p, revenue):
        if p >= 0.6 and revenue >= self.q80:
            return "Champion"
        if p >= 0.5:
            return "Loyal regular"
        if revenue >= self.q50:
            return "At risk"
        return "Hibernating"

    @staticmethod
    def risk(p):
        return "Low" if p >= 0.7 else "Medium" if p >= 0.4 else "High"

    def score(self, rows, margin=35.0):
        """Score cleaned feature dicts. margin is a percentage."""
        if not rows:
            return []
        X = self._frame(rows)
        rev = np.clip(self.reg.predict(X), 0, None)
        p = self.clf.predict_proba(X)[:, 1]
        m = margin / 100.0
        return [{"revenue_12m": round(float(r), 2), "clv_12m": round(float(r) * m, 2),
                 "retention_probability": round(float(q), 4), "churn_risk": self.risk(float(q)),
                 "segment": self.segment(float(q), float(r))} for r, q in zip(rev, p)]

    def explain(self, feats, base, margin):
        """Occlusion drivers: how much does each feature move this customer vs a typical one?"""
        variants = []
        for n in FEATURE_NAMES:
            v = dict(feats)
            v[n] = self.spec[n]["default"]
            variants.append(v)
        X = self._frame(variants)
        rev = np.clip(self.reg.predict(X), 0, None)
        p = self.clf.predict_proba(X)[:, 1]
        out = []
        for i, n in enumerate(FEATURE_NAMES):
            out.append({"feature": n, "label": self.spec[n]["label"], "value": feats[n],
                        "typical": self.spec[n]["default"],
                        "clv_effect": round(float((base["revenue_12m"] - rev[i]) * margin / 100), 2),
                        "retention_effect": round(float(base["retention_probability"] - p[i]), 4)})
        return sorted(out, key=lambda d: -abs(d["clv_effect"]))

    def actions(self, f, seg):
        a = []
        if f["recency"] > 90:
            a.append(f"It has been {int(f['recency'])} days since the last order. Send a win-back message with a time-limited offer.")
        if f["email_click_rate"] < 15:
            a.append("Email clicks are low. Try shorter subject lines or reach out on SMS or WhatsApp.")
        if f["sessions"] < 5:
            a.append("Few site visits. Retarget with reminders of items they viewed or saved.")
        if f["frequency"] < 4:
            a.append("Few orders per year. Offer a subscription or bundle to build a repeat habit.")
        if f["cart_abandon_rate"] > 75:
            a.append("Many abandoned carts. Send cart reminders and simplify checkout.")
        if f["support_tickets"] >= 4:
            a.append("Several support tickets. A personal follow-up could repair the relationship.")
        if f["discount_rate"] > 60:
            a.append("Mostly buys on discount. Protect margin with value-based perks instead of price cuts.")
        a.append({"Champion": "Reward loyalty with early access, a referral bonus or a members-only perk.",
                  "Loyal regular": "Grow the basket with cross-sell suggestions and free-shipping thresholds.",
                  "At risk": "Act this week: this customer has real value but is drifting away.",
                  "Hibernating": "Keep costs low: use automated nudges rather than personal outreach."}[seg])
        return a[:4]

    def predict_one(self, raw, margin=35.0):
        f = self.clean(raw)
        base = self.score([f], margin)[0]
        drivers = self.explain(f, base, margin)
        return {**base, "features": f, "margin": margin, "drivers": drivers,
                "actions": self.actions(f, base["segment"]),
                "model": {"regressor": self.meta["best_regressor"], "classifier": self.meta["best_classifier"],
                          "version": self.meta["version"]}}
