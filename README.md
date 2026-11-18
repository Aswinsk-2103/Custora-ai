## Overview

**Custora AI** is a machine learning-based customer analytics
application that predicts a customer's expected revenue over the next 12
months and estimates the probability that the customer will continue
purchasing.

The application analyses purchase behaviour and customer engagement
data, generates customer-level predictions, explains the factors
influencing each score, and recommends suitable business actions.

It combines trained machine learning models, a Flask REST API, an SQLite
database, and a browser-based interface in one application.

> **Dataset note:** The bundled dataset used for the current training
> results is simulated. The project can also be trained on real customer
> data when it is provided using the required feature columns.

## Key Features

### Customer Value Prediction

-   Predicts expected customer revenue for the next 12 months.
-   Uses purchase history and engagement behaviour as model inputs.
-   Displays an individual customer's predicted value.

### Customer Retention Prediction

-   Estimates whether a customer is likely to place another order in the
    next 12 months.
-   Produces a retention probability.
-   Helps identify customers who may be at risk of becoming inactive.

### Explainable Predictions

-   Shows the factors that influence the overall model.
-   Provides customer-level reasons behind a prediction.
-   Helps users understand why a customer receives a particular score.

### Customer Segmentation and Action Planning

-   Groups customers into Champion, Loyal Regular, At Risk, and
    Hibernating segments.
-   Maps each segment to a suggested business action.
-   Helps businesses prioritise retention efforts.

### Batch Scoring and Business Planning

-   Supports CSV upload for scoring multiple customers.
-   Ranks customers based on predicted value.
-   Includes business planning features for five-year value and payback.

### Model Report and Prediction History

-   Displays model metrics and charts.
-   Saves scored items and plans in SQLite.
-   Supports viewing, exporting, and deleting saved items.

## How It Works

1.  **Collect customer data** -- Use purchase and engagement information
    from the observation period.
2.  **Prepare features** -- Convert the customer information into the
    nine model input features.
3.  **Train the models** -- Compare regression models for revenue
    prediction and classifiers for retention prediction.
4.  **Evaluate performance** -- Use cross-validation and held-out test
    data to evaluate the trained models.
5.  **Generate predictions** -- The browser sends customer details to
    the Flask API.
6.  **Explain the result** -- The application displays the predicted
    value, retention probability, and contributing factors.
7.  **Recommend an action** -- The customer is assigned to a segment
    with a suggested next step.

### Observation and Prediction Period

  -----------------------------------------------------------------------
  Period                              Purpose
  ----------------------------------- -----------------------------------
  Months 1--12                        Observe purchase behaviour and
                                      engagement

  Months 13--24                       Predict future revenue and whether
                                      the customer orders again
  -----------------------------------------------------------------------

## Input Features

Custora AI uses **nine features** from two data categories.

### Purchase Behaviour

  Feature               Description
  --------------------- ----------------------------------------------------------
  Recency               Number of days since the customer's last order
  Frequency             Number of orders in the last 12 months
  Average Order Value   Average amount spent per order
  Tenure                Number of months the customer has been with the business
  Discount Share        Share of orders placed using a discount

### Customer Engagement

  Feature            Description
  ------------------ --------------------------------------------------
  Site Sessions      Website visits per month
  Email Click Rate   Share of emails clicked by the customer
  Cart Abandonment   Number of carts left unfinished
  Support Tickets    Number of support contacts in the last 12 months

## Machine Learning Models

The project uses separate models for the two prediction tasks.

### 1. Revenue Prediction -- Regression

The following regression algorithms are compared:

-   Linear Regression
-   Random Forest
-   Gradient Boosting
-   Hist Gradient Boosting

**Selected model: Random Forest**

Random Forest is selected using the lowest 3-fold cross-validation RMSE.

### 2. Retention Prediction -- Classification

The following classifiers are compared:

-   Logistic Regression
-   Hist Gradient Boosting

**Selected model: Hist Gradient Boosting**

It estimates the probability that a customer will place another order in
the next 12 months.

