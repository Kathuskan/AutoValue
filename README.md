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
  notebooks/car_valuation.ipynb  Manually run EDA, features, evaluation and prediction
  backend/
    api.py                       HTTP endpoints and request validation
    predict.py                   Shared prediction and validation logic
    features.py                  Shared training/prediction transformations
  models/vehicle_price.joblib     One saved pipeline, including evaluation metadata
  web/                           HTML, CSS, JavaScript and icon
  tests/                         Validation and workflow checks
```

## Training

```bash
.venv/bin/python train.py
```

The same feature columns and supplied mileage values are used for every accepted merged record, without source-specific masking, weights or source columns. Supplied values are not independently verified vehicle measurements. Tiptronic is normalized to Automatic. Price is learned in lakhs; predictions are displayed in lakhs and rupees.

The workflow groups similar vehicle specifications to keep profiles separate between training and evaluation. Preprocessing is learned inside each fold. Models are selected using mean MAE over three grouped validation folds; the final model is fitted on development records and evaluated on holdout records. The holdout has been used in earlier experiments and is not an independent external benchmark.

Only the winner is saved. Model comparison, split indices and metrics are stored inside the same model file, with no separate report folder. Raw inputs are not overwritten. Notebook execution is manual; no notebook builder or execution scripts are included.

## Checks

```bash
.venv/bin/python -m unittest discover -s tests -v
```
