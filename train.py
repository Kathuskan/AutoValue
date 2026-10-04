"""Merge inputs, compare regressors and save one model: python train.py."""
from pathlib import Path
import hashlib
import json
import platform
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit, GroupKFold
from backend.features import FEATURES, CATEGORIES, REFERENCE_YEAR, normalize, group_ids, make_pipeline, engine_options

ROOT = Path(__file__).resolve().parent
DATASET = ROOT / 'data/cars.csv'
MODEL = ROOT / 'models/selected_model.joblib'
SEED = 42
COLUMNS = FEATURES + ['Price', 'Date']


def merge_data():
    """One dataset; supplied mileage is retained for every accepted record."""
    paths = [ROOT / 'data/raw/car_price_dataset.csv', ROOT / 'data_collection/cleaned_new_data.csv']
    parts = [normalize(pd.read_csv(path)[COLUMNS]) for path in paths]
    frame = pd.concat(parts, ignore_index=True)
    frame['Price'] = pd.to_numeric(frame.Price, errors='coerce')
    frame['Date'] = pd.to_datetime(frame.Date, format='%Y-%m-%d', errors='coerce').dt.strftime('%Y-%m-%d')
    # Tiptronic is represented as automatic consistently in training and the UI.
    frame['Gear'] = frame.Gear.replace('TIPTRONIC', 'AUTOMATIC')
    valid = (np.isfinite(frame[['YOM', 'Engine (cc)', 'Millage(KM)', 'Price']]).all(axis=1)
             & frame.Price.gt(0) & frame.YOM.between(1886, REFERENCE_YEAR)
             & frame.YOM.mod(1).eq(0) & frame['Engine (cc)'].between(0, 20000)
             & frame['Millage(KM)'].between(0, 3000000)
             & frame[CATEGORIES].notna().all(axis=1) & frame.Date.notna()
             & frame.Gear.isin(['AUTOMATIC', 'MANUAL']) & frame.Condition.isin(['USED', 'NEW']))
    electric = frame['Fuel Type'].eq('ELECTRIC')
    valid &= (electric & frame['Engine (cc)'].eq(0)) | (~electric & frame['Engine (cc)'].gt(0))
    cleaned = frame.loc[valid].drop_duplicates(COLUMNS).reset_index(drop=True)
    DATASET.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(DATASET, index=False)
    print(f'Merged {len(frame):,} input rows into {len(cleaned):,} records.', flush=True)
    return cleaned


def metrics(actual, predicted):
    """Errors use lakhs; percentage measures use 0–100; R2 is a score."""
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    relative = abs(actual - predicted) / actual
    return {'MAE': float(mean_absolute_error(actual, predicted)),
            'RMSE': float(root_mean_squared_error(actual, predicted)),
            'R2': float(r2_score(actual, predicted)),
            'MAPE_pct': float(relative.mean() * 100),
            'Within_10_pct': float((relative <= .1).mean() * 100),
            'Within_20_pct': float((relative <= .2).mean() * 100)}


def candidates():
    return {
        'Median baseline': DummyRegressor(strategy='median'),
        'Linear regression': LinearRegression(),
        'Ridge regression': Ridge(alpha=10, solver='lsqr'),
        'Decision tree': DecisionTreeRegressor(max_depth=18, min_samples_leaf=4, random_state=SEED),
        'Random forest': RandomForestRegressor(n_estimators=100, max_depth=26, min_samples_leaf=2, n_jobs=2, random_state=SEED),
        'Extra trees': ExtraTreesRegressor(n_estimators=120, max_depth=28, min_samples_leaf=1, n_jobs=2, random_state=SEED),
        'Gradient boosting': GradientBoostingRegressor(n_estimators=120, max_depth=3, learning_rate=.06, loss='huber', random_state=SEED),
    }


def validation_scores(pipeline, frame, folds):
    results = []
    for fit, valid in folds:
        fitted = clone(pipeline).fit(frame.iloc[fit][FEATURES], frame.iloc[fit].Price)
        results.append(metrics(frame.iloc[valid].Price, fitted.predict(frame.iloc[valid][FEATURES])))
    return results


