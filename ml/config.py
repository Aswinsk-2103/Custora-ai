"""Shared configuration: paths and the feature schema used by training, API and UI."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("CUSTORA_DATA_DIR", ROOT / "data"))
MODEL_DIR = Path(os.environ.get("CUSTORA_MODEL_DIR", ROOT / "models"))
DB_PATH = Path(os.environ.get("CUSTORA_DB", DATA_DIR / "custora.db"))
FRONTEND_DIR = ROOT / "frontend"

# name, label, min, max, group
FEATURES = [
    {"name": "recency", "label": "Days since last order", "min": 1, "max": 365, "group": "purchase"},
    {"name": "frequency", "label": "Orders in the last 12 months", "min": 0, "max": 40, "group": "purchase"},
    {"name": "aov", "label": "Average order value", "min": 5, "max": 500, "group": "purchase"},
    {"name": "tenure", "label": "Months as a customer", "min": 1, "max": 72, "group": "purchase"},
    {"name": "discount_rate", "label": "Orders with a discount (%)", "min": 0, "max": 100, "group": "purchase"},
    {"name": "sessions", "label": "Site sessions per month", "min": 0, "max": 60, "group": "engagement"},
    {"name": "email_click_rate", "label": "Email click rate (%)", "min": 0, "max": 100, "group": "engagement"},
    {"name": "cart_abandon_rate", "label": "Cart abandonment (%)", "min": 0, "max": 100, "group": "engagement"},
    {"name": "support_tickets", "label": "Support tickets (12 months)", "min": 0, "max": 10, "group": "engagement"},
]
FEATURE_NAMES = [f["name"] for f in FEATURES]
TARGET_REVENUE = "future_revenue"   # revenue in the next 12 months
TARGET_ORDERS = "future_orders"     # orders in the next 12 months (>0 means retained)
