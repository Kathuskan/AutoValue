"""Shared preprocessing for training and prediction."""
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

FEATURES = ['Brand', 'Model', 'YOM', 'Engine (cc)', 'Gear', 'Fuel Type', 'Millage(KM)', 'Condition']
PROFILE = ['Brand', 'Model', 'YOM', 'Engine (cc)', 'Gear', 'Fuel Type']
CATEGORIES = ['Brand', 'Model', 'Gear', 'Fuel Type', 'Condition']
REFERENCE_YEAR = 2026

def engine_options(frame):
    """Observed training capacities, not a catalogue of valid vehicle configurations."""
    options = {}
    for (brand, model), group in normalize(frame).groupby(['Brand', 'Model']):
        capacities = sorted(float(v) for v in group['Engine (cc)'].dropna().unique() if np.isfinite(v) and v > 0)
        if capacities:
            options.setdefault(brand, {})[model] = capacities
    return options

def normalize(frame):
    out = frame.copy()
    for col in CATEGORIES:
        if col in out:
            out[col] = out[col].astype('string').str.strip().str.upper().str.replace(r'\s+', ' ', regex=True)
            out[col] = out[col].replace('', pd.NA).astype(object).where(lambda s: s.notna(), np.nan)
    for col in ['YOM', 'Engine (cc)', 'Millage(KM)']:
        if col in out:
            out[col] = pd.to_numeric(out[col], errors='coerce').astype(float)
    return out

def group_ids(frame):
    # Mileage is unreliable in legacy data; condition may differ across reposts.
    return pd.util.hash_pandas_object(normalize(frame)[PROFILE], index=False).astype(str)

class VehicleFeatures(BaseEstimator, TransformerMixin):
    def __init__(self, use_mileage=True, use_engine=True, reference_year=REFERENCE_YEAR):
        self.use_mileage = use_mileage
        self.use_engine = use_engine
        self.reference_year = reference_year

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        columns = ['YOM'] + CATEGORIES
        if self.use_engine:
            columns.append('Engine (cc)')
        if self.use_mileage:
            columns.append('Millage(KM)')
        out = normalize(X[columns])
        out['Age at reference year'] = (self.reference_year - out.YOM).clip(lower=0)
        out['Brand model'] = out.Brand + ' | ' + out.Model
        if self.use_mileage:
            out['Log mileage'] = np.log1p(out['Millage(KM)'].clip(lower=0))
        return out

def make_pipeline(model, use_mileage=True, use_engine=True):
    numeric = ['YOM', 'Age at reference year']
    if use_engine:
        numeric += ['Engine (cc)']
    if use_mileage:
        numeric += ['Millage(KM)', 'Log mileage']
    prep = ColumnTransformer([
        ('numeric', Pipeline([('impute', SimpleImputer(strategy='median')),
                              ('scale', StandardScaler())]), numeric),
        ('categorical', Pipeline([('impute', SimpleImputer(strategy='constant', fill_value='UNKNOWN')),
                                  ('encode', OneHotEncoder(handle_unknown='ignore', min_frequency=5))]),
         CATEGORIES + ['Brand model'])])
    return Pipeline([('features', VehicleFeatures(use_mileage, use_engine)), ('preprocessing', prep), ('model', model)])
