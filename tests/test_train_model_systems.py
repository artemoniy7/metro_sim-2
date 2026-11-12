"""Regression tests for model-specific train systems and profiles."""

import json
import unittest
from pathlib import Path

from core.train_models import create_train, get_train_model_class
from core.train_models.model_81_717 import Train81717
from core.train_models.model_81_740 import Train81740
from core.train_models.model_81_760 import Train81760
from core.train_models.model_81_777 import Train81777
from core.train_models.oka import profile as oka_profile
from core.train_models.nomernoy import profile as nomernoy_profile
from core.train_models.rusich import profile as rusich_profile
from core.train_models.moscow_2020 import profile as moscow_2020_profile
from core.train_models.shared.provisional_equipment import ProvisionalPneumaticSystem


class TrainModelRegistryTests(unittest.TestCase):
    def test_each_supported_model_has_a_distinct_adapter(self):
        classes = (
            get_train_model_class("81-717"),
            get_train_model_class("81-740"),
            get_train_model_class("81-760"),
            get_train_model_class("81-777"),
        )
        self.assertEqual(classes, (Train81717, Train81740, Train81760, Train81777))
        self.assertEqual(len(set(classes)), 4)

    def test_factory_uses_explicit_model_id(self):
        for model_id, expected_class in (
            ("81-717", Train81717),
            ("81-740", Train81740),
            ("81-760", Train81760),
            ("81-777", Train81777),
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
            create_train({"model_id": "81-777", "name": "81-777"}),
        )
        for attribute in ("pneumatics", "electrodynamic_brake", "traction_system"):
            with self.subTest(component=attribute):
                self.assertEqual(len({type(getattr(train, attribute)) for train in trains}), 4)

    def test_provisional_models_do_not_claim_oka_pressure_units_or_ed(self):
        for model_id in ("81-717", "81-740", "81-777"):
            train = create_train({"model_id": model_id, "name": model_id})
            self.assertEqual(train.PRESSURE_DISPLAY_UNIT, "усл. ед.")
            self.assertFalse(train.electrodynamic_brake.available)
            self.assertEqual(train.electrodynamic_brake.calculate(10.0, -3), 0.0)

    def test_oka_keeps_its_documented_ed_implementation(self):
        train = create_train({"model_id": "81-760", "name": "81-760"})
        self.assertEqual(train.PRESSURE_DISPLAY_UNIT, "кгс/см²")
        self.assertTrue(train.electrodynamic_brake.available)
        self.assertGreater(train.electrodynamic_brake.calculate(60.0 / 3.6, -3), 0.0)


    def test_visual_audio_profiles_do_not_reuse_oka_assets_or_geometry(self):
        self.assertEqual(oka_profile.ASSET_DIRECTORY, "81-760")
        self.assertEqual(nomernoy_profile.ASSET_DIRECTORY, "81-717")
        self.assertEqual(rusich_profile.ASSET_DIRECTORY, "81-740")
        self.assertTrue(oka_profile.DOOR_ANIMATION_SUPPORTED)
        self.assertFalse(nomernoy_profile.DOOR_ANIMATION_SUPPORTED)
        self.assertFalse(rusich_profile.DOOR_ANIMATION_SUPPORTED)
        self.assertEqual(nomernoy_profile.LOCO_PAIRS, ())
        self.assertEqual(rusich_profile.LOCO_PAIRS, ())
        self.assertIsNone(nomernoy_profile.JOINT_PATTERN)
        self.assertIsNone(rusich_profile.JOINT_PATTERN)
        self.assertTrue(oka_profile.COMPRESSOR_SUPPORTED)
        self.assertFalse(nomernoy_profile.COMPRESSOR_SUPPORTED)
        self.assertFalse(rusich_profile.COMPRESSOR_SUPPORTED)
        self.assertEqual(moscow_2020_profile.ASSET_DIRECTORY, "81-777")
        self.assertEqual(moscow_2020_profile.LOCO_SOURCE_SIZE, (2130, 444))
        self.assertEqual(moscow_2020_profile.CAR_SOURCE_SIZE, (2050, 431))
        self.assertTrue(moscow_2020_profile.DOOR_ANIMATION_SUPPORTED)
        self.assertEqual(moscow_2020_profile.AUDIO_DIRECTORY, "81-777")
        self.assertEqual(moscow_2020_profile.MOTION_AUDIO_DIRECTORY, "81-760")
        self.assertEqual(moscow_2020_profile.LOCO_PAIRS, ((359, 646), (1833, 2082)))
        self.assertEqual(moscow_2020_profile.CAR_PAIRS, ((193, 464), (1763, 2018)))
        self.assertIsNotNone(moscow_2020_profile.JOINT_PATTERN)
        self.assertIsNotNone(moscow_2020_profile.STATION_JOINT_PATTERN)
        self.assertTrue(moscow_2020_profile.COMPRESSOR_SUPPORTED)

    def test_provisional_pneumatics_apply_and_release_service_brake(self):
        system = ProvisionalPneumaticSystem()
        system.update(0.1, controller_notch=-3)
        self.assertGreater(system.pressure_tc, 0.0)
        system.update(0.1, controller_notch=0)
        self.assertLess(system.pressure_tc, 1.0)

    def test_train_data_files_declare_matching_model_ids(self):
        data_dir = Path(__file__).resolve().parents[1] / "data" / "trains"
        for model_id in ("81-717", "81-740", "81-760", "81-777"):
            with self.subTest(model_id=model_id):
                config = json.loads((data_dir / f"{model_id}.json").read_text(encoding="utf-8"))
                self.assertEqual(config["model_id"], model_id)
                self.assertEqual(config["name"], model_id)


    def test_81_777_uses_provided_wagon_length_and_provisional_physics(self):
        data_dir = Path(__file__).resolve().parents[1] / "data" / "trains"
        config = json.loads((data_dir / "81-777.json").read_text(encoding="utf-8"))
        train = create_train(config)
        self.assertEqual(train.model_id, "81-777")
        self.assertEqual(train.loco_length_m, 19.32)
        self.assertEqual(train.car_length_m, 19.32)
        self.assertEqual(len(train.wagons), 8)
        self.assertEqual(train.physics_reference_status, "provisional_pending_technical_sources")
        self.assertFalse(train.electrodynamic_brake.available)


if __name__ == "__main__":
    unittest.main()
