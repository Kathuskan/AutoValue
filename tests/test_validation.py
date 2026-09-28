"""Run from AutoValue: python -m unittest discover -s tests -v."""
import unittest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from backend.api import app
from backend.predict import load_bundle, predict_car


class PredictionValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = load_bundle()
        cls.example = cls.bundle['metadata']['example']

    def test_invalid_details_never_reach_model(self):
        pipeline = Mock()
        bundle = {**self.bundle, 'pipeline': pipeline}
        cases = [dict(engine_cc=0, fuel_type='PETROL'), dict(gear='BANANA'),
                 dict(gear='TIPTRONIC'), dict(fuel_type='BANANA'),
                 dict(brand='UNKNOWN BRAND'), dict(model_name='UNKNOWN MODEL'),
                 dict(millage=-1), dict(engine_cc=True), dict(yom=2024.5),
                 dict(engine_cc=float('nan')), dict(engine_cc=None)]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                predict_car({**self.example, **changes}, bundle)
        pipeline.predict.assert_not_called()

    def test_api_rejects_invalid_inputs(self):
        with TestClient(app) as client:
            for changes in [dict(engine_cc=0, fuel_type='PETROL'), dict(gear='BANANA'),
                            dict(fuel_type='BANANA'), dict(engine_cc=True),
                            dict(millage=False), dict(yom=True), dict(engine_cc=None)]:
                with self.subTest(changes=changes):
                    self.assertEqual(client.post('/predict', json={**self.example, **changes}).status_code, 422)

    def test_example_and_manual_capacity_remain_supported(self):
        with TestClient(app) as client:
            response = client.post('/predict', json=self.example)
            self.assertEqual(response.status_code, 200)
            self.assertGreater(response.json()['predicted_price_lakhs'], 0)
            manual = client.post('/predict', json={**self.example, 'engine_cc': 661})
            self.assertEqual(manual.status_code, 200)
            self.assertTrue(manual.json()['warnings'])

    def test_normalized_text_is_accepted(self):
        result = predict_car({**self.example, 'brand': ' nissan ', 'gear': ' automatic '}, self.bundle)
        self.assertGreater(result['predicted_price_lkr'], 0)


if __name__ == '__main__':
    unittest.main()
