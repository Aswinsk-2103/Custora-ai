"""Simulate a customer base: 12 months of observed behaviour -> next 12 months of revenue.

The simulation follows the logic of buy-till-you-die models: each customer has a latent
purchase rate and a latent loyalty. Loyal customers are more likely to still be "alive",
and engagement signals (sessions, email clicks) are noisy readings of that loyalty.
Replace this module with a loader for real data (same columns) to train on your own customers.
"""
import argparse
import numpy as np
import pandas as pd
from .config import DATA_DIR, FEATURE_NAMES, TARGET_ORDERS, TARGET_REVENUE


def generate(n: int = 8000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    loyalty = rng.beta(2, 2, n)
    lam = rng.gamma(1.6, 2.6, n) * (0.6 + 0.8 * loyalty)          # orders per year
    tenure = rng.integers(1, 73, n)
    alive = rng.random(n) < (0.2 + 0.75 * loyalty)
    exposure = np.minimum(tenure, 12) / 12

    frequency = rng.poisson(lam * exposure * np.where(alive, 1.0, 0.7))
    recency = np.where(alive,
                       rng.exponential(365 / (frequency + 1) * 0.8),
                       120 + rng.exponential(100, n))
    recency = np.clip(np.round(recency), 1, 365)
    aov = np.clip(np.exp(rng.normal(np.log(55) + 0.35 * loyalty, 0.55, n)), 5, 500)
    sessions = np.clip(rng.poisson(2 + 16 * loyalty * np.where(alive, 1, 0.35) + 0.6 * lam), 0, 60)
    email = np.clip(rng.normal(8 + 48 * loyalty * np.where(alive, 1, 0.45), 9), 0, 100)
    discount = np.clip(rng.normal(35 - 20 * loyalty, 15), 0, 100)
    cart = np.clip(rng.normal(75 - 35 * loyalty, 12), 0, 100)
    tickets = np.minimum(rng.poisson(0.4 + 1.8 * (1 - loyalty)), 10)

    future_orders = rng.poisson(lam * (0.7 + 0.3 * loyalty) * alive)
    future_revenue = future_orders * aov * np.exp(rng.normal(0, 0.12, n))

    df = pd.DataFrame({
        "recency": recency, "frequency": frequency, "aov": aov.round(2), "tenure": tenure,
        "discount_rate": discount.round(1), "sessions": sessions, "email_click_rate": email.round(1),
        "cart_abandon_rate": cart.round(1), "support_tickets": tickets,
        TARGET_ORDERS: future_orders, TARGET_REVENUE: future_revenue.round(2),
    })
    return df[FEATURE_NAMES + [TARGET_ORDERS, TARGET_REVENUE]]


def main():
    ap = argparse.ArgumentParser(description="Generate the synthetic customer dataset")
    ap.add_argument("--n", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--sample", action="store_true", help="also write a 200-row upload sample")
    a = ap.parse_args()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = generate(a.n, a.seed)
    df.to_csv(DATA_DIR / "synthetic_customers.csv", index=False)
    print(f"Wrote {len(df)} rows to {DATA_DIR / 'synthetic_customers.csv'}")
    if a.sample:
        s = generate(200, a.seed + 1)[FEATURE_NAMES]
        s.insert(0, "customer_id", [f"C-{1001 + i}" for i in range(len(s))])
        s.to_csv(DATA_DIR / "customers_sample.csv", index=False)
        print("Wrote data/customers_sample.csv")


if __name__ == "__main__":
    main()