## Model Performance

The reported results are from the training run on **6,000 simulated
customers**.

### Revenue Model Comparison

  Model                      RMSE   MAE         R²   CV RMSE
  ------------------------ ------ ----- ---------- ---------
  Linear Regression           225   131       0.57       243
  Random Forest               206   106       0.64   **197**
  Gradient Boosting           196   105   **0.67**       202
  Hist Gradient Boosting      202   108       0.65       210

Random Forest is selected because it has the lowest cross-validation
RMSE (**197**). Gradient Boosting has a slightly higher test R², so the
models perform relatively closely on the held-out test set.

### Retention Model Comparison

  Classifier                  ROC-AUC   Accuracy   F1 Score
  ------------------------ ---------- ---------- ----------
  Logistic Regression            0.91        85%       0.83
  Hist Gradient Boosting     **0.94**    **86%**   **0.86**

**Selected retention model:** Hist Gradient Boosting.

### Evaluation Metrics

-   **RMSE:** Measures the typical size of prediction errors, with
    larger errors receiving more weight. Lower is better.
-   **MAE:** Measures the average absolute prediction error. Lower is
    better.
-   **R²:** Measures how much of the variation in the target is
    explained by the regression model. Higher is better.
-   **ROC-AUC:** Measures how well a classifier distinguishes between
    customers who return and those who do not. Higher is better.
-   **Accuracy:** The proportion of correct classification predictions.
-   **F1 Score:** Combines precision and recall into one score.

## Feature Importance

The permutation-importance analysis in the current simulated dataset
reports the following results:

  Feature                          Importance
  ------------------------------ ------------
  Average Order Value                   32.0%
  Orders in the Last 12 Months          28.2%
  Days Since Last Order                 27.6%
  Site Sessions per Month               10.4%
  Email Click Rate                       0.9%
  Months as a Customer                   0.4%

The three leading purchase signals account for approximately 88% of the
reported model behaviour in this dataset. Feature importance may change
when the model is trained using real customer data.

## Customer Segments and Recommended Actions

  -----------------------------------------------------------------------
  Segment                 Conditions              Suggested Action
  ----------------------- ----------------------- -----------------------
  Champion                Retention probability   Offer early access and
                          is 60% or above and     loyalty benefits
                          predicted value is in   
                          the top 20%             

  Loyal Regular           Retention probability   Increase basket size
                          is 50% or above         through bundles and
                                                  cross-selling

  At Risk                 Retention probability   Prioritise win-back
                          is below 50% and        offers
                          predicted value is      
                          above the median        

  Hibernating             Retention probability   Use low-cost automated
                          is below 50% and        reminders and nudges
                          predicted value is      
                          lower                   
  -----------------------------------------------------------------------

These segments turn model predictions into practical customer-retention
actions.

## System Architecture

``` text
                 +----------------------+
                 |      Browser UI      |
                 | HTML, CSS, JavaScript|
                 +----------+-----------+
                            |
                            v
                 +----------------------+
                 |      Flask API       |
                 | Validation & Scoring |
                 +----+------------+----+
                      |            |
             +--------v---+   +----v-------------+
             | Trained ML  |   |  SQLite Database |
             | Models      |   | Saved customers  |
             | Revenue     |   | Scores and plans |
             | Retention   |   +------------------+
             +-------------+

                 Training Pipeline
                        |
                        v
                  ml/train.py
                        |
                        v
              Saved model files
                (joblib / JSON)
```

### Main Components

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  Browser UI                          Customer inputs, sliders, CSV
                                      upload, charts, and history

  Flask REST API                      Input validation, predictions,
                                      explanations, planning, and batch
                                      scoring

  SQLite                              Stores customers, scored lists, and
                                      plans

  Trained Models                      Revenue regression and retention
                                      classification

  `ml/train.py`                       Prepares data, compares models, and
                                      saves trained model files
  -----------------------------------------------------------------------

