# Viva cheat sheet

**What problem does it solve?** It estimates how valuable each customer will be, so retention budget goes
where it returns most.

**What is CLV?** Customer lifetime value: the profit a customer is expected to bring over a period.
Here it is 12-month predicted revenue x margin.

**Why two models?** One regression model predicts how much a customer will spend; one classifier predicts whether
they will come back. The classifier's probability drives churn risk and segments.

**Which metrics?** Regression: RMSE, MAE, R². Classification: ROC-AUC, accuracy, F1.
RMSE penalises large misses; MAE is the average miss; R² is the share of variance explained.

**Why cross-validation?** It picks the model on training data only, so the test set stays unseen and the final
score is honest.

**Why do tree models beat linear regression here?** Customer value depends on interactions and thresholds
(for example many orders AND recent activity), which trees capture and a straight line cannot.

**How do you explain a prediction?** Permutation importance (global) and occlusion against a typical customer (per customer).

**Is the data real?** By default it is simulated with buy-till-you-die logic so the project runs anywhere.
`python -m ml.train --csv` trains on real data with the same columns.

**What would you improve?** Real data, BG/NBD baseline, scheduled retraining, drift monitoring, A/B tests of actions, authentication.
