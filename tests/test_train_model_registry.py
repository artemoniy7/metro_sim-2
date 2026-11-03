"""Regression tests for explicit per-model train dispatch."""

import unittest

from core.train import Train
from core.train_models import create_train, get_train_model_class
from core.train_models.model_81_717 import Train81717
from core.train_models.model_81_740 import Train81740
from core.train_models.model_81_760 import Train81760
from core.train_models.model_81_777 import Train81777


class TrainModelRegistryTests(unittest.TestCase):
    def test_each_supported_model_has_a_distinct_adapter(self):
        classes = (
            get_train_model_class("81-717"),
            get_train_model_class("81-740"),
            get_train_model_class("81-760"),
        )
        self.assertEqual(classes, (Train81717, Train81740, Train81760))
        self.assertEqual(len(set(classes)), 3)
        self.assertTrue(all(issubclass(cls, Train) for cls in classes))

    def test_factory_uses_model_id_from_configuration(self):
        for model_id, expected_class in (
            ("81-717", Train81717),
            ("81-740", Train81740),
            ("81-760", Train81760),
            ("81-777", Train81777),
        ):
            with self.subTest(model_id=model_id):
                train = create_train({"name": model_id})
                self.assertIsInstance(train, expected_class)
                self.assertEqual(train.model_id, model_id)

    def test_unknown_model_does_not_silently_fall_back(self):
        with self.assertRaisesRegex(ValueError, "Unsupported train model"):
            create_train({"name": "unknown-train"})


if __name__ == "__main__":
    unittest.main()
