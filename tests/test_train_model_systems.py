"""Regression tests for model-specific train systems and profiles."""

import json
import unittest
from pathlib import Path

from core.train_models import create_train, get_train_model_class
from core.train_models.model_81_717 import Train81717
from core.train_models.model_81_740 import Train81740
from core.train_models.model_81_760 import Train81760


class TrainModelRegistryTests(unittest.TestCase):
    def test_each_supported_model_has_a_distinct_adapter(self):
        classes = (
            get_train_model_class("81-717"),
            get_train_model_class("81-740"),
            get_train_model_class("81-760"),
        )
        self.assertEqual(classes, (Train81717, Train81740, Train81760))
        self.assertEqual(len(set(classes)), 3)

    def test_factory_uses_explicit_model_id(self):
        for model_id, expected_class in (
            ("81-717", Train81717),
            ("81-740", Train81740),
            ("81-760", Train81760),
        ):
            with self.subTest(model_id=model_id):
                train = create_train({"model_id": model_id, "name": model_id})
                self.assertIsInstance(train, expected_class)
                self.assertEqual(train.model_id, model_id)

    def test_unknown_or_mismatched_model_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported train model"):
            create_train({"name": "unknown-train"})
        with self.assertRaisesRegex(ValueError, "does not match"):
            create_train({"model_id": "81-717", "name": "81-760"})

    def test_equipment_implementations_are_model_specific(self):
        trains = (
            create_train({"model_id": "81-717", "name": "81-717"}),
            create_train({"model_id": "81-740", "name": "81-740"}),
            create_train({"model_id": "81-760", "name": "81-760"}),
        )
        for attribute in ("pneumatics", "electrodynamic_brake", "traction_system"):
            with self.subTest(component=attribute):
                self.assertEqual(len({type(getattr(train, attribute)) for train in trains}), 3)

    def test_provisional_models_do_not_claim_oka_pressure_units_or_ed(self):
        for model_id in ("81-717", "81-740"):
            train = create_train({"model_id": model_id, "name": model_id})
            self.assertEqual(train.PRESSURE_DISPLAY_UNIT, "усл. ед.")
            self.assertFalse(train.electrodynamic_brake.available)
            self.assertEqual(train.electrodynamic_brake.calculate(10.0, -3), 0.0)

    def test_oka_keeps_its_documented_ed_implementation(self):
        train = create_train({"model_id": "81-760", "name": "81-760"})
        self.assertEqual(train.PRESSURE_DISPLAY_UNIT, "кгс/см²")
        self.assertTrue(train.electrodynamic_brake.available)
        self.assertGreater(train.electrodynamic_brake.calculate(60.0 / 3.6, -3), 0.0)

    def test_train_data_files_declare_matching_model_ids(self):
        data_dir = Path(__file__).resolve().parents[1] / "data" / "trains"
        for model_id in ("81-717", "81-740", "81-760"):
            with self.subTest(model_id=model_id):
                config = json.loads((data_dir / f"{model_id}.json").read_text(encoding="utf-8"))
                self.assertEqual(config["model_id"], model_id)
                self.assertEqual(config["name"], model_id)


if __name__ == "__main__":
    unittest.main()
