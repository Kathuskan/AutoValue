"""Verify saved-model evaluation and the single dataset without retraining."""
import hashlib
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
from backend.features import FEATURES, group_ids, normalize
from backend.predict import load_bundle
from train import metrics

ROOT = Path(__file__).resolve().parents[1]


class WorkflowTests(unittest.TestCase):
    def test_one_dataset_preserves_supplied_values(self):
        data = pd.read_csv(ROOT / 'data/cars.csv')
        self.assertEqual(set(data.columns), set(FEATURES + ['Price', 'Date']))
        self.assertFalse(data['Millage(KM)'].isna().any())
        inputs = pd.concat([pd.read_csv(ROOT / 'data/raw/car_price_dataset.csv'),
                            pd.read_csv(ROOT / 'data_collection/cleaned_new_data.csv')], ignore_index=True)
        inputs = normalize(inputs)
        inputs['Gear'] = inputs.Gear.replace('TIPTRONIC', 'AUTOMATIC')
        columns = FEATURES + ['Price']
        original = set(map(tuple, inputs[columns].itertuples(index=False, name=None)))
        self.assertTrue(all(row in original for row in data[columns].itertuples(index=False, name=None)))
        self.assertEqual(set(data.Gear), {'AUTOMATIC', 'MANUAL'})

    def test_saved_holdout_scores_and_split(self):
        data = pd.read_csv(ROOT / 'data/cars.csv')
        bundle = load_bundle()
        info = bundle['metadata']['metrics']
        self.assertEqual(hashlib.sha256((ROOT / 'data/cars.csv').read_bytes()).hexdigest(), info['dataset_sha256'])
        fit, test = info['development_indices'], info['holdout_indices']
        self.assertEqual(set(fit) | set(test), set(range(len(data))))
        self.assertFalse(set(fit) & set(test))
        groups = group_ids(data)
        self.assertFalse(set(groups.iloc[fit]) & set(groups.iloc[test]))
        scores = metrics(data.iloc[test].Price, bundle['pipeline'].predict(data.iloc[test][FEATURES]))
        for key, expected in info['test'].items():
            self.assertTrue(np.isclose(scores[key], expected), key)
        self.assertTrue(info['use_mileage'])
        self.assertTrue(info['use_engine'])


if __name__ == '__main__':
    unittest.main()