### API Endpoints

  Method   Endpoint               Purpose
  -------- ---------------------- --------------------------------
  POST     `/api/predict`         Predict an individual customer
  POST     `/api/predict/batch`   Score multiple customers
  POST     `/api/planner`         Run business planning
  GET      `/api/model`           Retrieve model information
  GET      `/api/export`          Export application data

## Tech Stack

### Backend and Machine Learning

-   **Python** -- Main programming language
-   **Flask** -- REST API and application backend
-   **scikit-learn** -- Machine learning algorithms and evaluation
-   **Pandas** -- Data handling and preprocessing
-   **Joblib** -- Saving and loading trained models

### Frontend

-   **HTML** -- Page structure
-   **CSS** -- User interface styling
-   **JavaScript** -- Interactive controls and API communication

### Database

-   **SQLite** -- Local data storage

## Getting Started

### Prerequisites

Install the following before running the project:

-   Python 3.x
-   pip
-   Git
-   A code editor such as Visual Studio Code

### 1. Clone the Repository

``` bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <YOUR_PROJECT_FOLDER>
```

### 2. Create a Virtual Environment

**Windows:**

``` bash
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**

``` bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

If the repository includes a `requirements.txt` file, run:

``` bash
pip install -r requirements.txt
```

If dependencies are not listed in that file, install the packages
specified by the project:

``` bash
pip install flask pandas scikit-learn joblib
```

### 4. Train the Models

Run the training script from the project root:

``` bash
python ml/train.py
```

This prepares or loads the dataset, compares the models, evaluates the
selected models, and saves the trained model files.

### 5. Run the Application

``` bash
python run.py
```

Open the local address printed in the terminal by the Flask application.

> Run commands from the project root directory. The exact dataset and
> model-file locations depend on the repository's implementation.

## Application Modules

The application provides the following main areas:

1.  **Predict a Customer** -- Enter customer details and view live
    predictions, explanations, and suggested actions.
2.  **Score a List** -- Upload a CSV and rank multiple customers.
3.  **Plan My Business** -- Explore five-year value and payback.
4.  **Model Report** -- View model metrics and charts.
5.  **My Data** -- View saved items, export data, and delete saved
    records.

## Project Structure

The following is an illustrative structure based on the components
described in the project presentation. Update it to match the actual
repository folders and filenames before publishing.

``` text
Custora-AI/
│
├── app/
│   ├── templates/          # HTML templates (if used)
│   └── static/             # CSS, JavaScript and static assets
│
├── ml/
│   └── train.py            # Model training and comparison
│
├── models/                 # Saved model files (if used)
│
├── data/                   # Dataset files (if included)
│
├── run.py                  # Application entry point
├── requirements.txt        # Python dependencies (if included)
├── README.md
└── .gitignore
```

## Limitations

-   The default bundled dataset is simulated, so the reported metrics do
    not establish real-world business performance.
-   Real customer data is required to validate performance in a
    production setting.
-   The application does not currently include user accounts; privacy is
    based on a browser ID.
-   Model retraining is currently a manual process.
-   Recommended actions are decision-support suggestions and should be
    evaluated by the business before implementation.

## Future Enhancements

-   Train and validate the models using real customer data.
-   Add drift monitoring and scheduled model retraining.
-   A/B test the recommended customer-retention actions.
-   Add user authentication and account management.
-   Evaluate the models on data from different business periods and
    customer groups.

## Contributing

Contributions and suggestions are welcome.

1.  Fork the repository.

2.  Create a feature branch:

    ``` bash
    git checkout -b feature/your-feature
    ```

3.  Commit your changes:

    ``` bash
    git commit -m "Add your feature"
    ```

4.  Push your branch:

    ``` bash
    git push origin feature/your-feature
    ```

5.  Open a Pull Request.

## License

No license has been specified for this project yet. Add a `LICENSE` file
before presenting the repository as open source.

## Author

**Aswin SK**\
B.Tech -- Artificial Intelligence and Data Science\
Project: Custora AI

------------------------------------------------------------------------

::: {align="center"}
**Custora AI -- Turning Customer Data into Smarter Business Decisions.**
:::
