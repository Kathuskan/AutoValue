# AutoValue LK

One workflow: merge the two input datasets, train and compare regression models on one dataset, save one selected model, and serve predictions through the website. Data was obtained from Kaggle and scraped ikman.lk listings.

## Setup and application

From the repository root, create a Python 3.9 virtual environment and install the dependencies:

```bash
python3.9 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_web.py
```

Open http://127.0.0.1:8000. Stop with Control+C. Restart after backend or model changes.
For a new installation, create a Python 3.9 environment and install requirements.txt. The dependencies match the locally checked environment.

## Structure

```text
AutoValue/
  train.py                       Merge, compare models, evaluate, save the winner
  run_web.py                     Start website and prediction API
  requirements.txt               Python dependencies
  data/
    raw/car_price_dataset.csv    Untouched original input
    cars.csv                     One merged dataset used for training
  data_collection/               Scraped inputs, cleaner and cleaning notebook
  notebooks/Complete_workflow.ipynb  Explained cleaning, EDA, features and seven-model training
  backend/
    api.py                       HTTP endpoints and request validation
    predict.py                   Shared prediction and validation logic
    features.py                  Shared training/prediction transformations
  models/selected_model.joblib    Selected pipeline used by the website and notebook
  models/vehicle_price.joblib     Preserved older model
  models/selected_six_model.joblib  Preserved previous six-model winner
  web/                           HTML, CSS, JavaScript and icon
```

## Training

```bash
.venv/bin/python train.py
```

The same feature columns and supplied mileage values are used for every accepted merged record, without source-specific masking, weights or source columns. Supplied values are not independently verified vehicle measurements. Tiptronic is normalized to Automatic. Price is learned in lakhs; predictions are displayed in lakhs and rupees.

The workflow groups similar vehicle specifications to keep profiles separate between training and evaluation. Preprocessing is learned inside each fold. Models are selected using mean MAE over three grouped validation folds; the final model is fitted on development records and evaluated on holdout records. The holdout has been used in earlier experiments and is not an independent external benchmark.

The seven candidates are Median baseline, Linear regression, Ridge regression, Decision tree, Random forest, Extra trees and Gradient boosting. Extra trees starts with 120 trees, maximum depth 28 and minimum leaf size 1. If Random forest or Extra trees wins, its leaf size and feature fraction are tuned using the same development folds. The selected algorithm is determined by validation MAE, not fixed in advance.

Every candidate displays MAE, RMSE, R2, MAPE_pct, Within_10_pct and Within_20_pct for cross-validation and holdout evaluation. MAE and RMSE are in LKR lakhs; MAPE and within-tolerance rates are percentages. Lower errors and higher R2/within-tolerance rates are better. The choice is locked using validation MAE before holdout evaluation; candidate holdout scores are descriptive and do not select the model. The selected-model holdout table includes any winning tuning configuration.

Only the new winner is saved to `models/selected_model.joblib`, with preprocessing, selected parameters, comparison, tuning, split indices and evaluation metadata. Saving uses a temporary file, reloads it to verify prediction consistency, and then replaces the selected artifact. Previous model files remain available. The website loads this same selected artifact; restart an already-running server after training to load it.

Run `notebooks/Complete_workflow.ipynb` from top to bottom with the `.venv-1` kernel for explanations, code comments and all evaluation measures. Charts compare every candidate's six CV and holdout measures. Saved-model diagnostics show actual versus predicted prices, residuals versus predictions and the full residual distribution. The notebook reloads the artifact and checks that its holdout metrics reproduce the saved values. Raw inputs are not overwritten.