def train_model(frame):
    """Select on grouped cross-validation, evaluate once, persist only the winner."""
    groups = group_ids(frame)
    fit, test = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=SEED).split(frame, groups=groups))
    development = frame.iloc[fit].reset_index(drop=True)
    holdout = frame.iloc[test]
    assert not set(groups.iloc[fit]) & set(groups.iloc[test])
    development_groups = group_ids(development)
    folds = list(GroupKFold(n_splits=3).split(development, groups=development_groups))
    for a, b in folds:
        assert not set(development_groups.iloc[a]) & set(development_groups.iloc[b])
    comparison = []
    best, best_score, winner = None, float('inf'), None
    for name, estimator in candidates().items():
        print(f'Comparing: {name}', flush=True)
        pipeline = make_pipeline(estimator, use_mileage=True, use_engine=True)
        scores = validation_scores(pipeline, development, folds)
        score = float(np.mean([s['MAE'] for s in scores]))
        # Report every measure on the same folds for a fair comparison.
        comparison.append({'Model': name,
                           **{'CV ' + key: float(np.mean([s[key] for s in scores])) for key in scores[0]},
                           'Fold metrics': scores})
        if score < best_score:
            best, best_score, winner = pipeline, score, name
    tuning = []
    # Tune the winning bagged-tree family using development folds only.
    if winner in {'Random forest', 'Extra trees'}:
        base = clone(best)
        for leaf, fraction in [(1, .7), (2, .7), (3, 1.)]:
            print(f'Tuning {winner}: leaf={leaf}, features={fraction}', flush=True)
            proposal = clone(base).set_params(model__min_samples_leaf=leaf, model__max_features=fraction)
            scores = validation_scores(proposal, development, folds)
            score = float(np.mean([s['MAE'] for s in scores]))
            tuning.append({'min_samples_leaf': leaf, 'max_features': fraction,
                           **{'CV ' + key: float(np.mean([s[key] for s in scores])) for key in scores[0]}})
            if score < best_score:
                best, best_score = proposal, score
    # Lock the choice using validation MAE before consulting holdout outcomes.
    for row in comparison:
        fitted = make_pipeline(candidates()[row['Model']]).fit(development[FEATURES], development.Price)
        row.update({'Holdout ' + key: value for key, value in
                    metrics(holdout.Price, fitted.predict(holdout[FEATURES])).items()})
    best.fit(development[FEATURES], development.Price)
    scores = metrics(holdout.Price, best.predict(holdout[FEATURES]))
    info = {'winner': winner, 'test': scores, 'reference_year': REFERENCE_YEAR,
            'date_range': [str(frame.Date.min()), str(frame.Date.max())],
            'use_mileage': True, 'use_engine': True, 'selection_metric': 'Mean MAE over three grouped validation folds',
            'selected_cv_mae': best_score, 'model_comparison': comparison, 'tuning': tuning,
            'selected_parameters': best.named_steps['model'].get_params(),
            'development_rows': len(development), 'holdout_rows': len(holdout), 'group_overlap': 0,
            'development_indices': fit.tolist(), 'holdout_indices': test.tolist(),
            'seed': SEED, 'price_unit': 'LKR lakhs',
            'dataset_sha256': hashlib.sha256(DATASET.read_bytes()).hexdigest(),
            'evaluation_note': 'Grouped development holdout; these records have been used in previous experiments, not external validation.',
            'versions': {'python': platform.python_version(), 'sklearn': sklearn.__version__, 'pandas': pd.__version__}}
    metadata = {'metrics': info,
                'categories': {c: sorted(development[c].dropna().unique().tolist()) for c in CATEGORIES},
                'ranges': {c: [float(development[c].min()), float(development[c].max())]
                           for c in ['YOM', 'Engine (cc)', 'Millage(KM)']},
                'brand_models': {brand: sorted(g.Model.unique().tolist()) for brand, g in development.groupby('Brand')},
                'engine_options': engine_options(development)}
    from backend.predict import FIELDS, predict_car
    preferred = development[(development.Brand == 'NISSAN') & (development.Model == 'ROOX') & (development.Gear == 'AUTOMATIC')]
    sample = preferred.iloc[0] if len(preferred) else development.iloc[0]
    metadata['example'] = {key: (int(sample[col]) if key == 'yom' else float(sample[col])
                               if key in {'engine_cc', 'millage'} else str(sample[col])) for key, col in FIELDS.items()}
    bundle = {'pipeline': best, 'metadata': metadata}
    predict_car(metadata['example'], bundle)
    MODEL.parent.mkdir(parents=True, exist_ok=True)
    temporary = MODEL.with_suffix('.tmp')
    joblib.dump(bundle, temporary)
    # Verify that the serialized pipeline reproduces inference before replacement.
    restored = joblib.load(temporary)
    np.testing.assert_allclose(best.predict(holdout[FEATURES].iloc[:5]),
                               restored['pipeline'].predict(holdout[FEATURES].iloc[:5]))
    temporary.replace(MODEL)
    print(pd.DataFrame(comparison).drop(columns='Fold metrics').sort_values('CV MAE').to_string(index=False), flush=True)
    print('Selected:', winner, '\nHoldout:', json.dumps(scores, indent=2), flush=True)
    return bundle


def main():
    train_model(merge_data())


if __name__ == '__main__':
    main()
