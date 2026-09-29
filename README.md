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
  notebooks/Complete_workflow.ipynb  Explained cleaning, EDA, features and six-model training
  notebooks/car_valuation.ipynb  Compact workflow and saved evaluation results
  backend/
    api.py                       HTTP endpoints and request validation
    predict.py                   Shared prediction and validation logic
    features.py                  Shared training/prediction transformations
  models/vehicle_price.joblib     Existing website model
  models/selected_six_model.joblib  Newly selected six-model winner and evaluation metadata
  web/                           HTML, CSS, JavaScript and icon
  tests/                         Validation and workflow checks
```

## Training

```bash
.venv/bin/python train.py
```

The same feature columns and supplied mileage values are used for every accepted merged record, without source-specific masking, weights or source columns. Supplied values are not independently verified vehicle measurements. Tiptronic is normalized to Automatic. Price is learned in lakhs; predictions are displayed in lakhs and rupees.

The workflow groups similar vehicle specifications to keep profiles separate between training and evaluation. Preprocessing is learned inside each fold. Models are selected using mean MAE over three grouped validation folds; the final model is fitted on development records and evaluated on holdout records. The holdout has been used in earlier experiments and is not an independent external benchmark.

The candidates are Median baseline, Linear regression, Ridge regression, Decision tree, Random forest and Gradient boosting. No Extra Trees models are trained. If Random forest wins, its leaf size and feature fraction are tuned using the same development folds.

Every candidate displays MAE, RMSE, R2, MAPE_pct, Within_10_pct and Within_20_pct for cross-validation and holdout evaluation. MAE and RMSE are in LKR lakhs; MAPE and within-tolerance rates are percentages. Lower errors and higher R2/within-tolerance rates are better. The choice is locked using validation MAE before holdout evaluation; candidate holdout scores are descriptive and do not select the model. The selected-model holdout table includes any winning tuning configuration.

Only the new winner is saved to `models/selected_six_model.joblib`, with comparison, tuning, split indices and evaluation metadata. The existing website model is preserved and its loading path is unchanged. Run `notebooks/Complete_workflow.ipynb` from top to bottom with the `.venv-1` kernel for explanations, code comments, charts and all evaluation measures. `car_valuation.ipynb` loads the new winner for its compact evaluation and prediction demonstration. Raw inputs are not overwritten. No report folder or notebook helper scripts are required.

## Checks

```bash
.venv/bin/python -m unittest discover -s tests -v
```
