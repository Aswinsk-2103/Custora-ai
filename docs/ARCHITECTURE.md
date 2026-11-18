# Architecture

## Request flow (single prediction)
1. The browser sends `POST /api/predict` with the nine features and the margin.
2. `Predictor.clean` fills missing values (training median) and clamps every value to its valid range.
3. The regression model predicts 12-month revenue; the classifier predicts the probability of ordering again.
4. CLV = revenue x margin. The segment comes from retention and revenue percentiles.
5. `Predictor.explain` runs 9 "typical value" variants of the customer to measure each feature's effect.
6. Rule-based actions are chosen from the weakest signals and the segment. The JSON reply goes back to the UI.

## Database (SQLite, `data/custora.db`)
- `customers(id, client_id, name, features, result, margin, created_at)`
- `batches(id, client_id, name, count, total_clv, avg_clv, segments, margin, truncated, created_at)`
- `batch_rows(batch_id -> batches ON DELETE CASCADE, idx, customer_id, features, clv, retention, segment, risk)`
- `plans(id, client_id, inputs, result, created_at)`
Indexes cover `(client_id, created_at)` and `(batch_id, idx)`. Every query filters by `client_id`.

## Design decisions
- **One schema file for features** (`ml/config.py`) so training, API validation and UI sliders cannot drift apart.
- **Model chosen on cross-validation, scored on a test set** to avoid optimistic results.
- **Server-side recomputation on save**: the API recomputes predictions instead of trusting numbers from the browser.
- **Auto-training on first start** so a fresh clone works with one command.
- **Static frontend served by Flask**: one process, no CORS, no build tooling.
