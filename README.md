# Custora AI: Customer Lifetime Value Prediction Using Purchase Behaviour and Engagement Data

**Author:** Aswin SK (24AD026)

A complete machine learning web application. It learns from a customer's purchase history and engagement
signals to predict (1) how much revenue the customer will bring in the next 12 months, (2) the probability the
customer is still active, and (3) the next best action, then serves everything through a REST API and a web UI.

```
 Browser (frontend/)  --HTTP/JSON-->  Flask API (backend/)  --->  SQLite (data/custora.db)
   sliders, upload,                     validation, scoring,          customers, scored lists, plans
   charts, history                      explanations, planner
                                              |
                                              v
                              Trained models (models/*.joblib)  <---  ml/train.py  <---  data
```

## Quick start

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                      # open http://127.0.0.1:5000
```

The first start trains the models automatically (about 30 seconds). To train explicitly and see the
comparison table in the terminal: `python -m ml.train`.

## Project structure

| Path | Purpose |
|---|---|
| `ml/config.py` | Feature schema (names, labels, valid ranges) shared by training, API and UI |
| `ml/generate_data.py` | Simulates a customer base (12 months of behaviour, then the next 12 months of revenue) |
| `ml/train.py` | Trains and compares models, evaluates on a held-out test set, saves artifacts |
| `backend/app.py` | Flask app: REST endpoints, validation, error handling, serves the frontend |
| `backend/predictor.py` | Loads models, scores customers, explains scores, picks segment and actions |
| `backend/planner.py` | Business planner (five-year value, payback, value of better retention) |
| `backend/db.py` | SQLite schema and queries, every row scoped to a client id |
| `frontend/` | `index.html`, `styles.css`, `app.js` (no build step) |
| `tests/test_api.py` | API tests (health, sanity of predictions, privacy, CSV upload, planner) |
| `data/customers_sample.csv` | 200-customer file to try the upload feature |
| `docs/` | Architecture notes and a viva cheat sheet |

## Machine learning approach

**Features (9):** recency, frequency, average order value, tenure, discount share (purchase behaviour);
site sessions, email click rate, cart abandonment, support tickets (engagement).

**Targets:** `future_revenue` (regression) and `future_orders > 0` (retention classification).

**Models compared:** Linear Regression, Random Forest, Gradient Boosting, Hist Gradient Boosting
(plus XGBoost and LightGBM automatically if installed). The winner is chosen by 3-fold cross-validated RMSE
on the training split and then reported on a held-out 20% test set, so the test score stays honest.
Retention uses Logistic Regression vs Hist Gradient Boosting, chosen by cross-validated ROC-AUC.

**Predicted CLV** = predicted 12-month revenue x profit margin (you set the margin in the UI).

**Explanations:** global importance comes from permutation importance on the test set. Per-customer
"why this score" bars come from occlusion: each feature is replaced by the typical (median) value and the
change in predicted value is measured.

**Segments:** Champion, Loyal regular, At risk, Hibernating, from retention probability and predicted value
percentiles. Each segment and weak signal maps to a recommended action.

### About the data
The bundled dataset is **simulated** with buy-till-you-die style logic (latent purchase rate and loyalty,
engagement as a noisy signal of loyalty). It lets the project run anywhere without private data, and the
model report says so. To use real customers, prepare a CSV with the nine feature columns plus
`future_revenue` and `future_orders`, where the features describe the last 12 months and the targets
describe the following 12 months, then run:

```bash
python -m ml.train --csv path/to/your_table.csv
```

## REST API

All data endpoints need the header `X-Client-Id` (the web app creates one per browser).

| Method and path | Description |
|---|---|
| `GET /api/health` | Service and model status |
| `GET /api/model` | Metrics, feature schema, importance, scatter data |
| `POST /api/predict` | `{features:{...}, margin}` returns value, retention, segment, drivers, actions |
| `POST /api/predict/batch` | Multipart CSV (`file`, optional `margin`, `name`, `save`) returns scored rows and summary |
| `POST/GET /api/customers` | Save and list scored customers |
| `GET /api/batches`, `GET /api/batches/<id>` | Saved scored lists and their rows |
| `POST /api/planner`, `POST/GET /api/plans` | Business planner and saved plans |
| `DELETE /api/<customers or batches or plans>/<id>` | Delete one item |
| `GET /api/export`, `DELETE /api/data` | Export or erase everything for the client |

Example:
```bash
curl -X POST http://127.0.0.1:5000/api/predict -H "Content-Type: application/json" \
  -d '{"features":{"recency":20,"frequency":10,"aov":90,"sessions":15,"email_click_rate":30},"margin":35}'
```
Missing features fall back to the training median; out-of-range values are clamped to the supported range.

## Tests

```bash
pip install pytest
pytest -q
```

## Docker

```bash
docker build -t custora-ai .
docker run -p 8000:8000 custora-ai       # http://localhost:8000
```

## Limitations and future work
- Trained on simulated data by default: real-world accuracy depends on real data quality.
- No user accounts: privacy is by a random per-browser id. Add authentication before storing sensitive data.
- Retraining is manual. Next steps: scheduled retraining, drift monitoring, a probabilistic BG/NBD baseline,
  and A/B tests of the recommended actions.
